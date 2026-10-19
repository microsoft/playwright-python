# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Port of tests/library/page-clock.spec.ts.

The Python clock API takes the times of install, pause_at, set_fixed_time and
set_system_time in seconds (upstream: milliseconds); run_for and fast_forward take
milliseconds, as upstream does.
"""

import datetime
import os
import time
from typing import Any, Callable, Dict, List

import pytest

from playwright.sync_api import Browser, Error, Page
from tests.server import Server, TestServerRequest

# Upstream skips this file when PW_CLOCK installs a clock in every context.
pytestmark = pytest.mark.skipif(bool(os.environ.get("PW_CLOCK")), reason="PW_CLOCK")

Calls = List[Dict[str, List[Any]]]


@pytest.fixture
def calls(page: Page) -> Calls:
    calls: Calls = []
    page.expose_function("stub", lambda *params: calls.append({"params": list(params)}))
    return calls


@pytest.fixture
def install_and_pause(page: Page) -> None:
    # The beforeEach of the runFor, fastForward and stubTimers describes.
    page.clock.install(time=0)
    page.clock.pause_at(1)


def _popup_route(server: Server) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(b"<script>window.time = Date.now()</script>")
        request.finish()

    server.set_route("/popup.html", handler)


@pytest.mark.usefixtures("install_and_pause")
def test_CK_001_run_for_triggers_immediately_without_specified_delay(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub);
    }"""
    )
    page.clock.run_for(0)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
def test_CK_002_run_for_does_not_trigger_without_sufficient_delay(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
    }"""
    )
    page.clock.run_for(10)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
def test_CK_003_run_for_triggers_after_sufficient_delay(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
    }"""
    )
    page.clock.run_for(100)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
def test_CK_004_run_for_triggers_simultaneous_timers(page: Page, calls: Calls) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
      setTimeout(window.stub, 100);
    }"""
    )
    page.clock.run_for(100)
    assert len(calls) == 2


@pytest.mark.usefixtures("install_and_pause")
def test_CK_005_run_for_triggers_multiple_simultaneous_timers(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
      setTimeout(window.stub, 100);
      setTimeout(window.stub, 99);
      setTimeout(window.stub, 100);
    }"""
    )
    page.clock.run_for(100)
    assert len(calls) == 4


@pytest.mark.usefixtures("install_and_pause")
def test_CK_006_run_for_waits_after_set_timeout_was_called(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub, 150);
    }"""
    )
    page.clock.run_for(50)
    assert calls == []
    page.clock.run_for(100)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
def test_CK_007_run_for_triggers_event_when_some_throw(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(() => { throw new Error(); }, 100);
      setTimeout(window.stub, 120);
    }"""
    )
    with pytest.raises(Error):
        page.clock.run_for(120)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
def test_CK_008_run_for_creates_updated_date_while_ticking(
    page: Page, calls: Calls
) -> None:
    page.clock.set_system_time(0)
    page.evaluate(
        """async () => {
      setInterval(() => {
        window.stub(new Date().getTime());
      }, 10);
    }"""
    )
    page.clock.run_for(100)
    assert calls == [
        {"params": [10]},
        {"params": [20]},
        {"params": [30]},
        {"params": [40]},
        {"params": [50]},
        {"params": [60]},
        {"params": [70]},
        {"params": [80]},
        {"params": [90]},
        {"params": [100]},
    ]


@pytest.mark.usefixtures("install_and_pause")
def test_CK_009_run_for_passes_8_seconds(page: Page, calls: Calls) -> None:
    page.evaluate(
        """async () => {
      setInterval(window.stub, 4000);
    }"""
    )
    page.clock.run_for("08")
    assert len(calls) == 2


@pytest.mark.usefixtures("install_and_pause")
def test_CK_010_run_for_passes_1_minute(page: Page, calls: Calls) -> None:
    page.evaluate(
        """async () => {
      setInterval(window.stub, 6000);
    }"""
    )
    page.clock.run_for("01:00")
    assert len(calls) == 10


