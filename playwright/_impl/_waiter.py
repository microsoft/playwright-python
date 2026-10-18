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

"""Port of packages/playwright-core/src/client/waiter.ts."""

import asyncio
import inspect
import math
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pyee import EventEmitter

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import TimeoutError, rewrite_error_message


class Waiter:
    # Upstream's waits are promises that race with the failures. Here a wait is a
    # future that starts right away (the expect_*() methods return it before the
    # action runs), and the first failure fails the active waits and the later ones.
    def __init__(self, channel_owner: ChannelOwner, event: str) -> None:
        self._wait_id = uuid.uuid4().hex
        self._channel_owner = channel_owner
        self._loop = channel_owner._loop
        self._failure: Optional[Exception] = None
        self._active_waits: List[Callable[[Exception], None]] = []
        self._immediate_error: Optional[Exception] = None
        self._logs: List[str] = []
        self._error: Optional[str] = None
        # The tasks of the async predicates.
        self._pending_tasks: List[asyncio.Task] = []
        self._disposed = False
        self._dispose_on_settle = False
        self._result: Optional[asyncio.Future] = None

        self._send_wait_info(
            {"waitId": self._wait_id, "phase": "before", "event": event},
            title=f'Wait for event "{event}"',
        )
        self._dispose: List[Callable[[], None]] = [
            lambda: self._send_wait_info(
                {"waitId": self._wait_id, "phase": "after", "error": self._error},
                internal=True,
            )
        ]

    @staticmethod
    def create_for_event(channel_owner: ChannelOwner, event: str) -> "Waiter":
        return Waiter(channel_owner, event)

    def _send_wait_info(
        self, info: Dict[str, Any], title: str = None, internal: bool = False
    ) -> None:
        # Fire-and-forget: the server intentionally never replies, and we never
        # throw to the caller.
        owner = self._channel_owner
        try:
            # An outer api_call() may have set its own title (e.g. "Wait for
            # navigation"); send_no_reply() falls back to ours only when the outer
            # zone left it blank and this message reports the call.
            owner._channel.send_no_reply(
                "__waitInfo__", info, is_internal=internal, title=title
            )
        except Exception:
            pass

    def reject_on_event(
        self,
        emitter: EventEmitter,
        event: str,
        error: Union[Exception, Callable[[], Exception]],
        predicate: Callable = None,
    ) -> None:
        dispose = _wait_for_event(
            self,
            emitter,
            event,
            predicate,
            lambda _: self._fail(error() if callable(error) else error),
            self._fail,
        )
        self._dispose.append(dispose)

    def reject_immediately(self, error: Exception) -> None:
        self._immediate_error = error

    def throw_if_immediately_rejected(self) -> None:
        if self._immediate_error:
            raise self._immediate_error

    def reject_on_timeout(self, timeout: float, message: str) -> None:
        if timeout:
            handle = self._loop.call_later(
                timeout / 1000, lambda: self._fail(TimeoutError(message))
            )
            self._dispose.append(handle.cancel)

    def _fail(self, error: Exception) -> None:
        # A failure of _rejectOn() upstream: the first failure fails the active
        # waits and the later ones.
        if self._failure:
            return
        self._failure = error
        for reject in list(self._active_waits):
            reject(error)

    def wait_for_event(
        self,
        emitter: EventEmitter,
        event: str,
        predicate: Callable = None,
    ) -> asyncio.Future:
        """Port of waitForEvent().

        Starts to listen right away. Returns a future that settles with the event,
        or fails when the waiter fails first.
        """
        dispose = _wait_for_event(
            self,
            emitter,
            event,
            predicate,
            lambda value: resolve(value),
            lambda error: reject(error),
        )
        result, resolve, reject = self._start_wait(dispose)
        self._result = result
        return result

    def wait_for_future(
        self, future: asyncio.Future, dispose: Callable[[], None] = None
    ) -> asyncio.Future:
        """Port of waitForPromise().

        Returns a future that settles as `future` does, or fails when the waiter
        fails first.
        """

        def on_done(_: asyncio.Future) -> None:
            if future.cancelled():
                return
            error = future.exception()
            if error is None:
                resolve(future.result())
            elif isinstance(error, Exception):
                reject(error)

        def cancel() -> None:
            future.remove_done_callback(on_done)
            if not future.done():
                future.cancel()
            if dispose:
                dispose()

        future.add_done_callback(on_done)
        result, resolve, reject = self._start_wait(cancel)
        return result

    def _start_wait(
        self, dispose: Callable[[], None]
    ) -> Tuple[asyncio.Future, Callable[[Any], None], Callable[[Exception], None]]:
        """The body of waitForPromise(): returns the future of a wait, and the
        functions that settle it.

        Settling ends the wait and calls `dispose`. A failure also disposes the
        waiter and adds the log to the error.
        """
        result: asyncio.Future = self._loop.create_future()
        settled = False

        def finish() -> bool:
            nonlocal settled
            if settled:
                return False
            settled = True
            if reject in self._active_waits:
                self._active_waits.remove(reject)
            dispose()
            return True

        def resolve(value: Any) -> None:
            if not finish():
                return
            if not result.done():
                result.set_result(value)
            if self._dispose_on_settle or result.cancelled():
                self.dispose()

        def reject(error: Exception) -> None:
            if not finish():
                return
            self._error = str(error)
            self.dispose()
            if not result.done():
                result.set_exception(
                    rewrite_error_message(
                        error, str(error) + format_log_recording(self._logs)
                    )
                )

        def on_result_done(_: asyncio.Future) -> None:
            # The caller cancelled the wait.
            if result.cancelled() and finish():
                self.dispose()

        result.add_done_callback(on_result_done)
        error = self._immediate_error or self._failure
        if error:
            reject(error)
        else:
            self._active_waits.append(reject)
        return result, resolve, reject

    def result(self) -> asyncio.Future:
        """The future of the last wait_for_event(), for a waiter that waits for
        one event: the waiter is disposed when it settles."""
        assert self._result
        self._dispose_on_settle = True
        return self._result

    def dispose(self) -> None:
        # Settling and cancelling a wait both dispose the waiter, so dispose once.
        if self._disposed:
            return
        self._disposed = True
        for dispose in self._dispose:
            dispose()
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()

    def log(self, s: str) -> None:
        self._logs.append(s)
        self._send_wait_info(
            {"waitId": self._wait_id, "phase": "log", "message": s}, internal=True
        )


