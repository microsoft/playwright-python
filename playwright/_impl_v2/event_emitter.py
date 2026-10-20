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

"""Port of packages/playwright-core/src/client/eventEmitter.ts.

Python: a listener that returns an awaitable (an async def handler) is a listener
that returns a promise. Its coroutine starts as a task, in the next iteration of
the event loop; a JS async listener runs at once until its first await.

Python: listeners compare with ==, not by identity, so that a bound method that is
looked up twice (self._on_close) is the same listener.
"""

import asyncio
import inspect
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Union

from playwright._impl_v2.utils.debug import is_under_test
from playwright._impl_v2.utils.tasks import completed

EventType = str
Listener = Callable[..., Any]

DEFAULT_MAX_LISTENERS = 10


class EventEmitter:
    def __init__(self) -> None:
        self._events: Dict[EventType, Union[Listener, List[Listener]]] = {}
        self._events_count = 0
        self._max_listeners: Optional[float] = None
        self._pending_handlers: Dict[EventType, Set["asyncio.Future[Any]"]] = {}
        self._rejection_handler: Optional[Callable[[BaseException], None]] = None
        # Python: a list takes no attributes, so the `warned` flag of each listener
        # array is kept here, by event type.
        self._warned: Set[EventType] = set()
        setattr(self, "on", self.add_listener)
        setattr(self, "off", self.remove_listener)

    def set_max_listeners(self, n: float) -> "EventEmitter":
        # Python: ValueError stands for RangeError.
        if not isinstance(n, (int, float)) or isinstance(n, bool) or n < 0 or n != n:
            raise ValueError(
                'The value of "n" is out of range. It must be a non-negative number. Received '
                + str(n)
                + "."
            )
        self._max_listeners = n
        return self

    def get_max_listeners(self) -> float:
        return (
            DEFAULT_MAX_LISTENERS
            if self._max_listeners is None
            else self._max_listeners
        )

    def emit(self, type: EventType, *args: Any) -> bool:
        events = self._events
        handler = events.get(type)
        if handler is None:
            return False

        if not isinstance(handler, list):
            self._call_handler(type, handler, args)
        else:
            listeners = list(handler)
            for listener in listeners:
                self._call_handler(type, listener, args)
        return True

    def _call_handler(self, type: EventType, handler: Listener, args: Any) -> None:
        promise = handler(*args)
        if not inspect.isawaitable(promise):
            return
        # Python: the coroutine of an async def handler runs as a task.
        future = asyncio.ensure_future(promise)
        pending = self._pending_handlers.get(type)
        if pending is None:
            pending = set()
            self._pending_handlers[type] = pending
        pending.add(future)

        def on_done(f: "asyncio.Future[Any]") -> None:
            pending.discard(f)
            if f.cancelled():
                return
            e = f.exception()
            if e is None:
                return
            if self._rejection_handler:
                self._rejection_handler(e)
            else:
                # Python: the counterpart of an unhandled rejection.
                self._report_unhandled_error(e)

        future.add_done_callback(on_done)

    def _report_unhandled_error(self, error: BaseException) -> None:
        # Python: an unhandled rejection crashes Node.js; see report_unhandled_error().
        report_unhandled_error(error)

    def add_listener(self, type: EventType, listener: Listener) -> "EventEmitter":
        return self._add_listener(type, listener, False)

    def on(self, type: EventType, listener: Listener) -> "EventEmitter":
        return self._add_listener(type, listener, False)

    def _add_listener(
        self, type: EventType, listener: Listener, prepend: bool
    ) -> "EventEmitter":
        check_listener(listener)
        events = self._events
        # To avoid recursion in the case that type == "newListener"! Before
        # adding it to the listeners, first emit "newListener".
        if events.get("newListener") is not None:
            self.emit("newListener", type, unwrap_listener(listener))
            # Re-assign `events` because a newListener handler could have caused the
            # self._events to be assigned to a new object
            events = self._events
        existing = events.get(type)

        if existing is None:
            # Optimize the case of one listener. Don't need the extra array object.
            events[type] = listener
            self._events_count += 1
        else:
            if not isinstance(existing, list):
                # Adding the second element, need to change to array.
                existing = events[type] = (
                    [listener, existing] if prepend else [existing, listener]
                )
                # If we've already got an array, just append.
            elif prepend:
                existing.insert(0, listener)
            else:
                existing.append(listener)

            # Check for listener leak
            m = self.get_max_listeners()
            if m > 0 and len(existing) > m and type not in self._warned:
                self._warned.add(type)
                # No error code for this since it is a Warning
                # Python: printed to stderr, as console.warn() does.
                if not is_under_test():
                    print(
                        "MaxListenersExceededWarning: Possible EventEmitter memory leak detected. "
                        + str(len(existing))
                        + " "
                        + str(type)
                        + " listeners added. Use emitter.set_max_listeners() to increase limit",
                        file=sys.stderr,
                    )

        return self

    def prepend_listener(self, type: EventType, listener: Listener) -> "EventEmitter":
        return self._add_listener(type, listener, True)

    def once(self, type: EventType, listener: Listener) -> "EventEmitter":
        check_listener(listener)
        self.on(type, OnceWrapper(self, type, listener).wrapper_function)
        return self

    def prepend_once_listener(
        self, type: EventType, listener: Listener
    ) -> "EventEmitter":
        check_listener(listener)
        self.prepend_listener(type, OnceWrapper(self, type, listener).wrapper_function)
        return self

    def remove_listener(self, type: EventType, listener: Listener) -> "EventEmitter":
        check_listener(listener)

        events = self._events
        list_ = events.get(type)
        if list_ is None:
            return self

        if not isinstance(list_, list):
            if list_ == listener or wrapped_listener(list_) == listener:
                self._events_count -= 1
                if self._events_count == 0:
                    self._events = {}
                else:
                    del events[type]
                    if events.get("removeListener") is not None:
                        self.emit(
                            "removeListener",
                            type,
                            wrapped_listener(list_) or listener,
                        )
        else:
            position = -1
            original_listener = None

            for i in range(len(list_) - 1, -1, -1):
                if list_[i] == listener or wrapped_listener(list_[i]) == listener:
                    original_listener = wrapped_listener(list_[i])
                    position = i
                    break

            if position < 0:
                return self

            if position == 0:
                list_.pop(0)
            else:
                del list_[position]

            if len(list_) == 1:
                events[type] = list_[0]

            if events.get("removeListener") is not None:
                self.emit("removeListener", type, original_listener or listener)

        return self

    def off(self, type: EventType, listener: Listener) -> "EventEmitter":
        return self.remove_listener(type, listener)

    def remove_all_listeners(
        self, type: Optional[EventType] = None, behavior: Optional[str] = None
    ) -> Any:
        """removeAllListeners(type) and removeAllListeners(type, { behavior }).

        Python: with a behavior, the result is a future to await, as the JS method
        returns a promise.
        """
        self._remove_all_listeners(type)
        if behavior is None:
            return self

        if behavior == "wait":
            errors: List[BaseException] = []
            self._rejection_handler = lambda error: errors.append(error)

            async def wait() -> None:
                await self._wait_for(type)
                if errors:
                    raise errors[0]

            return wait()

        if behavior == "ignoreErrors":
            self._rejection_handler = lambda error: None

        return completed(None)

    def _remove_all_listeners(self, type: Optional[EventType] = None) -> None:
        events = self._events
        if not events:
            return

        # not listening for removeListener, no need to emit
        if events.get("removeListener") is None:
            if type is None:
                self._events = {}
                self._events_count = 0
            elif events.get(type) is not None:
                self._events_count -= 1
                if self._events_count == 0:
                    self._events = {}
                else:
                    del events[type]
            return

        # emit removeListener for all listeners on all events
        if type is None:
            for key in list(events.keys()):
                if key == "removeListener":
                    continue
                self._remove_all_listeners(key)
            self._remove_all_listeners("removeListener")
            self._events = {}
            self._events_count = 0
            return

        listeners = events.get(type)

        if listeners is not None and not isinstance(listeners, list):
            self.remove_listener(type, listeners)
        elif listeners is not None:
            # LIFO order
            for i in range(len(listeners) - 1, -1, -1):
                self.remove_listener(type, listeners[i])

    def listeners(self, type: EventType) -> List[Listener]:
        return self._listeners(self, type, True)

    def raw_listeners(self, type: EventType) -> List[Listener]:
        return self._listeners(self, type, False)

    def listener_count(self, type: EventType) -> int:
        listener = self._events.get(type)
        if listener is None:
            return 0
        if not isinstance(listener, list):
            return 1
        return len(listener)

    def event_names(self) -> List[EventType]:
        return list(self._events.keys()) if self._events_count > 0 else []

    def _wait_for(self, type: Optional[EventType] = None) -> "asyncio.Future[Any]":
        # Python: not an async def; the pending handlers are taken at call time, as
        # the JS async function takes them before its first await.
        promises: List["asyncio.Future[Any]"] = []
        if type:
            promises = list(self._pending_handlers.get(type) or [])
        else:
            for pending in self._pending_handlers.values():
                promises.extend(pending)
        return asyncio.gather(*promises)

    def _listeners(
        self, target: "EventEmitter", type: EventType, unwrap: bool
    ) -> List[Listener]:
        listener = target._events.get(type)
        if listener is None:
            return []

        if not isinstance(listener, list):
            return [unwrap_listener(listener)] if unwrap else [listener]

        return unwrap_listeners(listener) if unwrap else list(listener)