@pytest.mark.usefixtures("install_and_pause")
def test_CK_011_run_for_passes_2_hours_34_minutes_and_10_seconds(
    page: Page,
    calls: Calls,
) -> None:
    page.evaluate(
        """async () => {
      setInterval(window.stub, 10000);
    }"""
    )
    start = time.monotonic()
    page.clock.run_for("02:34:10")
    assert len(calls) == 925
    # Nested setTimeout(fn, 0) is clamped to 4ms, so firing 925 timers used to take over 4 seconds.
    assert (time.monotonic() - start) * 1000 < 2000


@pytest.mark.usefixtures("install_and_pause")
def test_CK_012_run_for_throws_for_invalid_format(page: Page, calls: Calls) -> None:
    page.evaluate(
        """async () => {
      setInterval(window.stub, 10000);
    }"""
    )
    with pytest.raises(Error):
        page.clock.run_for("12:02:34:10")
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
def test_CK_013_run_for_returns_the_current_now_value(page: Page) -> None:
    page.clock.set_system_time(0)
    value = 200
    page.clock.run_for(value)
    assert page.evaluate("() => Date.now()") == value


@pytest.mark.usefixtures("install_and_pause")
def test_CK_014_fast_forward_ignores_timers_which_wouldn_t_be_run(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(() => {
        window.stub('should not be logged');
      }, 1000);
    }"""
    )
    page.clock.fast_forward(500)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
def test_CK_015_fast_forward_pushes_back_execution_time_for_skipped_timers(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(() => {
        window.stub(Date.now());
      }, 1000);
    }"""
    )
    page.clock.fast_forward(2000)
    assert calls == [{"params": [1000 + 2000]}]


@pytest.mark.usefixtures("install_and_pause")
def test_CK_016_fast_forward_supports_string_time_arguments(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(() => {
        window.stub(Date.now());
      }, 100000);  // 100000 = 1:40
    }"""
    )
    page.clock.fast_forward("01:50")
    assert calls == [{"params": [1000 + 110000]}]


@pytest.mark.usefixtures("install_and_pause")
def test_CK_017_stub_timers_sets_initial_timestamp(page: Page, calls: Calls) -> None:
    page.clock.set_system_time(1.4)
    assert page.evaluate("() => Date.now()") == 1400


@pytest.mark.usefixtures("install_and_pause")
def test_CK_018_stub_timers_should_throw_for_invalid_date(page: Page) -> None:
    # Upstream first passes new Date('invalid'); Python has no invalid datetime.
    with pytest.raises(Error) as exc_info:
        page.clock.set_system_time("invalid")
    assert "Clock.set_system_time: Invalid date: invalid" in exc_info.value.message


@pytest.mark.usefixtures("install_and_pause")
def test_CK_019_stub_timers_replaces_global_set_timeout(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setTimeout(window.stub, 1000);
    }"""
    )
    page.clock.run_for(1000)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
def test_CK_020_stub_timers_global_fake_set_timeout_should_return_id(
    page: Page, calls: Calls
) -> None:
    to = page.evaluate("() => setTimeout(window.stub, 1000)")
    assert isinstance(to, int)


@pytest.mark.usefixtures("install_and_pause")
def test_CK_021_stub_timers_replaces_global_clear_timeout(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      const to = setTimeout(window.stub, 1000);
      clearTimeout(to);
    }"""
    )
    page.clock.run_for(1000)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
def test_CK_022_stub_timers_replaces_global_set_interval(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      setInterval(window.stub, 500);
    }"""
    )
    page.clock.run_for(1000)
    assert len(calls) == 2


@pytest.mark.usefixtures("install_and_pause")
def test_CK_023_stub_timers_replaces_global_clear_interval(
    page: Page, calls: Calls
) -> None:
    page.evaluate(
        """async () => {
      const to = setInterval(window.stub, 500);
      clearInterval(to);
    }"""
    )
    page.clock.run_for(1000)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
