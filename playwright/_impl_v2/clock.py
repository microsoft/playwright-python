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

"""Port of packages/playwright-core/src/client/clock.ts.

Python: Clock is not a ChannelOwner, so it keeps the event loop of its context for
the generated API. A number time is Unix time in seconds in the Python API, not in
milliseconds, and a Date is a datetime. Ticks are milliseconds, as upstream.
"""

import datetime
from typing import TYPE_CHECKING, Optional, TypedDict, Union

from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.browser_context import BrowserContext


class Clock:
    def __init__(self, browser_context: "BrowserContext") -> None:
        self._browser_context = browser_context
        # Python: the generated API reads the event loop of each object.
        self._loop = browser_context._loop

    async def install(
        self, time: Optional[Union[float, str, datetime.datetime]]
    ) -> None:
        params = parse_time(time) if time is not None else _TimeParams()
        await self._browser_context._channel.clockInstall(
            timeNumber=params.get("timeNumber"),
            timeString=params.get("timeString"),
            timeout=NO_TIMEOUT,
        )

    async def fast_forward(self, ticks: Union[int, str]) -> None:
        params = parse_ticks(ticks)
        await self._browser_context._channel.clockFastForward(
            ticksNumber=params["ticksNumber"],
            ticksString=params["ticksString"],
            timeout=NO_TIMEOUT,
        )

    async def pause_at(self, time: Union[float, str, datetime.datetime]) -> None:
        params = parse_time(time)
        await self._browser_context._channel.clockPauseAt(
            timeNumber=params.get("timeNumber"),
            timeString=params.get("timeString"),
            timeout=NO_TIMEOUT,
        )

    async def resume(self) -> None:
        await self._browser_context._channel.clockResume(timeout=NO_TIMEOUT)

    async def run_for(self, ticks: Union[int, str]) -> None:
        params = parse_ticks(ticks)
        await self._browser_context._channel.clockRunFor(
            ticksNumber=params["ticksNumber"],
            ticksString=params["ticksString"],
            timeout=NO_TIMEOUT,
        )

    async def set_fixed_time(self, time: Union[float, str, datetime.datetime]) -> None:
        params = parse_time(time)
        await self._browser_context._channel.clockSetFixedTime(
            timeNumber=params.get("timeNumber"),
            timeString=params.get("timeString"),
            timeout=NO_TIMEOUT,
        )

    async def set_system_time(self, time: Union[float, str, datetime.datetime]) -> None:
        params = parse_time(time)
        await self._browser_context._channel.clockSetSystemTime(
            timeNumber=params.get("timeNumber"),
            timeString=params.get("timeString"),
            timeout=NO_TIMEOUT,
        )


class _TimeParams(TypedDict, total=False):
    timeNumber: int
    timeString: str


class _TicksParams(TypedDict):
    ticksNumber: Optional[float]
    ticksString: Optional[str]


def parse_time(time: Union[float, str, datetime.datetime]) -> _TimeParams:
    if isinstance(time, (int, float)):
        # Python: a number is Unix time in seconds; the protocol takes
        # milliseconds.
        return {"timeNumber": int(time * 1_000)}
    if isinstance(time, str):
        return {"timeString": time}
    # Python: a datetime is always a valid date, so there is no "Invalid date"
    # check.
    return {"timeNumber": int(time.timestamp() * 1_000)}


def parse_ticks(ticks: Union[int, str]) -> _TicksParams:
    return {
        "ticksNumber": ticks if isinstance(ticks, (int, float)) else None,
        "ticksString": ticks if isinstance(ticks, str) else None,
    }
