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
import inspect
import traceback
from typing import Awaitable, Callable, Dict

import greenlet

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import Error, is_target_closed_error


class Disposable(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def dispose(self) -> None:
        try:
            await self._channel.send(
                "dispose",
                None,
            )
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    async def close(self) -> None:
        await self.dispose()

    def __repr__(self) -> str:
        return "<Disposable>"


class DisposableStub:
    def __init__(
        self,
        dispose_fn: Callable[[], Awaitable[None]],
        parent: ChannelOwner,
    ) -> None:
        self._dispose_fn = dispose_fn
        self._loop = parent._loop
        self._dispatcher_fiber = parent._dispatcher_fiber

    async def dispose(self) -> None:
        await self._dispose_fn()

    async def __aenter__(self) -> "DisposableStub":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.dispose()

    def __enter__(self) -> "DisposableStub":
        return self

    def __exit__(self, *args: object) -> None:
        self._sync(self.dispose())

    def _sync(self, coro: object) -> object:
        __tracebackhide__ = True
        if self._loop.is_closed():
            coro.close()  # type: ignore
            raise Error("Event loop is closed! Is Playwright already stopped?")
        g_self = greenlet.getcurrent()
        task = self._loop.create_task(coro)  # type: ignore
        setattr(task, "__pw_stack__", inspect.stack(0))
        setattr(task, "__pw_stack_trace__", traceback.extract_stack(limit=10))
        task.add_done_callback(lambda _: g_self.switch())
        while not task.done():
            self._dispatcher_fiber.switch()  # type: ignore
        asyncio._set_running_loop(self._loop)
        return task.result()

    async def close(self) -> None:
        await self.dispose()

    def __repr__(self) -> str:
        return "<Disposable>"
