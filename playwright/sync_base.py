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
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    cast,
)

import greenlet

from playwright.impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")

dispatcher_fiber_: greenlet


def set_dispatcher_fiber(fiber: greenlet) -> None:
    global dispatcher_fiber_
    dispatcher_fiber_ = fiber


def dispatcher_fiber() -> greenlet:
    return dispatcher_fiber_


class EventInfo(Generic[T]):
    def __init__(self, loop: asyncio.AbstractEventLoop, coroutine: Coroutine) -> None:
        self._loop = loop
        self._value: Optional[T] = None
        self._exception = None
        self._future = loop.create_task(coroutine)
        g_self = greenlet.getcurrent()

        def done_callback(task: Any) -> None:
            try:
                self._value = mapping.from_maybe_impl(self._future.result())
            except Exception as e:
                self._exception = e
            finally:
                g_self.switch()

        self._future.add_done_callback(done_callback)

    @property
    def value(self) -> T:
        while not self._future.done():
            dispatcher_fiber_.switch()
        asyncio._set_running_loop(self._loop)
        if self._exception:
            raise self._exception
        return cast(T, self._value)


class EventContextManager(Generic[T]):
    def __init__(self, loop: asyncio.AbstractEventLoop, coroutine: Coroutine) -> None:
        self._event: EventInfo = EventInfo(loop, coroutine)

    def __enter__(self) -> EventInfo[T]:
        return self._event

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._event.value


class SyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop = impl_obj._loop

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _sync(self, task: asyncio.Future) -> Any:
        g_self = greenlet.getcurrent()
        future = self._loop.create_task(task)

        def callback(result: Any) -> None:
            g_self.switch()

        future.add_done_callback(callback)
        while not future.done():
            dispatcher_fiber_.switch()
        asyncio._set_running_loop(self._loop)
        return future.result()

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
            dispatcher_fiber_.switch()

        asyncio._set_running_loop(self._loop)
        if exceptions:
            raise exceptions[0]

        return list(map(lambda action: results[action], actions))
