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

from playwright._impl._connection import Channel
from playwright._impl._helper import MouseButton, locals_to_params


class Keyboard:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def down(self, key: str) -> None:
        await self._channel.send("keyboardDown", locals_to_params(locals()))

    async def up(self, key: str) -> None:
        await self._channel.send("keyboardUp", locals_to_params(locals()))

    async def insert_text(self, text: str) -> None:
        await self._channel.send("keyboardInsertText", locals_to_params(locals()))

    async def type(self, text: str, delay: float = None) -> None:
        await self._channel.send("keyboardType", locals_to_params(locals()))

    async def press(self, key: str, delay: float = None) -> None:
        await self._channel.send("keyboardPress", locals_to_params(locals()))


class Mouse:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def move(self, x: float, y: float, steps: int = None) -> None:
        await self._channel.send("mouseMove", locals_to_params(locals()))

    async def down(
        self,
        button: MouseButton = None,
        clickCount: int = None,
    ) -> None:
        await self._channel.send("mouseDown", locals_to_params(locals()))

    async def up(
        self,
        button: MouseButton = None,
        clickCount: int = None,
    ) -> None:
        await self._channel.send("mouseUp", locals_to_params(locals()))

    async def click(
        self,
        x: float,
        y: float,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
    ) -> None:
        await self._channel.send("mouseClick", locals_to_params(locals()))

    async def dblclick(
        self,
        x: float,
        y: float,
        delay: float = None,
        button: MouseButton = None,
    ) -> None:
        await self.click(x, y, delay=delay, button=button, clickCount=2)

    async def wheel(self, deltaX: float, deltaY: float) -> None:
        await self._channel.send("mouseWheel", locals_to_params(locals()))


class Touchscreen:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def tap(self, x: float, y: float) -> None:
        await self._channel.send("touchscreenTap", locals_to_params(locals()))
