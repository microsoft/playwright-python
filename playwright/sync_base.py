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
from typing import Any, Callable, Generic, Optional, TypeVar, cast

import greenlet

from playwright.impl_to_api_mapping import ImplToApiMapping, ImplWrapper
from playwright.wait_helper import WaitHelper

mapping = ImplToApiMapping()


T = TypeVar("T")

dispatcher_fiber_: greenlet


def set_dispatcher_fiber(fiber: greenlet) -> None:
    global dispatcher_fiber_
    dispatcher_fiber_ = fiber


def dispatcher_fiber() -> greenlet:
    return dispatcher_fiber_


class EventInfo(Generic[T]):
    def __init__(
        self,
        sync_base: "SyncBase",
        event: str,
        predicate: Callable[[T], bool] = None,
        timeout: int = None,
    ) -> None:
        self._value: Optional[T] = None
        self._exception = None
        self._loop = sync_base._loop

        wait_helper = WaitHelper(sync_base._loop)
        wait_helper.reject_on_timeout(
            timeout or 30000, f'Timeout while waiting for event "${event}"'
        )
        self._future = sync_base._loop.create_task(
            wait_helper.wait_for_event(sync_base._impl_obj, event, predicate)
        )
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
        while not self._value and not self._exception:
            dispatcher_fiber_.switch()
        asyncio._set_running_loop(self._loop)
        if self._exception:
            raise self._exception
        return cast(T, self._value)


class EventContextManager(Generic[T]):
    def __init__(
        self,
        sync_base: "SyncBase",
        event: str,
        predicate: Callable[[T], bool] = None,
        timeout: int = None,
    ) -> None:
        self._loop = sync_base._loop
        self._event = EventInfo(sync_base, event, predicate, timeout)

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

    def on(self, event_name: str, handler: Any) -> None:
        self._impl_obj.on(event_name, self._wrap_handler(handler))

    def once(self, event_name: str, handler: Any) -> None:
        self._impl_obj.once(event_name, self._wrap_handler(handler))

    def remove_listener(self, event_name: str, handler: Any) -> None:
        self._impl_obj.remove_listener(event_name, handler)

    def expect_event(
        self, event: str, predicate: Callable[[Any], bool] = None, timeout: int = None,
    ) -> EventContextManager:
        return EventContextManager(self, event, predicate, timeout)
