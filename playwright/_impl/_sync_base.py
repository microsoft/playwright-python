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
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, Generic, List, Type, TypeVar, cast

import greenlet

from playwright._impl._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")
Self = TypeVar("Self", bound="SyncContextManager")


class EventInfo(Generic[T]):
    def __init__(self, sync_base: "SyncBase", future: "asyncio.Future[T]") -> None:
        self._sync_base = sync_base
        self._future = future
        g_self = greenlet.getcurrent()
        self._future.add_done_callback(lambda _: g_self.switch())

    @property
    def value(self) -> T:
        while not self._future.done():
            self._sync_base._dispatcher_fiber.switch()
        asyncio._set_running_loop(self._sync_base._loop)
        exception = self._future.exception()
        if exception:
            raise exception
        return cast(T, mapping.from_maybe_impl(self._future.result()))

    def is_done(self) -> bool:
        return self._future.done()


class EventContextManager(Generic[T]):
    def __init__(self, sync_base: "SyncBase", future: "asyncio.Future[T]") -> None:
        self._event = EventInfo[T](sync_base, future)

    def __enter__(self) -> EventInfo[T]:
        return self._event

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._event.value


class SyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop: asyncio.AbstractEventLoop = impl_obj._loop
        self._dispatcher_fiber = impl_obj._dispatcher_fiber

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _sync(self, api_name: str, coro: Awaitable) -> Any:
        __tracebackhide__ = True
        g_self = greenlet.getcurrent()
        task = self._loop.create_task(coro)
        setattr(task, "__pw_api_name__", api_name)
        setattr(task, "__pw_stack_trace__", traceback.extract_stack())

        task.add_done_callback(lambda _: g_self.switch())
        while not task.done():
            self._dispatcher_fiber.switch()
        asyncio._set_running_loop(self._loop)
        return task.result()

    def _wrap_handler(self, handler: Any) -> Callable[..., None]:
        if callable(handler):
            return mapping.wrap_handler(handler)
        return handler

    def on(self, event: Any, f: Any) -> None:
        """Registers the function ``f`` to the event name ``event``."""
        self._impl_obj.on(event, self._wrap_handler(f))

    def once(self, event: Any, f: Any) -> None:
        """The same as ``self.on``, except that the listener is automatically
        removed after being called.
        """
        self._impl_obj.once(event, self._wrap_handler(f))

    def remove_listener(self, event: Any, f: Any) -> None:
        """Removes the function ``f`` from ``event``."""
        self._impl_obj.remove_listener(event, self._wrap_handler(f))

    def _gather(self, *actions: Callable) -> List[Any]:
        g_self = greenlet.getcurrent()
        results: Dict[Callable, Any] = {}
        exceptions: List[Exception] = []

        def action_wrapper(action: Callable) -> Callable:
            def body() -> Any:
                try:
                    results[action] = action()
                except Exception as e:
                    results[action] = e
                    exceptions.append(e)
                g_self.switch()

            return body

        async def task() -> None:
            for action in actions:
                g = greenlet.greenlet(action_wrapper(action))
                g.switch()

        self._loop.create_task(task())

        while len(results) < len(actions):
            self._dispatcher_fiber.switch()

        asyncio._set_running_loop(self._loop)
        if exceptions:
            raise exceptions[0]

        return list(map(lambda action: results[action], actions))


class SyncContextManager(SyncBase):
    def __enter__(self: Self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        traceback: TracebackType,
    ) -> None:
        self.close()

    def close(self) -> None:
        ...
