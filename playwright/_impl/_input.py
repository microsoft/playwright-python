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
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, TypeVar

from playwright._impl._connection import api_call
from playwright._impl._helper import MouseButton

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page

T = TypeVar("T")


class Keyboard:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber

    async def down(self, key: str) -> None:
        await self._page._channel.keyboardDown(key=key)

    async def up(self, key: str) -> None:
        await self._page._channel.keyboardUp(key=key)

    async def insert_text(self, text: str) -> None:
        await self._page._channel.keyboardInsertText(text=text)

    async def type(self, text: str, delay: Optional[float]) -> None:
        await self._page._channel.keyboardType(text=text, delay=delay)

    async def press(self, key: str, delay: Optional[float]) -> None:
        await self._page._channel.keyboardPress(key=key, delay=delay)


class Mouse:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber

    async def _wrap_api_call(
        self,
        cb: Callable[[], Awaitable[T]],
        is_internal: bool = False,
        title: Optional[str] = None,
    ) -> T:
        return await self._page._wrap_api_call(cb, is_internal, title)

    async def move(self, x: float, y: float, steps: Optional[int]) -> None:
        await self._page._channel.mouseMove(x=x, y=y, steps=steps)

    async def down(
        self,
        button: Optional[MouseButton],
        click_count: Optional[int],
    ) -> None:
        await self._page._channel.mouseDown(button=button, clickCount=click_count)

    async def up(
        self,
        button: Optional[MouseButton],
        click_count: Optional[int],
    ) -> None:
        await self._page._channel.mouseUp(button=button, clickCount=click_count)

    async def click(
        self,
        x: float,
        y: float,
        delay: Optional[float],
        button: Optional[MouseButton],
        click_count: Optional[int],
    ) -> None:
        await self._page._channel.mouseClick(
            x=x, y=y, delay=delay, button=button, clickCount=click_count
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
        await self._page._channel.mouseWheel(deltaX=delta_x, deltaY=delta_y)


class Touchscreen:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber

    async def tap(self, x: float, y: float) -> None:
        await self._page._channel.touchscreenTap(x=x, y=y)
