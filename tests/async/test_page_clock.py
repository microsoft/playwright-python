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

import asyncio
import datetime
from typing import Any, AsyncGenerator, List

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


@pytest.fixture(autouse=True)
async def calls(page: Page) -> List[Any]:
    calls: List[Any] = []
    await page.expose_function("stub", lambda *args: calls.append(list(args)))
    return calls


class TestRunFor:
    @pytest.fixture(autouse=True)
    async def before_each(self, page: Page) -> AsyncGenerator[None, None]:
        await page.clock.install(time=0)
        await page.clock.pause_at(1000)
        yield

    async def test_run_for_triggers_immediately_without_specified_delay(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setTimeout(window.stub)")
        await page.clock.run_for(0)
        assert len(calls) == 1

    async def test_run_for_does_not_trigger_without_sufficient_delay(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setTimeout(window.stub, 100)")
        await page.clock.run_for(10)
        assert len(calls) == 0

    async def test_run_for_triggers_after_sufficient_delay(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setTimeout(window.stub, 100)")
        await page.clock.run_for(100)
        assert len(calls) == 1

    async def test_run_for_triggers_simultaneous_timers(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            "setTimeout(window.stub, 100); setTimeout(window.stub, 100)"
        )
        await page.clock.run_for(100)
        assert len(calls) == 2

    async def test_run_for_triggers_multiple_simultaneous_timers(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            "setTimeout(window.stub, 100); setTimeout(window.stub, 100); setTimeout(window.stub, 99); setTimeout(window.stub, 100)"
        )
        await page.clock.run_for(100)
        assert len(calls) == 4

    async def test_run_for_waits_after_setTimeout_was_called(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setTimeout(window.stub, 150)")
        await page.clock.run_for(50)
        assert len(calls) == 0
        await page.clock.run_for(100)
        assert len(calls) == 1

    async def test_run_for_triggers_event_when_some_throw(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            "setTimeout(() => { throw new Error(); }, 100); setTimeout(window.stub, 120)"
        )
        with pytest.raises(Error):
            await page.clock.run_for(120)
        assert len(calls) == 1

    async def test_run_for_creates_updated_Date_while_ticking(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.clock.set_system_time(0)
        await page.evaluate(
            "setInterval(() => { window.stub(new Date().getTime()); }, 10)"
        )
        await page.clock.run_for(100)
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

    async def test_run_for_passes_8_seconds(self, page: Page, calls: List[Any]) -> None:
        await page.evaluate("setInterval(window.stub, 4000)")
        await page.clock.run_for("08")
        assert len(calls) == 2

    async def test_run_for_passes_1_minute(self, page: Page, calls: List[Any]) -> None:
        await page.evaluate("setInterval(window.stub, 6000)")
        await page.clock.run_for("01:00")
        assert len(calls) == 10

    async def test_run_for_passes_2_hours_34_minutes_and_10_seconds(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setInterval(window.stub, 10000)")
        await page.clock.run_for("02:34:10")
        assert len(calls) == 925

    async def test_run_for_throws_for_invalid_format(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setInterval(window.stub, 10000)")
        with pytest.raises(Error):
            await page.clock.run_for("12:02:34:10")
        assert len(calls) == 0

    async def test_run_for_returns_the_current_now_value(self, page: Page) -> None:
        await page.clock.set_system_time(0)
        value = 200
        await page.clock.run_for(value)
        assert await page.evaluate("Date.now()") == value


class TestFastForward:
    @pytest.fixture(autouse=True)
    async def before_each(self, page: Page) -> AsyncGenerator[None, None]:
        await page.clock.install(time=0)
        await page.clock.pause_at(1)
        yield

    async def test_ignores_timers_which_wouldnt_be_run(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            "setTimeout(() => { window.stub('should not be logged'); }, 1000)"
        )
        await page.clock.fast_forward(500)
        assert len(calls) == 0

    async def test_pushes_back_execution_time_for_skipped_timers(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setTimeout(() => { window.stub(Date.now()); }, 1000)")
        await page.clock.fast_forward(2000)
        assert calls == [[1000 + 2000]]

    async def test_supports_string_time_arguments(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            "setTimeout(() => { window.stub(Date.now()); }, 100000)"
        )  # 100000 = 1:40
        await page.clock.fast_forward("01:50")
        assert calls == [[1000 + 110000]]


class TestStubTimers:
    @pytest.fixture(autouse=True)
    async def before_each(self, page: Page) -> AsyncGenerator[None, None]:
        await page.clock.install(time=0)
        await page.clock.pause_at(1)
        yield

    async def test_sets_initial_timestamp(self, page: Page) -> None:
        await page.clock.set_system_time(1.4)
        assert await page.evaluate("Date.now()") == 1400

    async def test_replaces_global_setTimeout(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setTimeout(window.stub, 1000)")
        await page.clock.run_for(1000)
        assert len(calls) == 1

    async def test_global_fake_setTimeout_should_return_id(self, page: Page) -> None:
        to = await page.evaluate("setTimeout(window.stub, 1000)")
        assert isinstance(to, int)

    async def test_replaces_global_clearTimeout(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            """
            const to = setTimeout(window.stub, 1000);
            clearTimeout(to);
        """
        )
        await page.clock.run_for(1000)
        assert len(calls) == 0

    async def test_replaces_global_setInterval(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate("setInterval(window.stub, 500)")
        await page.clock.run_for(1000)
        assert len(calls) == 2

    async def test_replaces_global_clearInterval(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.evaluate(
            """
            const to = setInterval(window.stub, 500);
            clearInterval(to);
        """
        )
        await page.clock.run_for(1000)
        assert len(calls) == 0

    async def test_replaces_global_performance_now(self, page: Page) -> None:
        promise = asyncio.create_task(
            page.evaluate(
                """async () => {
            const prev = performance.now();
            await new Promise(f => setTimeout(f, 1000));
            const next = performance.now();
            return { prev, next };
        }"""
            )
        )
        await asyncio.sleep(0)  # Make sure the promise is scheduled.
        await page.clock.run_for(1000)
        assert await promise == {"prev": 1000, "next": 2000}

    async def test_fakes_Date_constructor(self, page: Page) -> None:
        now = await page.evaluate("new Date().getTime()")
        assert now == 1000


class TestStubTimersPerformance:
    async def test_replaces_global_performance_time_origin(self, page: Page) -> None:
        await page.clock.install(time=1)
        await page.clock.pause_at(2)
        promise = asyncio.create_task(
            page.evaluate(
                """async () => {
            const prev = performance.now();
            await new Promise(f => setTimeout(f, 1000));
            const next = performance.now();
            return { prev, next };
        }"""
            )
        )
        await asyncio.sleep(0)  # Make sure the promise is scheduled.
        await page.clock.run_for(1000)
        assert await page.evaluate("performance.timeOrigin") == 1000
        assert await promise == {"prev": 1000, "next": 2000}


class TestPopup:
    async def test_should_tick_after_popup(self, page: Page) -> None:
        await page.clock.install(time=0)
        now = datetime.datetime.fromisoformat("2015-09-25")
        await page.clock.pause_at(now)
        popup, _ = await asyncio.gather(
            page.wait_for_event("popup"), page.evaluate("window.open('about:blank')")
        )
        popup_time = await popup.evaluate("Date.now()")
        assert popup_time == now.timestamp() * 1000
        await page.clock.run_for(1000)
        popup_time_after = await popup.evaluate("Date.now()")
        assert popup_time_after == now.timestamp() * 1000 + 1000

    async def test_should_tick_before_popup(self, page: Page) -> None:
        await page.clock.install(time=0)
        now = datetime.datetime.fromisoformat("2015-09-25")
        await page.clock.pause_at(now)
        await page.clock.run_for(1000)
        popup, _ = await asyncio.gather(
            page.wait_for_event("popup"), page.evaluate("window.open('about:blank')")
        )
        popup_time = await popup.evaluate("Date.now()")
        assert popup_time == int(now.timestamp() * 1000 + 1000)
        assert datetime.datetime.fromtimestamp(popup_time / 1_000).year == 2015

    async def test_should_run_time_before_popup(
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
        await page.goto(server.EMPTY_PAGE)
        # Wait for 2 second in real life to check that it is past in popup.
        await page.wait_for_timeout(2000)
        popup, _ = await asyncio.gather(
            page.wait_for_event("popup"),
            page.evaluate("window.open('{}')".format(server.PREFIX + "/popup.html")),
        )
        popup_time = await popup.evaluate("window.time")
        assert popup_time >= 2000

    async def test_should_not_run_time_before_popup_on_pause(
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
        await page.clock.install(time=0)
        await page.clock.pause_at(1)
        await page.goto(server.EMPTY_PAGE)
        # Wait for 2 second in real life to check that it is past in popup.
        await page.wait_for_timeout(2000)
        popup, _ = await asyncio.gather(
            page.wait_for_event("popup"),
            page.evaluate("window.open('{}')".format(server.PREFIX + "/popup.html")),
        )
        popup_time = await popup.evaluate("window.time")
        assert popup_time == 1000


class TestSetFixedTime:
    async def test_does_not_fake_methods(self, page: Page) -> None:
        await page.clock.set_fixed_time(0)
        # Should not stall.
        await page.evaluate("new Promise(f => setTimeout(f, 1))")

    async def test_allows_setting_time_multiple_times(self, page: Page) -> None:
        await page.clock.set_fixed_time(0.1)
        assert await page.evaluate("Date.now()") == 100
        await page.clock.set_fixed_time(0.2)
        assert await page.evaluate("Date.now()") == 200

    async def test_fixed_time_is_not_affected_by_clock_manipulation(
        self, page: Page
    ) -> None:
        await page.clock.set_fixed_time(0.1)
        assert await page.evaluate("Date.now()") == 100
        await page.clock.fast_forward(20)
        assert await page.evaluate("Date.now()") == 100

    async def test_allows_installing_fake_timers_after_setting_time(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.clock.set_fixed_time(0.1)
        assert await page.evaluate("Date.now()") == 100
        await page.clock.set_fixed_time(0.2)
        await page.evaluate("setTimeout(() => window.stub(Date.now()))")
        await page.clock.run_for(0)
        assert calls == [[200]]


class TestWhileRunning:
    async def test_should_progress_time(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.wait_for_timeout(1000)
        now = await page.evaluate("Date.now()")
        assert 1000 <= now <= 2000

    async def test_should_run_for(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.run_for(10000)
        now = await page.evaluate("Date.now()")
        assert 10000 <= now <= 11000

    async def test_should_fast_forward(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.fast_forward(10000)
        now = await page.evaluate("Date.now()")
        assert 10000 <= now <= 11000

    async def test_should_fast_forward_to(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.fast_forward(10000)
        now = await page.evaluate("Date.now()")
        assert 10000 <= now <= 11000

    async def test_should_pause(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.pause_at(1)
        await page.wait_for_timeout(1000)
        await page.clock.resume()
        now = await page.evaluate("Date.now()")
        assert 0 <= now <= 1000

    async def test_should_pause_and_fast_forward(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.pause_at(1)
        await page.clock.fast_forward(1000)
        now = await page.evaluate("Date.now()")
        assert now == 2000

    async def test_should_set_system_time_on_pause(self, page: Page) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.pause_at(1)
        now = await page.evaluate("Date.now()")
        assert now == 1000


class TestWhileOnPause:
    async def test_fast_forward_should_not_run_nested_immediate(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.pause_at(1000)
        await page.evaluate(
            """
            setTimeout(() => {
                window.stub('outer');
                setTimeout(() => window.stub('inner'), 0);
            }, 1000);
        """
        )
        await page.clock.fast_forward(1000)
        assert calls == [["outer"]]
        await page.clock.fast_forward(1)
        assert calls == [["outer"], ["inner"]]

    async def test_run_for_should_not_run_nested_immediate(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.pause_at(1000)
        await page.evaluate(
            """
            setTimeout(() => {
                window.stub('outer');
                setTimeout(() => window.stub('inner'), 0);
            }, 1000);
        """
        )
        await page.clock.run_for(1000)
        assert calls == [["outer"]]
        await page.clock.run_for(1)
        assert calls == [["outer"], ["inner"]]

    async def test_run_for_should_not_run_nested_immediate_from_microtask(
        self, page: Page, calls: List[Any]
    ) -> None:
        await page.clock.install(time=0)
        await page.goto("data:text/html,")
        await page.clock.pause_at(1000)
        await page.evaluate(
            """
            setTimeout(() => {
                window.stub('outer');
                void Promise.resolve().then(() => setTimeout(() => window.stub('inner'), 0));
            }, 1000);
        """
        )
        await page.clock.run_for(1000)
        assert calls == [["outer"]]
        await page.clock.run_for(1)
        assert calls == [["outer"], ["inner"]]
