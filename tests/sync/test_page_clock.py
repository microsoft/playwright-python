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

import datetime
from typing import Any, Generator, List

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


@pytest.fixture(autouse=True)
def calls(page: Page) -> List[Any]:
    calls: List[Any] = []
    page.expose_function("stub", lambda *args: calls.append(list(args)))
    return calls


class TestRunFor:
    @pytest.fixture(autouse=True)
    def before_each(self, page: Page) -> Generator[None, None, None]:
        page.clock.install(time=0)
        page.clock.pause_at(1000)
        yield

    def test_run_for_triggers_immediately_without_specified_delay(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setTimeout(window.stub)")
        page.clock.run_for(0)
        assert len(calls) == 1

    def test_run_for_does_not_trigger_without_sufficient_delay(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setTimeout(window.stub, 100)")
        page.clock.run_for(10)
        assert len(calls) == 0

    def test_run_for_triggers_after_sufficient_delay(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setTimeout(window.stub, 100)")
        page.clock.run_for(100)
        assert len(calls) == 1

    def test_run_for_triggers_simultaneous_timers(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setTimeout(window.stub, 100); setTimeout(window.stub, 100)")
        page.clock.run_for(100)
        assert len(calls) == 2

    def test_run_for_triggers_multiple_simultaneous_timers(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate(
            "setTimeout(window.stub, 100); setTimeout(window.stub, 100); setTimeout(window.stub, 99); setTimeout(window.stub, 100)"
        )
        page.clock.run_for(100)
        assert len(calls) == 4

    def test_run_for_waits_after_setTimeout_was_called(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setTimeout(window.stub, 150)")
        page.clock.run_for(50)
        assert len(calls) == 0
        page.clock.run_for(100)
        assert len(calls) == 1

    def test_run_for_triggers_event_when_some_throw(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate(
            "setTimeout(() => { throw new Error(); }, 100); setTimeout(window.stub, 120)"
        )
        with pytest.raises(Error):
            page.clock.run_for(120)
        assert len(calls) == 1

    def test_run_for_creates_updated_Date_while_ticking(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.clock.set_system_time(0)
        page.evaluate("setInterval(() => { window.stub(new Date().getTime()); }, 10)")
        page.clock.run_for(100)
        assert calls == [
            [10],
            [20],
            [30],
            [40],
            [50],
            [60],
            [70],
            [80],
            [90],
            [100],
        ]

    def test_run_for_passes_8_seconds(self, page: Page, calls: List[Any]) -> None:
        page.evaluate("setInterval(window.stub, 4000)")
        page.clock.run_for("08")
        assert len(calls) == 2

    def test_run_for_passes_1_minute(self, page: Page, calls: List[Any]) -> None:
        page.evaluate("setInterval(window.stub, 6000)")
        page.clock.run_for("01:00")
        assert len(calls) == 10

    def test_run_for_passes_2_hours_34_minutes_and_10_seconds(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setInterval(window.stub, 10000)")
        page.clock.run_for("02:34:10")
        assert len(calls) == 925

    def test_run_for_throws_for_invalid_format(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setInterval(window.stub, 10000)")
        with pytest.raises(Error):
            page.clock.run_for("12:02:34:10")
        assert len(calls) == 0

    def test_run_for_returns_the_current_now_value(self, page: Page) -> None:
        page.clock.set_system_time(0)
        value = 200
        page.clock.run_for(value)
        assert page.evaluate("Date.now()") == value


class TestFastForward:
    @pytest.fixture(autouse=True)
    def before_each(self, page: Page) -> Generator[None, None, None]:
        page.clock.install(time=0)
        page.clock.pause_at(1)
        yield

    def test_ignores_timers_which_wouldnt_be_run(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate(
            "setTimeout(() => { window.stub('should not be logged'); }, 1000)"
        )
        page.clock.fast_forward(500)
        assert len(calls) == 0

    def test_pushes_back_execution_time_for_skipped_timers(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.evaluate("setTimeout(() => { window.stub(Date.now()); }, 1000)")
        page.clock.fast_forward(2000)
        assert calls == [[1000 + 2000]]

    def test_supports_string_time_arguments(self, page: Page, calls: List[Any]) -> None:
        page.evaluate(
            "setTimeout(() => { window.stub(Date.now()); }, 100000)"
        )  # 100000 = 1:40
        page.clock.fast_forward("01:50")
        assert calls == [[1000 + 110000]]


class TestStubTimers:
    @pytest.fixture(autouse=True)
    def before_each(self, page: Page) -> Generator[None, None, None]:
        page.clock.install(time=0)
        page.clock.pause_at(1)
        yield

    def test_sets_initial_timestamp(self, page: Page) -> None:
        page.clock.set_system_time(1.4)
        assert page.evaluate("Date.now()") == 1400

    def test_replaces_global_setTimeout(self, page: Page, calls: List[Any]) -> None:
        page.evaluate("setTimeout(window.stub, 1000)")
        page.clock.run_for(1000)
        assert len(calls) == 1

    def test_global_fake_setTimeout_should_return_id(self, page: Page) -> None:
        to = page.evaluate("setTimeout(window.stub, 1000)")
        assert isinstance(to, int)

    def test_replaces_global_clearTimeout(self, page: Page, calls: List[Any]) -> None:
        page.evaluate(
            """
            const to = setTimeout(window.stub, 1000);
            clearTimeout(to);
        """
        )
        page.clock.run_for(1000)
        assert len(calls) == 0

    def test_replaces_global_setInterval(self, page: Page, calls: List[Any]) -> None:
        page.evaluate("setInterval(window.stub, 500)")
        page.clock.run_for(1000)
        assert len(calls) == 2

    def test_replaces_global_clearInterval(self, page: Page, calls: List[Any]) -> None:
        page.evaluate(
            """
            const to = setInterval(window.stub, 500);
            clearInterval(to);
        """
        )
        page.clock.run_for(1000)
        assert len(calls) == 0

    def test_replaces_global_performance_now(self, page: Page) -> None:
        page.evaluate(
            """() => {
            window.waitForPromise = new Promise(async resolve => {
                const prev = performance.now();
                await new Promise(f => setTimeout(f, 1000));
                const next = performance.now();
                resolve({ prev, next });
            });
        }"""
        )
        page.clock.run_for(1000)
        assert page.evaluate("window.waitForPromise") == {"prev": 1000, "next": 2000}

    def test_fakes_Date_constructor(self, page: Page) -> None:
        now = page.evaluate("new Date().getTime()")
        assert now == 1000


class TestStubTimersPerformance:
    def test_replaces_global_performance_time_origin(self, page: Page) -> None:
        page.clock.install(time=1)
        page.clock.pause_at(2)
        page.evaluate(
            """() => {
            window.waitForPromise = new Promise(async resolve => {
                const prev = performance.now();
                await new Promise(f => setTimeout(f, 1000));
                const next = performance.now();
                resolve({ prev, next });
            });
        }"""
        )
        page.clock.run_for(1000)
        assert page.evaluate("performance.timeOrigin") == 1000
        assert page.evaluate("window.waitForPromise") == {"prev": 1000, "next": 2000}


class TestPopup:
    def test_should_tick_after_popup(self, page: Page) -> None:
        page.clock.install(time=0)
        now = datetime.datetime.fromisoformat("2015-09-25")
        page.clock.pause_at(now)
        with page.expect_popup() as popup_info:
            page.evaluate("window.open('about:blank')")
        popup = popup_info.value
        popup_time = popup.evaluate("Date.now()")
        assert popup_time == now.timestamp() * 1000
        page.clock.run_for(1000)
        popup_time_after = popup.evaluate("Date.now()")
        assert popup_time_after == now.timestamp() * 1000 + 1000

    def test_should_tick_before_popup(self, page: Page) -> None:
        page.clock.install(time=0)
        now = datetime.datetime.fromisoformat("2015-09-25")
        page.clock.pause_at(now)
        page.clock.run_for(1000)
        with page.expect_popup() as popup_info:
            page.evaluate("window.open('about:blank')")
        popup = popup_info.value
        popup_time = popup.evaluate("Date.now()")
        assert popup_time == int(now.timestamp() * 1_000 + 1000)
        assert datetime.datetime.fromtimestamp(popup_time / 1_000).year == 2015

    def test_should_run_time_before_popup(self, page: Page, server: Server) -> None:
        server.set_route(
            "/popup.html",
            lambda res: (
                res.setHeader("Content-Type", "text/html"),
                res.write(b"<script>window.time = Date.now()</script>"),
                res.finish(),
            ),
        )
        page.goto(server.EMPTY_PAGE)
        # Wait for 2 second in real life to check that it is past in popup.
        page.wait_for_timeout(2000)
        with page.expect_popup() as popup_info:
            page.evaluate("window.open('{}')".format(server.PREFIX + "/popup.html"))
        popup = popup_info.value
        popup_time = popup.evaluate("window.time")
        assert popup_time >= 2000

    def test_should_not_run_time_before_popup_on_pause(
        self, page: Page, server: Server
    ) -> None:
        server.set_route(
            "/popup.html",
            lambda res: (
                res.setHeader("Content-Type", "text/html"),
                res.write(b"<script>window.time = Date.now()</script>"),
                res.finish(),
            ),
        )
        page.clock.install(time=0)
        page.clock.pause_at(1)
        page.goto(server.EMPTY_PAGE)
        # Wait for 2 second in real life to check that it is past in popup.
        page.wait_for_timeout(2000)
        with page.expect_popup() as popup_info:
            page.evaluate("window.open('{}')".format(server.PREFIX + "/popup.html"))
        popup = popup_info.value
        popup_time = popup.evaluate("window.time")
        assert popup_time == 1000


class TestSetFixedTime:
    def test_allows_passing_as_int(self, page: Page) -> None:
        page.clock.set_fixed_time(1)
        assert page.evaluate("Date.now()") == 1000
        page.clock.set_fixed_time(int(2))
        assert page.evaluate("Date.now()") == 2000

    def test_does_not_fake_methods(self, page: Page) -> None:
        page.clock.set_fixed_time(0)
        # Should not stall.
        page.evaluate("new Promise(f => setTimeout(f, 1))")

    def test_allows_setting_time_multiple_times(self, page: Page) -> None:
        page.clock.set_fixed_time(0.1)
        assert page.evaluate("Date.now()") == 100
        page.clock.set_fixed_time(0.2)
        assert page.evaluate("Date.now()") == 200

    def test_fixed_time_is_not_affected_by_clock_manipulation(self, page: Page) -> None:
        page.clock.set_fixed_time(0.1)
        assert page.evaluate("Date.now()") == 100
        page.clock.fast_forward(20)
        assert page.evaluate("Date.now()") == 100

    def test_allows_installing_fake_timers_after_setting_time(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.clock.set_fixed_time(0.1)
        assert page.evaluate("Date.now()") == 100
        page.clock.set_fixed_time(0.2)
        page.evaluate("setTimeout(() => window.stub(Date.now()))")
        page.clock.run_for(0)
        assert calls == [[200]]


class TestWhileRunning:
    def test_should_progress_time(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.wait_for_timeout(1000)
        now = page.evaluate("Date.now()")
        assert 1000 <= now <= 2000

    def test_should_run_for(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.run_for(10000)
        now = page.evaluate("Date.now()")
        assert 10000 <= now <= 11000

    def test_should_fast_forward(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.fast_forward(10000)
        now = page.evaluate("Date.now()")
        assert 10000 <= now <= 11000

    def test_should_fast_forward_to(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.fast_forward(10000)
        now = page.evaluate("Date.now()")
        assert 10000 <= now <= 11000

    def test_should_pause(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.pause_at(1)
        page.wait_for_timeout(1000)
        page.clock.resume()
        now = page.evaluate("Date.now()")
        assert 0 <= now <= 1000

    def test_should_pause_and_fast_forward(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.pause_at(1)
        page.clock.fast_forward(1000)
        now = page.evaluate("Date.now()")
        assert now == 2000

    def test_should_set_system_time_on_pause(self, page: Page) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.pause_at(1)
        now = page.evaluate("Date.now()")
        assert now == 1000


class TestWhileOnPause:
    def test_fast_forward_should_not_run_nested_immediate(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.pause_at(1000)
        page.evaluate(
            """
            setTimeout(() => {
                window.stub('outer');
                setTimeout(() => window.stub('inner'), 0);
            }, 1000);
        """
        )
        page.clock.fast_forward(1000)
        assert calls == [["outer"]]
        page.clock.fast_forward(1)
        assert calls == [["outer"], ["inner"]]

    def test_run_for_should_not_run_nested_immediate(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.pause_at(1000)
        page.evaluate(
            """
            setTimeout(() => {
                window.stub('outer');
                setTimeout(() => window.stub('inner'), 0);
            }, 1000);
        """
        )
        page.clock.run_for(1000)
        assert calls == [["outer"]]
        page.clock.run_for(1)
        assert calls == [["outer"], ["inner"]]

    def test_run_for_should_not_run_nested_immediate_from_microtask(
        self, page: Page, calls: List[Any]
    ) -> None:
        page.clock.install(time=0)
        page.goto("data:text/html,")
        page.clock.pause_at(1000)
        page.evaluate(
            """
            setTimeout(() => {
                window.stub('outer');
                void Promise.resolve().then(() => setTimeout(() => window.stub('inner'), 0));
            }, 1000);
        """
        )
        page.clock.run_for(1000)
        assert calls == [["outer"]]
        page.clock.run_for(1)
        assert calls == [["outer"], ["inner"]]
