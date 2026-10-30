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

import asyncio
import datetime
import os
import time
from typing import Any, Dict, List

import pytest

from playwright.async_api import Browser, Error, Page
from tests.server import Server, TestServerRequest

# Upstream skips this file when PW_CLOCK installs a clock in every context.
pytestmark = pytest.mark.skipif(bool(os.environ.get("PW_CLOCK")), reason="PW_CLOCK")

Calls = List[Dict[str, List[Any]]]


@pytest.fixture
async def calls(page: Page) -> Calls:
    calls: Calls = []
    await page.expose_function(
        "stub", lambda *params: calls.append({"params": list(params)})
    )
    return calls


@pytest.fixture
async def install_and_pause(page: Page) -> None:
    # The beforeEach of the runFor, fastForward and stubTimers describes.
    await page.clock.install(time=0)
    await page.clock.pause_at(1)


def _popup_route(server: Server) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(b"<script>window.time = Date.now()</script>")
        request.finish()

    server.set_route("/popup.html", handler)


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_001_run_for_triggers_immediately_without_specified_delay(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub);
    }"""
    )
    await page.clock.run_for(0)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_002_run_for_does_not_trigger_without_sufficient_delay(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
    }"""
    )
    await page.clock.run_for(10)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_003_run_for_triggers_after_sufficient_delay(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
    }"""
    )
    await page.clock.run_for(100)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_004_run_for_triggers_simultaneous_timers(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
      setTimeout(window.stub, 100);
    }"""
    )
    await page.clock.run_for(100)
    assert len(calls) == 2


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_005_run_for_triggers_multiple_simultaneous_timers(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub, 100);
      setTimeout(window.stub, 100);
      setTimeout(window.stub, 99);
      setTimeout(window.stub, 100);
    }"""
    )
    await page.clock.run_for(100)
    assert len(calls) == 4


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_006_run_for_waits_after_set_timeout_was_called(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub, 150);
    }"""
    )
    await page.clock.run_for(50)
    assert calls == []
    await page.clock.run_for(100)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_007_run_for_triggers_event_when_some_throw(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(() => { throw new Error(); }, 100);
      setTimeout(window.stub, 120);
    }"""
    )
    with pytest.raises(Error):
        await page.clock.run_for(120)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_008_run_for_creates_updated_date_while_ticking(
    page: Page, calls: Calls
) -> None:
    await page.clock.set_system_time(0)
    await page.evaluate(
        """async () => {
      setInterval(() => {
        window.stub(new Date().getTime());
      }, 10);
    }"""
    )
    await page.clock.run_for(100)
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
async def test_CK_009_run_for_passes_8_seconds(page: Page, calls: Calls) -> None:
    await page.evaluate(
        """async () => {
      setInterval(window.stub, 4000);
    }"""
    )
    await page.clock.run_for("08")
    assert len(calls) == 2


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_010_run_for_passes_1_minute(page: Page, calls: Calls) -> None:
    await page.evaluate(
        """async () => {
      setInterval(window.stub, 6000);
    }"""
    )
    await page.clock.run_for("01:00")
    assert len(calls) == 10


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_011_run_for_passes_2_hours_34_minutes_and_10_seconds(
    page: Page,
    calls: Calls,
) -> None:
    await page.evaluate(
        """async () => {
      setInterval(window.stub, 10000);
    }"""
    )
    await page.clock.run_for("02:34:10")
    assert len(calls) == 925


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_012_run_for_throws_for_invalid_format(
    page: Page, calls: Calls, server: Server
) -> None:
    await page.evaluate(
        """async () => {
      setInterval(window.stub, 10000);
    }"""
    )
    with pytest.raises(Error):
        await page.clock.run_for("12:02:34:10")
    with pytest.raises(Error, match="Clock.run_for: Invalid ticks: NaN"):
        await page.clock.run_for(float("nan"))  # type: ignore[arg-type]
    with pytest.raises(Error, match="Clock.fast_forward: Invalid ticks: Infinity"):
        await page.clock.fast_forward(float("inf"))  # type: ignore[arg-type]
    assert calls == []
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("() => Date.now()") == 1000


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_013_run_for_returns_the_current_now_value(page: Page) -> None:
    await page.clock.set_system_time(0)
    value = 200
    await page.clock.run_for(value)
    assert await page.evaluate("() => Date.now()") == value


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_014_fast_forward_ignores_timers_which_wouldn_t_be_run(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(() => {
        window.stub('should not be logged');
      }, 1000);
    }"""
    )
    await page.clock.fast_forward(500)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_015_fast_forward_pushes_back_execution_time_for_skipped_timers(
    page: Page, calls: Calls, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
      setTimeout(() => {
        window.stub(Date.now());
      }, 1000);
    }"""
    )
    fifty_days = 50 * 24 * 60 * 60 * 1000
    await page.clock.fast_forward(fifty_days)
    assert calls == [{"params": [1000 + fifty_days]}]
    assert await page.evaluate("() => Date.now()") == 1000 + fifty_days
    await page.reload()
    assert await page.evaluate("() => Date.now()") == 1000 + fifty_days


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_016_fast_forward_supports_string_time_arguments(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(() => {
        window.stub(Date.now());
      }, 100000);  // 100000 = 1:40
    }"""
    )
    await page.clock.fast_forward("01:50")
    assert calls == [{"params": [1000 + 110000]}]


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_017_stub_timers_sets_initial_timestamp(
    page: Page, calls: Calls
) -> None:
    await page.clock.set_system_time(1.4)
    assert await page.evaluate("() => Date.now()") == 1400


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_018_stub_timers_should_throw_for_invalid_date(page: Page) -> None:
    # Upstream first passes new Date('invalid'); Python has no invalid datetime.
    with pytest.raises(Error) as exc_info:
        await page.clock.set_system_time("invalid")
    assert "Clock.set_system_time: Invalid date: invalid" in exc_info.value.message


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_019_stub_timers_replaces_global_set_timeout(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setTimeout(window.stub, 1000);
    }"""
    )
    await page.clock.run_for(1000)
    assert len(calls) == 1


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_020_stub_timers_global_fake_set_timeout_should_return_id(
    page: Page, calls: Calls
) -> None:
    to = await page.evaluate("() => setTimeout(window.stub, 1000)")
    assert isinstance(to, int)


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_021_stub_timers_replaces_global_clear_timeout(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      const to = setTimeout(window.stub, 1000);
      clearTimeout(to);
    }"""
    )
    await page.clock.run_for(1000)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_022_stub_timers_replaces_global_set_interval(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      setInterval(window.stub, 500);
    }"""
    )
    await page.clock.run_for(1000)
    assert len(calls) == 2


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_023_stub_timers_replaces_global_clear_interval(
    page: Page, calls: Calls
) -> None:
    await page.evaluate(
        """async () => {
      const to = setInterval(window.stub, 500);
      clearInterval(to);
    }"""
    )
    await page.clock.run_for(1000)
    assert calls == []


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_024_stub_timers_replaces_global_performance_now(
    page: Page,
) -> None:
    result, _ = await asyncio.gather(
        page.evaluate(
            """async () => {
      const prev = performance.now();
      await new Promise(f => setTimeout(f, 1000));
      const next = performance.now();
      return { prev, next };
    }"""
        ),
        page.clock.run_for(1000),
    )
    assert result == {"prev": 1000, "next": 2000}


@pytest.mark.usefixtures("install_and_pause")
async def test_CK_025_stub_timers_fakes_date_constructor(page: Page) -> None:
    now = await page.evaluate("() => new Date().getTime()")
    assert now == 1000


async def test_CK_026_stub_timers_replaces_global_performance_time_origin(
    page: Page,
) -> None:
    await page.clock.install(time=1)
    await page.clock.pause_at(2)
    result, _ = await asyncio.gather(
        page.evaluate(
            """async () => {
      const prev = performance.now();
      await new Promise(f => setTimeout(f, 1000));
      const next = performance.now();
      return { prev, next };
    }"""
        ),
        page.clock.run_for(1000),
    )
    assert await page.evaluate("() => performance.timeOrigin") == 1000
    assert result == {"prev": 1000, "next": 2000}


async def test_CK_027_popup_should_tick_after_popup(page: Page) -> None:
    await page.clock.install(time=0)
    now = datetime.datetime(2015, 9, 25, tzinfo=datetime.timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    await page.clock.pause_at(now)
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('about:blank')")
    popup = await popup_info.value
    popup_time = await popup.evaluate("() => Date.now()")
    assert popup_time == now_ms
    await page.clock.run_for(1000)
    popup_time_after = await popup.evaluate("() => Date.now()")
    assert popup_time_after == now_ms + 1000


async def test_CK_028_popup_should_tick_before_popup(page: Page) -> None:
    await page.clock.install(time=0)
    now = datetime.datetime(2015, 9, 25, tzinfo=datetime.timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    await page.clock.pause_at(now)
    await page.clock.run_for(1000)

    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('about:blank')")
    popup = await popup_info.value
    popup_time = await popup.evaluate("() => Date.now()")
    assert popup_time == now_ms + 1000


async def test_CK_029_popup_should_run_time_before_popup(
    page: Page, server: Server
) -> None:
    _popup_route(server)
    await page.goto(server.EMPTY_PAGE)
    # Wait for 2 second in real life to check that it is past in popup.
    await page.wait_for_timeout(2000)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => window.open(url)", server.PREFIX + "/popup.html")
    popup = await popup_info.value
    popup_time = await popup.evaluate("time")
    assert popup_time >= 2000


async def test_CK_030_popup_should_not_run_time_before_popup_on_pause(
    page: Page, server: Server
) -> None:
    _popup_route(server)
    await page.clock.install(time=0)
    await page.clock.pause_at(1)
    await page.goto(server.EMPTY_PAGE)
    # Wait for 2 second in real life to check that it is past in popup.
    await page.wait_for_timeout(2000)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => window.open(url)", server.PREFIX + "/popup.html")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    popup_time = await popup.evaluate("time")
    assert popup_time == 1000


async def test_CK_031_set_fixed_time_does_not_fake_methods(page: Page) -> None:
    await page.clock.set_fixed_time(0)

    # Should not stall.
    await page.evaluate("() => new Promise(f => setTimeout(f, 1))")


async def test_CK_032_set_fixed_time_allows_setting_time_multiple_times(
    page: Page,
) -> None:
    await page.clock.set_fixed_time(0.1)
    assert await page.evaluate("() => Date.now()") == 100
    await page.clock.set_fixed_time(0.2)
    assert await page.evaluate("() => Date.now()") == 200


async def test_CK_033_set_fixed_time_fixed_time_is_not_affected_by_clock_manipulation(
    page: Page,
) -> None:
    await page.clock.set_fixed_time(0.1)
    assert await page.evaluate("() => Date.now()") == 100
    await page.clock.fast_forward(20)
    assert await page.evaluate("() => Date.now()") == 100


async def test_CK_034_set_fixed_time_allows_installing_fake_timers_after_settings_time(
    page: Page, calls: Calls
) -> None:
    await page.clock.set_fixed_time(0.1)
    assert await page.evaluate("() => Date.now()") == 100
    await page.clock.set_fixed_time(0.2)
    await page.evaluate(
        """async () => {
      setTimeout(() => window.stub(Date.now()));
    }"""
    )
    await page.clock.run_for(0)
    assert calls == [{"params": [200]}]


async def test_CK_035_while_running_should_progress_time(page: Page) -> None:
    await page.clock.install(time=0)
    start_real_time = time.time() * 1000
    await page.goto("data:text/html,")
    await page.wait_for_timeout(1000)
    now = await page.evaluate("() => Date.now()")
    real_elapsed = time.time() * 1000 - start_real_time
    assert now >= 1000
    assert now <= real_elapsed + 1000


async def test_CK_036_while_running_should_run_for(page: Page) -> None:
    await page.clock.install(time=0)
    start_real_time = time.time() * 1000
    await page.goto("data:text/html,")
    await page.clock.run_for(10000)
    now = await page.evaluate("() => Date.now()")
    real_elapsed = time.time() * 1000 - start_real_time
    assert now >= 10000
    assert now <= 10000 + real_elapsed + 1000


async def test_CK_037_while_running_should_fast_forward(page: Page) -> None:
    await page.clock.install(time=0)
    start_real_time = time.time() * 1000
    await page.goto("data:text/html,")
    await page.clock.fast_forward(10000)
    now = await page.evaluate("() => Date.now()")
    real_elapsed = time.time() * 1000 - start_real_time
    assert now >= 10000
    assert now <= 10000 + real_elapsed + 1000


async def test_CK_038_while_running_should_pause(page: Page) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(60)
    # Internally wait to make sure the clock is paused and not running.
    await page.wait_for_timeout(1111)
    now = await page.evaluate("() => Date.now()")
    assert now == 60000


async def test_CK_039_while_running_should_reject_an_invalid_target_time_with_an_active_request_animation_frame_loop(
    page: Page,
) -> None:
    await page.clock.install()
    await page.set_content(
        "<script>function tick() { requestAnimationFrame(tick); } requestAnimationFrame(tick);</script>"
    )
    date_now = await page.evaluate("() => Date.now()")
    invalid_time = date_now * 1_000_000
    with pytest.raises(Error) as exc_info:
        # pause_at takes seconds: date_now * 1000 seconds is invalid_time milliseconds.
        await page.clock.pause_at(date_now * 1000)
    assert f"Clock.pause_at: Invalid date: {invalid_time}" in exc_info.value.message


async def test_CK_040_while_running_should_pause_and_fast_forward(page: Page) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(60)
    await page.clock.fast_forward(1000)
    now = await page.evaluate("() => Date.now()")
    assert now == 61000


async def test_CK_041_while_running_should_set_system_time_on_pause(
    page: Page,
) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(60)
    now = await page.evaluate("() => Date.now()")
    assert now == 60000


async def test_CK_042_while_on_pause_fast_forward_should_not_run_nested_immediate(
    page: Page, calls: Calls
) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(1)
    await page.evaluate(
        """() => {
      setTimeout(() => {
        window.stub('outer');
        setTimeout(() => window.stub('inner'), 0);
      }, 1000);
    }"""
    )
    await page.clock.fast_forward(1000)
    assert calls == [{"params": ["outer"]}]
    await page.clock.fast_forward(1)
    assert calls == [{"params": ["outer"]}, {"params": ["inner"]}]


async def test_CK_043_while_on_pause_run_for_should_not_run_nested_immediate(
    page: Page, calls: Calls
) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(1)
    await page.evaluate(
        """() => {
      setTimeout(() => {
        window.stub('outer');
        setTimeout(() => window.stub('inner'), 0);
      }, 1000);
    }"""
    )
    await page.clock.run_for(1000)
    assert calls == [{"params": ["outer"]}]
    await page.clock.run_for(1)
    assert calls == [{"params": ["outer"]}, {"params": ["inner"]}]


async def test_CK_044_while_on_pause_run_for_should_not_run_nested_immediate_from_microtask(
    page: Page, calls: Calls
) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(1)
    await page.evaluate(
        """() => {
      setTimeout(() => {
        window.stub('outer');
        void Promise.resolve().then(() => setTimeout(() => window.stub('inner'), 0));
      }, 1000);
    }"""
    )
    await page.clock.run_for(1000)
    assert calls == [{"params": ["outer"]}]
    await page.clock.run_for(1)
    assert calls == [{"params": ["outer"]}, {"params": ["inner"]}]


async def test_CK_045_while_on_pause_should_stay_paused_on_the_next_page_when_an_init_script_reads_the_time(
    page: Page, server: Server
) -> None:
    await page.clock.install(time=0)
    await page.clock.pause_at(1)
    await page.add_init_script("(() => Date.now())()")
    await page.goto(server.EMPTY_PAGE)
    await page.clock.run_for(1000)
    await page.goto(server.PREFIX + "/title.html")
    assert await page.evaluate("() => Date.now()") == 2000
    await page.wait_for_timeout(500)
    assert await page.evaluate("() => Date.now()") == 2000


async def test_CK_046_while_on_pause_should_not_advance_performance_now_before_the_first_clock_call_on_a_new_page(
    page: Page, server: Server
) -> None:
    await page.clock.pause_at(1)
    await page.goto(server.EMPTY_PAGE)
    await page.wait_for_timeout(500)
    assert await page.evaluate("() => [performance.now(), Date.now()]") == [0, 1000]


async def test_CK_047_date_now_check_date_now_is_an_integer(page: Page) -> None:
    await page.clock.install()
    await page.goto("data:text/html,")
    await page.wait_for_timeout(1000)
    date_value = await page.evaluate("Date.now()")
    assert isinstance(date_value, int)
    await page.wait_for_timeout(1000)
    date_value2 = await page.evaluate("Date.now()")
    assert isinstance(date_value2, int)


@pytest.fixture
async def skip_without_temporal(page: Page) -> None:
    # The beforeEach of the Temporal.Now describe.
    if not await page.evaluate("() => 'Temporal' in globalThis"):
        pytest.skip("Temporal is not supported")


@pytest.mark.usefixtures("skip_without_temporal")
async def test_CK_049_temporal_now_should_follow_fixed_time(page: Page) -> None:
    await page.clock.set_fixed_time(
        datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    )
    await page.goto("data:text/html,")
    assert (
        await page.evaluate(
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
async def test_CK_050_temporal_now_should_advance_with_the_clock(page: Page) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    await page.clock.pause_at(1)
    await page.clock.run_for(2000)
    assert (
        await page.evaluate("() => globalThis.Temporal.Now.instant().epochMilliseconds")
        == 3000
    )


@pytest.mark.usefixtures("skip_without_temporal")
async def test_CK_051_temporal_now_should_use_the_system_time_zone_by_default(
    browser: Browser,
) -> None:
    context = await browser.new_context(timezone_id="America/Los_Angeles")
    page = await context.new_page()
    await page.clock.set_fixed_time(
        datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    )
    await page.goto("data:text/html,")
    assert (
        await page.evaluate(
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
    await context.close()


@pytest.mark.usefixtures("skip_without_temporal")
async def test_CK_052_temporal_now_should_keep_the_rest_of_temporal_intact(
    page: Page,
) -> None:
    await page.clock.install(time=0)
    await page.goto("data:text/html,")
    assert (
        await page.evaluate(
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


async def test_CK_053_abort_signal_timeout(page: Page, browser_name: str) -> None:
    await page.clock.install(time=0)
    controller = await page.evaluate_handle(
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
        await controller.evaluate(
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
    await page.clock.run_for(200)
    assert (
        await controller.evaluate(
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
    assert await page.evaluate("() => AbortSignal.abort().aborted") is True


async def test_CK_054_correctly_increments_date_now_performance_now_during_blocking_execution(
    page: Page, server: Server
) -> None:
    await page.clock.set_system_time(
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
    async with page.expect_console_message(lambda msg: msg.text == "done"):
        await page.goto(server.PREFIX + "/repro.html")
