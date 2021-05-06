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
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from playwright._impl._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")


class EventInfo(Generic[T]):
    def __init__(
        self,
        sync_base: "SyncBase",
        future: asyncio.Future,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._sync_base = sync_base
        self._value: Optional[T] = None
        self._future = future
        self._loop = loop

    @property
    def value(self) -> T:
        if self._value is None:
            self._value = mapping.from_maybe_impl(
                self._loop.run_until_complete(self._future)
            )
        return self._value

    def is_done(self) -> bool:
        return self._future.done()


class EventContextManager(Generic[T]):
    def __init__(self, sync_base: "SyncBase", future: asyncio.Future) -> None:
        self._event: EventInfo = EventInfo(sync_base, future, sync_base._loop)

    def __enter__(self) -> EventInfo[T]:
        return self._event

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._event.value


class SyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop: asyncio.AbstractEventLoop = impl_obj._loop

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _sync(self, api_name: str, coro: Awaitable) -> Any:
        return self._loop.run_until_complete(coro)

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