def check_listener(listener: Any) -> None:
    if not callable(listener):
        raise TypeError(
            'The "listener" argument must be of type Function. Received type '
            + type(listener).__name__
        )


class OnceWrapper:
    def __init__(
        self, event_emitter: EventEmitter, event_type: EventType, listener: Listener
    ) -> None:
        self._fired = False
        self._event_emitter = event_emitter
        self._event_type = event_type
        self._listener = listener

        def wrapper_function(*args: Any) -> Any:
            return self._handle(*args)

        setattr(wrapper_function, "listener", listener)
        self.wrapper_function: Listener = wrapper_function

    def _handle(self, *args: Any) -> Any:
        if self._fired:
            return None
        self._fired = True
        self._event_emitter.remove_listener(self._event_type, self.wrapper_function)
        return self._listener(*args)


def unwrap_listener(listener: Listener) -> Listener:
    return wrapped_listener(listener) or listener


def unwrap_listeners(arr: List[Listener]) -> List[Listener]:
    return [wrapped_listener(listener) or listener for listener in arr]


def wrapped_listener(listener: Listener) -> Optional[Listener]:
    return getattr(listener, "listener", None)


def report_unhandled_error(error: BaseException) -> None:
    # Python: an unhandled rejection crashes Node.js. Here the event loop reports it.
    asyncio.get_event_loop().call_exception_handler(
        {"message": "Unhandled error in an event listener", "exception": error}
    )