def _wait_for_event(
    waiter: Waiter,
    emitter: EventEmitter,
    event: str,
    predicate: Optional[Callable],
    resolve: Callable[[Any], None],
    reject: Callable[[Exception], None],
) -> Callable[[], None]:
    """Port of waitForEvent() in client/waiter.ts.

    Calls `resolve` with the first event that `predicate` accepts, or `reject` with
    the error of `predicate`. Returns the function that stops listening.
    """

    def remove_listener() -> None:
        if listener in emitter.listeners(event):
            emitter.remove_listener(event, listener)

    def on_match(event_arg: Any) -> None:
        remove_listener()
        resolve(event_arg)

    def on_error(error: Exception) -> None:
        remove_listener()
        reject(error)

    def listener(event_arg: Any = None) -> None:
        if predicate is None:
            on_match(event_arg)
            return
        try:
            matched = predicate(event_arg)
        except Exception as e:
            on_error(e)
            return
        if inspect.iscoroutine(matched):

            async def await_predicate(coro: Any) -> None:
                try:
                    if await coro:
                        on_match(event_arg)
                except Exception as e:
                    on_error(e)

            waiter._pending_tasks.append(
                waiter._loop.create_task(await_predicate(matched))
            )
            return
        if matched:
            on_match(event_arg)

    emitter.on(event, listener)
    return remove_listener


def format_log_recording(log: List[str]) -> str:
    if not log:
        return ""
    header = " logs "
    header_length = 60
    left_length = math.floor((header_length - len(header)) / 2)
    right_length = header_length - len(header) - left_length
    new_line = "\n"
    return f"{new_line}{'=' * left_length}{header}{'=' * right_length}{new_line}{new_line.join(log)}{new_line}{'=' * header_length}"