def test_CK_024_stub_timers_replaces_global_performance_now(
    page: Page, sync_gather: Callable
) -> None:
    result, _ = sync_gather(
        lambda: page.evaluate(
            """async () => {
      const prev = performance.now();
      await new Promise(f => setTimeout(f, 1000));
      const next = performance.now();
      return { prev, next };
    }"""
        ),
        lambda: page.clock.run_for(1000),
    )
    assert result == {"prev": 1000, "next": 2000}


@pytest.mark.usefixtures("install_and_pause")
def test_CK_025_stub_timers_fakes_date_constructor(page: Page) -> None:
    now = page.evaluate("() => new Date().getTime()")
    assert now == 1000


def test_CK_026_stub_timers_replaces_global_performance_time_origin(
    page: Page, sync_gather: Callable
) -> None:
    page.clock.install(time=1)
    page.clock.pause_at(2)
    result, _ = sync_gather(
        lambda: page.evaluate(
            """async () => {
      const prev = performance.now();
      await new Promise(f => setTimeout(f, 1000));
      const next = performance.now();
      return { prev, next };
    }"""
        ),
        lambda: page.clock.run_for(1000),
    )
    assert page.evaluate("() => performance.timeOrigin") == 1000
    assert result == {"prev": 1000, "next": 2000}


