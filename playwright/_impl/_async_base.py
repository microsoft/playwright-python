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
import traceback
from typing import Any, Awaitable, Callable, Generic, TypeVar

from playwright._impl._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")


class AsyncEventInfo(Generic[T]):
    def __init__(self, future: asyncio.Future) -> None:
        self._future = future

    @property
    async def value(self) -> T:
        return mapping.from_maybe_impl(await self._future)

    def is_done(self) -> bool:
        return self._future.done()


class AsyncEventContextManager(Generic[T]):
    def __init__(self, future: asyncio.Future) -> None:
        self._event: AsyncEventInfo = AsyncEventInfo(future)

    async def __aenter__(self) -> AsyncEventInfo[T]:
        return self._event

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._event.value


class AsyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop = impl_obj._loop

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _async(self, api_name: str, coro: Awaitable) -> Any:
        task = asyncio.current_task()
        setattr(task, "__pw_api_name__", api_name)
        setattr(task, "__pw_stack_trace__", traceback.extract_stack())
        return coro

    def _wrap_handler(self, handler: Any) -> Callable[..., None]:
        if callable(handler):
            return mapping.wrap_handler(handler)
        return handler

    def on(self, event: str, f: Any) -> None:
        """Registers the function ``f`` to the event name ``event``."""
        self._impl_obj.on(event, self._wrap_handler(f))

    def once(self, event: str, f: Any) -> None:
        """The same as ``self.on``, except that the listener is automatically
        removed after being called.
        """
        self._impl_obj.once(event, self._wrap_handler(f))

    def remove_listener(self, event: str, f: Any) -> None:
        """Removes the function ``f`` from ``event``."""
        self._impl_obj.remove_listener(event, self._wrap_handler(f))
