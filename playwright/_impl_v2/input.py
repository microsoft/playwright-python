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

"""Port of packages/playwright-core/src/client/input.ts.

Python: Keyboard, Mouse and Touchscreen are not ChannelOwners, so each one keeps the
event loop of its page for the generated API. The options objects are separate
parameters.
"""

from typing import TYPE_CHECKING, Awaitable, Callable, Literal, Optional, TypeVar

from playwright._impl_v2.channel_owner import ApiCallOptions, ApiZone, api_call
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.page import Page

R = TypeVar("R")

# Python: the type of the button option of the Python API
# (playwright/_impl/_helper.py).
MouseButton = Literal["left", "middle", "right"]


class Keyboard:
    def __init__(self, page: "Page") -> None:
        self._page = page
        # Python: the generated API reads the event loop of each object.
        self._loop = page._loop

    async def down(self, key: str) -> None:
        await self._page._channel.keyboardDown(key=key, timeout=NO_TIMEOUT)

    async def up(self, key: str) -> None:
        await self._page._channel.keyboardUp(key=key, timeout=NO_TIMEOUT)

    async def insert_text(self, text: str) -> None:
        await self._page._channel.keyboardInsertText(text=text, timeout=NO_TIMEOUT)

    async def type(self, text: str, delay: Optional[float]) -> None:
        await self._page._channel.keyboardType(
            text=text, delay=delay, timeout=NO_TIMEOUT
        )

    async def press(self, key: str, delay: Optional[float]) -> None:
        await self._page._channel.keyboardPress(
            key=key, delay=delay, timeout=NO_TIMEOUT
        )


class Mouse:
    def __init__(self, page: "Page") -> None:
        self._page = page
        # Python: the generated API reads the event loop of each object.
        self._loop = page._loop

    def _wrap_api_call(
        self,
        func: Callable[[ApiZone], Awaitable[R]],
        options: Optional[ApiCallOptions] = None,
    ) -> Awaitable[R]:
        # Python: not an async def, as ChannelOwner._wrap_api_call(): func is
        # called at once.
        return self._page._wrap_api_call(func, options)

    async def move(self, x: float, y: float, steps: Optional[int]) -> None:
        await self._page._channel.mouseMove(x=x, y=y, steps=steps, timeout=NO_TIMEOUT)

    async def down(
        self, button: Optional[MouseButton], click_count: Optional[int]
    ) -> None:
        await self._page._channel.mouseDown(
            button=button, clickCount=click_count, timeout=NO_TIMEOUT
        )

    async def up(
        self, button: Optional[MouseButton], click_count: Optional[int]
    ) -> None:
        await self._page._channel.mouseUp(
            button=button, clickCount=click_count, timeout=NO_TIMEOUT
        )

    async def click(
        self,
        x: float,
        y: float,
        delay: Optional[float],
        button: Optional[MouseButton],
        click_count: Optional[int],
    ) -> None:
        await self._page._channel.mouseClick(
            x=x,
            y=y,
            delay=delay,
            button=button,
            clickCount=click_count,
            timeout=NO_TIMEOUT,
        )

    @api_call(title="Double click")
    async def dblclick(
        self,
        x: float,
        y: float,
        delay: Optional[float],
        button: Optional[MouseButton],
    ) -> None:
        await self.click(x, y, delay=delay, button=button, click_count=2)

    async def wheel(self, delta_x: float, delta_y: float) -> None:
        await self._page._channel.mouseWheel(
            deltaX=delta_x, deltaY=delta_y, timeout=NO_TIMEOUT
        )


class Touchscreen:
    def __init__(self, page: "Page") -> None:
        self._page = page
        # Python: the generated API reads the event loop of each object.
        self._loop = page._loop

    async def tap(self, x: float, y: float) -> None:
        await self._page._channel.touchscreenTap(x=x, y=y, timeout=NO_TIMEOUT)
