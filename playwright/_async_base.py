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
from typing import Any, Callable, Coroutine, Generic, Optional, TypeVar, cast

from playwright._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")


class AsyncEventInfo(Generic[T]):
    def __init__(self, coroutine: Coroutine) -> None:
        self._value: Optional[T] = None
        self._future = asyncio.get_event_loop().create_task(coroutine)
        self._done = False

    @property
    async def value(self) -> T:
        if not self._done:
            self._value = mapping.from_maybe_impl(await self._future)
            self._done = True
        return cast(T, self._value)


class AsyncEventContextManager(Generic[T]):
    def __init__(self, coroutine: Coroutine) -> None:
        self._event: AsyncEventInfo = AsyncEventInfo(coroutine)

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

    def _sync(self, future: asyncio.Future) -> Any:
        return self._loop.run_until_complete(future)

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