def test_CK_027_popup_should_tick_after_popup(page: Page) -> None:
    page.clock.install(time=0)
    now = datetime.datetime(2015, 9, 25, tzinfo=datetime.timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    page.clock.pause_at(now)
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank')")
    popup = popup_info.value
    popup_time = popup.evaluate("() => Date.now()")
    assert popup_time == now_ms
    page.clock.run_for(1000)
    popup_time_after = popup.evaluate("() => Date.now()")
    assert popup_time_after == now_ms + 1000


def test_CK_028_popup_should_tick_before_popup(page: Page) -> None:
    page.clock.install(time=0)
    now = datetime.datetime(2015, 9, 25, tzinfo=datetime.timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    page.clock.pause_at(now)
    page.clock.run_for(1000)

    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank')")
    popup = popup_info.value
    popup_time = popup.evaluate("() => Date.now()")
    assert popup_time == now_ms + 1000


def test_CK_029_popup_should_run_time_before_popup(page: Page, server: Server) -> None:
    _popup_route(server)
    page.goto(server.EMPTY_PAGE)
    # Wait for 2 second in real life to check that it is past in popup.
    page.wait_for_timeout(2000)
    with page.expect_popup() as popup_info:
        page.evaluate("url => window.open(url)", server.PREFIX + "/popup.html")
    popup = popup_info.value
    popup_time = popup.evaluate("time")
    assert popup_time >= 2000


def test_CK_030_popup_should_not_run_time_before_popup_on_pause(
    page: Page, server: Server
) -> None:
    _popup_route(server)
    page.clock.install(time=0)
    page.clock.pause_at(1)
    page.goto(server.EMPTY_PAGE)
    # Wait for 2 second in real life to check that it is past in popup.
    page.wait_for_timeout(2000)
    with page.expect_popup() as popup_info:
        page.evaluate("url => window.open(url)", server.PREFIX + "/popup.html")
    popup = popup_info.value
    popup.wait_for_load_state()
    popup_time = popup.evaluate("time")
    assert popup_time == 1000


def test_CK_031_set_fixed_time_does_not_fake_methods(page: Page) -> None:
    page.clock.set_fixed_time(0)

    # Should not stall.
    page.evaluate("() => new Promise(f => setTimeout(f, 1))")


def test_CK_032_set_fixed_time_allows_setting_time_multiple_times(
    page: Page,
) -> None:
    page.clock.set_fixed_time(0.1)
    assert page.evaluate("() => Date.now()") == 100
    page.clock.set_fixed_time(0.2)
    assert page.evaluate("() => Date.now()") == 200


def test_CK_033_set_fixed_time_fixed_time_is_not_affected_by_clock_manipulation(
    page: Page,
) -> None:
    page.clock.set_fixed_time(0.1)
    assert page.evaluate("() => Date.now()") == 100
    page.clock.fast_forward(20)
    assert page.evaluate("() => Date.now()") == 100


def test_CK_034_set_fixed_time_allows_installing_fake_timers_after_settings_time(
    page: Page, calls: Calls
) -> None:
    page.clock.set_fixed_time(0.1)
    assert page.evaluate("() => Date.now()") == 100
    page.clock.set_fixed_time(0.2)
    page.evaluate(
        """async () => {
      setTimeout(() => window.stub(Date.now()));
    }"""
    )
    page.clock.run_for(0)
    assert calls == [{"params": [200]}]


def test_CK_035_while_running_should_progress_time(page: Page) -> None:
    page.clock.install(time=0)
    start_real_time = time.time() * 1000
    page.goto("data:text/html,")
    page.wait_for_timeout(1000)
    now = page.evaluate("() => Date.now()")
    real_elapsed = time.time() * 1000 - start_real_time
    assert now >= 1000
    assert now <= real_elapsed + 1000


def test_CK_036_while_running_should_run_for(page: Page) -> None:
    page.clock.install(time=0)
    start_real_time = time.time() * 1000
    page.goto("data:text/html,")
    page.clock.run_for(10000)
    now = page.evaluate("() => Date.now()")
    real_elapsed = time.time() * 1000 - start_real_time
    assert now >= 10000
    assert now <= 10000 + real_elapsed + 1000


def test_CK_037_while_running_should_fast_forward(page: Page) -> None:
    page.clock.install(time=0)
    start_real_time = time.time() * 1000
    page.goto("data:text/html,")
    page.clock.fast_forward(10000)
    now = page.evaluate("() => Date.now()")
    real_elapsed = time.time() * 1000 - start_real_time
    assert now >= 10000
    assert now <= 10000 + real_elapsed + 1000


def test_CK_038_while_running_should_pause(page: Page) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(60)
    # Internally wait to make sure the clock is paused and not running.
    page.wait_for_timeout(1111)
    now = page.evaluate("() => Date.now()")
    assert now == 60000


def test_CK_039_while_running_should_reject_an_invalid_target_time_with_an_active_request_animation_frame_loop(
    page: Page,
) -> None:
    page.clock.install()
    page.set_content(
        "<script>function tick() { requestAnimationFrame(tick); } requestAnimationFrame(tick);</script>"
    )
    date_now = page.evaluate("() => Date.now()")
    invalid_time = date_now * 1_000_000
    with pytest.raises(Error) as exc_info:
        # pause_at takes seconds: date_now * 1000 seconds is invalid_time milliseconds.
        page.clock.pause_at(date_now * 1000)
    assert f"Clock.pause_at: Invalid date: {invalid_time}" in exc_info.value.message


def test_CK_040_while_running_should_pause_and_fast_forward(page: Page) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(60)
    page.clock.fast_forward(1000)
    now = page.evaluate("() => Date.now()")
    assert now == 61000


def test_CK_041_while_running_should_set_system_time_on_pause(
    page: Page,
) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(60)
    now = page.evaluate("() => Date.now()")
    assert now == 60000


def test_CK_042_while_on_pause_fast_forward_should_not_run_nested_immediate(
    page: Page, calls: Calls
) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(1)
    page.evaluate(
        """() => {
      setTimeout(() => {
        window.stub('outer');
        setTimeout(() => window.stub('inner'), 0);
      }, 1000);
    }"""
    )
    page.clock.fast_forward(1000)
    assert calls == [{"params": ["outer"]}]
    page.clock.fast_forward(1)
    assert calls == [{"params": ["outer"]}, {"params": ["inner"]}]


def test_CK_043_while_on_pause_run_for_should_not_run_nested_immediate(
    page: Page, calls: Calls
) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(1)
    page.evaluate(
        """() => {
      setTimeout(() => {
        window.stub('outer');
        setTimeout(() => window.stub('inner'), 0);
      }, 1000);
    }"""
    )
    page.clock.run_for(1000)
    assert calls == [{"params": ["outer"]}]
    page.clock.run_for(1)
    assert calls == [{"params": ["outer"]}, {"params": ["inner"]}]


def test_CK_044_while_on_pause_run_for_should_not_run_nested_immediate_from_microtask(
    page: Page, calls: Calls
) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(1)
    page.evaluate(
        """() => {
      setTimeout(() => {
        window.stub('outer');
        void Promise.resolve().then(() => setTimeout(() => window.stub('inner'), 0));
      }, 1000);
    }"""
    )
    page.clock.run_for(1000)
    assert calls == [{"params": ["outer"]}]
    page.clock.run_for(1)
    assert calls == [{"params": ["outer"]}, {"params": ["inner"]}]


def test_CK_045_while_on_pause_should_stay_paused_on_the_next_page_when_an_init_script_reads_the_time(
    page: Page, server: Server
) -> None:
    page.clock.install(time=0)
    page.clock.pause_at(1)
    page.add_init_script("(() => Date.now())()")
    page.goto(server.EMPTY_PAGE)
    page.clock.run_for(1000)
    page.goto(server.PREFIX + "/title.html")
    assert page.evaluate("() => Date.now()") == 2000
    page.wait_for_timeout(500)
    assert page.evaluate("() => Date.now()") == 2000


def test_CK_046_while_on_pause_should_not_advance_performance_now_before_the_first_clock_call_on_a_new_page(
    page: Page, server: Server
) -> None:
    page.clock.pause_at(1)
    page.goto(server.EMPTY_PAGE)
    page.wait_for_timeout(500)
    assert page.evaluate("() => [performance.now(), Date.now()]") == [0, 1000]


def test_CK_047_date_now_check_date_now_is_an_integer(page: Page) -> None:
    page.clock.install()
    page.goto("data:text/html,")
    page.wait_for_timeout(1000)
    date_value = page.evaluate("Date.now()")
    assert isinstance(date_value, int)
    page.wait_for_timeout(1000)
    date_value2 = page.evaluate("Date.now()")
    assert isinstance(date_value2, int)


@pytest.fixture
def skip_without_temporal(page: Page) -> None:
    # The beforeEach of the Temporal.Now describe.
    if not page.evaluate("() => 'Temporal' in globalThis"):
        pytest.skip("Temporal is not supported")


@pytest.mark.usefixtures("skip_without_temporal")
def test_CK_049_temporal_now_should_follow_fixed_time(page: Page) -> None:
    page.clock.set_fixed_time(
        datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    )
    page.goto("data:text/html,")
    assert (
        page.evaluate(
            """() => {
      const Temporal = globalThis.Temporal;
      return {
        instant: Temporal.Now.instant().toString(),
        zonedDateTime: Temporal.Now.zonedDateTimeISO('UTC').toString(),
        plainDateTime: Temporal.Now.plainDateTimeISO('UTC').toString(),
        plainDate: Temporal.Now.plainDateISO('UTC').toString(),
        plainTime: Temporal.Now.plainTimeISO('UTC').toString(),
      };
    }"""
        )
        == {
            "instant": "2020-01-01T00:00:00Z",
            "zonedDateTime": "2020-01-01T00:00:00+00:00[UTC]",
            "plainDateTime": "2020-01-01T00:00:00",
            "plainDate": "2020-01-01",
            "plainTime": "00:00:00",
        }
    )


@pytest.mark.usefixtures("skip_without_temporal")
def test_CK_050_temporal_now_should_advance_with_the_clock(page: Page) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    page.clock.pause_at(1)
    page.clock.run_for(2000)
    assert (
        page.evaluate("() => globalThis.Temporal.Now.instant().epochMilliseconds")
        == 3000
    )


@pytest.mark.usefixtures("skip_without_temporal")
def test_CK_051_temporal_now_should_use_the_system_time_zone_by_default(
    browser: Browser,
) -> None:
    context = browser.new_context(timezone_id="America/Los_Angeles")
    page = context.new_page()
    page.clock.set_fixed_time(
        datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    )
    page.goto("data:text/html,")
    assert (
        page.evaluate(
            """() => {
      const Temporal = globalThis.Temporal;
      return {
        timeZoneId: Temporal.Now.timeZoneId(),
        zonedDateTime: Temporal.Now.zonedDateTimeISO().toString(),
        plainDateTime: Temporal.Now.plainDateTimeISO().toString(),
      };
    }"""
        )
        == {
            "timeZoneId": "America/Los_Angeles",
            "zonedDateTime": "2019-12-31T16:00:00-08:00[America/Los_Angeles]",
            "plainDateTime": "2019-12-31T16:00:00",
        }
    )
    context.close()


@pytest.mark.usefixtures("skip_without_temporal")
def test_CK_052_temporal_now_should_keep_the_rest_of_temporal_intact(
    page: Page,
) -> None:
    page.clock.install(time=0)
    page.goto("data:text/html,")
    assert (
        page.evaluate(
            """() => {
      const Temporal = globalThis.Temporal;
      return {
        tag: Object.prototype.toString.call(Temporal.Now),
        enumerable: Object.keys(Temporal).concat(Object.keys(Temporal.Now)),
        isInstant: Temporal.Now.instant() instanceof Temporal.Instant,
        duration: Temporal.Duration.from({ hours: 1 }).toString(),
      };
    }"""
        )
        == {
            "tag": "[object Temporal.Now]",
            "enumerable": [],
            "isInstant": True,
            "duration": "PT1H",
        }
    )


def test_CK_053_abort_signal_timeout(page: Page, browser_name: str) -> None:
    page.clock.install(time=0)
    controller = page.evaluate_handle(
        """() => {
      const signal = AbortSignal.any([
        AbortSignal.timeout(100)
      ]);
      const handle = {
        signal,
        event: false,
        handler: false,
      };
      signal.addEventListener('abort', () => handle.event = true);
      signal.onabort = () => handle.handler = true;
      return handle;
    }"""
    )
    assert (
        controller.evaluate(
            """handle => ({
      signal: handle.signal.aborted,
      event: handle.event,
      handler: handle.handler,
    })"""
        )
        == {
            "signal": False,
            "event": False,
            "handler": False,
        }
    )
    page.clock.run_for(200)
    assert (
        controller.evaluate(
            """handle => ({
      signal: handle.signal.aborted,
      event: handle.event,
      handler: handle.handler,
      reason: {
        name: handle.signal.reason.name,
        message: handle.signal.reason.message,
        code: handle.signal.reason.code,
      },
    })"""
        )
        == {
            "signal": True,
            "event": True,
            "handler": True,
            "reason": {
                "name": "TimeoutError",
                "message": (
                    "signal timed out"
                    if browser_name == "chromium"
                    else "The operation timed out."
                ),
                "code": 23,
            },
        }
    )
    assert page.evaluate("() => AbortSignal.abort().aborted") is True


def test_CK_054_correctly_increments_date_now_performance_now_during_blocking_execution(
    page: Page, server: Server
) -> None:
    page.clock.set_system_time(
        datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    )

    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""
      <html>
        <body>
          <script>
          {
            const start = performance.now();
            while (performance.now() - start < 100) { }
          }
          {
            const start = Date.now();
            while (Date.now() - start < 100) { }
          }
          console.log('done');
          </script>
        </body>
      </html>
    """
        )
        request.finish()

    server.set_route("/repro.html", handler)
    with page.expect_console_message(lambda msg: msg.text == "done"):
        page.goto(server.PREFIX + "/repro.html")
