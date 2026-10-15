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
from typing import TYPE_CHECKING, Optional, Tuple, Union

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext


class Clock:
    def __init__(self, browser_context: "BrowserContext") -> None:
        self._browser_context = browser_context
        self._loop = browser_context._loop
        self._dispatcher_fiber = browser_context._dispatcher_fiber

    async def install(
        self, time: Optional[Union[float, str, datetime.datetime]]
    ) -> None:
        time_number, time_string = (
            parse_time(time) if time is not None else (None, None)
        )
        await self._browser_context._channel.clockInstall(
            timeNumber=time_number, timeString=time_string
        )

    async def fast_forward(
        self,
        ticks: Union[int, str],
    ) -> None:
        ticks_number, ticks_string = parse_ticks(ticks)
        await self._browser_context._channel.clockFastForward(
            ticksNumber=ticks_number, ticksString=ticks_string
        )

    async def pause_at(
        self,
        time: Union[float, str, datetime.datetime],
    ) -> None:
        time_number, time_string = parse_time(time)
        await self._browser_context._channel.clockPauseAt(
            timeNumber=time_number, timeString=time_string
        )

    async def resume(
        self,
    ) -> None:
        await self._browser_context._channel.clockResume()

    async def run_for(
        self,
        ticks: Union[int, str],
    ) -> None:
        ticks_number, ticks_string = parse_ticks(ticks)
        await self._browser_context._channel.clockRunFor(
            ticksNumber=ticks_number, ticksString=ticks_string
        )

    async def set_fixed_time(
        self,
        time: Union[float, str, datetime.datetime],
    ) -> None:
        time_number, time_string = parse_time(time)
        await self._browser_context._channel.clockSetFixedTime(
            timeNumber=time_number, timeString=time_string
        )

    async def set_system_time(
        self,
        time: Union[float, str, datetime.datetime],
    ) -> None:
        time_number, time_string = parse_time(time)
        await self._browser_context._channel.clockSetSystemTime(
            timeNumber=time_number, timeString=time_string
        )


def parse_time(
    time: Union[float, str, datetime.datetime],
) -> Tuple[Optional[int], Optional[str]]:
    """Returns (timeNumber, timeString)."""
    if isinstance(time, (float, int)):
        return int(time * 1_000), None
    if isinstance(time, str):
        return None, time
    return int(time.timestamp() * 1_000), None


def parse_ticks(ticks: Union[int, str]) -> Tuple[Optional[int], Optional[str]]:
    """Returns (ticksNumber, ticksString)."""
    if isinstance(ticks, int):
        return ticks, None
    return None, ticks
