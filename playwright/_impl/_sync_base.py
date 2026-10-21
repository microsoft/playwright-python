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
import sys
from contextlib import AbstractContextManager
from types import TracebackType
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from playwright._impl._errors import Error
from playwright._impl._greenlets import connection_closed_error, wait_for_future
from playwright._impl._impl_to_api_mapping import ImplToApiMapping, ImplWrapper

mapping = ImplToApiMapping()


T = TypeVar("T")
Self = TypeVar("Self", bound="SyncContextManager")


class EventInfo(Generic[T]):
    def __init__(self, sync_base: "SyncBase", future: "asyncio.Future[T]") -> None:
        self._sync_base = sync_base
        self._future = future

    @property
    def value(self) -> T:
        wait_for_future(
            self._sync_base._loop, self._sync_base._dispatcher_fiber, self._future
        )
        exception = self._future.exception()
        if exception:
            raise exception
        return cast(T, mapping.from_maybe_impl(self._future.result()))

    def _cancel(self) -> None:
        self._future.cancel()

    def is_done(self) -> bool:
        return self._future.done()


class EventContextManager(Generic[T], AbstractContextManager):
    def __init__(self, sync_base: "SyncBase", future: "asyncio.Future[T]") -> None:
        self._event = EventInfo[T](sync_base, future)

    def __enter__(self) -> EventInfo[T]:
        # The wait takes its first step before the body runs; see
        # AsyncEventContextManager.__aenter__(). The body of a sync block may make
        # no call at all, so the event loop gets a turn here.
        sync_base = self._event._sync_base
        wait_for_future(
            sync_base._loop,
            sync_base._dispatcher_fiber,
            asyncio.ensure_future(asyncio.sleep(0)),
        )
        return self._event

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_val:
            self._event._cancel()
        else:
            self._event.value


async def _wait(awaitable: Awaitable[Any]) -> Any:
    return await awaitable


class SyncBase(ImplWrapper):
    def __init__(self, impl_obj: Any) -> None:
        super().__init__(impl_obj)
        self._loop: asyncio.AbstractEventLoop = impl_obj._loop
        self._dispatcher_fiber = impl_obj._dispatcher_fiber

    def __str__(self) -> str:
        return self._impl_obj.__str__()

    def _sync(self, awaitable: Awaitable[Any]) -> Any:
        __tracebackhide__ = True
        # An API call returns the coroutine of the call, or, when it runs inside
        # another call, the awaitable of the channel call (a future).
        coro = awaitable if asyncio.iscoroutine(awaitable) else _wait(awaitable)
        if self._loop.is_closed():
            coro.close()
            raise Error("Event loop is closed! Is Playwright already stopped?")
        if self._dispatcher_fiber.dead:
            coro.close()
            raise connection_closed_error()

        task: asyncio.tasks.Task[Any] = self._loop.create_task(coro)
        # The task runs in the dispatcher fiber, where the stack of this call is not
        # visible. The client continues the stack from the caller's frame, which it
        # reads from the task (capture_raw_stack() in utils/stack_trace.py).
        setattr(task, "__pw_caller_frame__", sys._getframe(1))

        wait_for_future(self._loop, self._dispatcher_fiber, task)
        return task.result()

    def _wrap_handler(self, handler: Union[Callable[..., Any], Any]) -> Any:
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


class SyncContextManager(SyncBase):
    def __enter__(self: Self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None: ...
