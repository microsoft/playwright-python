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
from asyncio.tasks import Task
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pyee import EventEmitter

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import Error, TimeoutError


class Waiter:
    # Port of packages/playwright-core/src/client/waiter.ts. `event` is the name of the
    # event that it waits for, "" when it waits for something else; `title` replaces
    # the title of the wait, as the title of the outer API call does upstream.
    def __init__(
        self, channel_owner: ChannelOwner, event: str, title: Optional[str] = None
    ) -> None:
        self._wait_id = uuid.uuid4().hex
        self._loop = channel_owner._loop
        self._pending_tasks: List[Task] = []
        self._channel = channel_owner._channel
        self._connection = channel_owner._connection
        self._logs: List[str] = []
        self._error: Optional[str] = None
        # The first rejection; it fails the active waits and the later ones.
        self._failure: Optional[Exception] = None
        self._active_waits: List[Callable[[Exception], None]] = []
        self._dispose_callbacks: List[Callable[[], None]] = []
        self._disposed = False
        self._dispose_on_settle = False
        self._result: Optional[asyncio.Future] = None
        self._wait_for_event_info_before(
            self._wait_id, event, title or f'Wait for event "{event}"'
        )

    def _wait_for_event_info_before(self, wait_id: str, event: str, title: str) -> None:
        self._send_wait_for_event_info(
            {
                "waitId": wait_id,
                "phase": "before",
                "event": event,
            },
            title=title,
        )

    def _wait_for_event_info_after(
        self, wait_id: str, error: Optional[str] = None
    ) -> None:
        self._send_wait_for_event_info(
            {
                "waitId": wait_id,
                "phase": "after",
                **({"error": error} if error else {}),
            },
            is_internal=True,
        )

    def _send_wait_for_event_info(
        self, params: Dict[str, Any], is_internal: bool = False, title: str = None
    ) -> None:
        # Wait info is fire-and-forget telemetry and must not affect the waiter.
        try:
            # An outer api_call() may have left the title blank; then the wait
            # names the call, as _sendWaitInfo() in waiter.ts does.
            zone = self._connection._api_zone.get()
            if zone is not None and title and not zone["title"]:
                zone["title"] = title
            self._channel.send_no_reply(
                "__waitInfo__",
                params,
                is_internal=is_internal,
                title=title,
            )
        except Error:
            pass

    def reject_on_event(
        self,
        emitter: EventEmitter,
        event: str,
        error: Union[Error, Callable[..., Error]],
        predicate: Callable = None,
    ) -> None:
        def on_match() -> None:
            self._fail(error() if callable(error) else error)

        def listener(event_data: Any = None) -> None:
            self._evaluate_predicate(predicate, event_data, on_match, self._fail)

        emitter.on(event, listener)
        self._dispose_callbacks.append(lambda: emitter.remove_listener(event, listener))

    def reject_immediately(self, error: Exception) -> None:
        """Port of Waiter.rejectImmediately() in client/waiter.ts: the waits fail with error."""
        self._fail(error)

    def reject_on_timeout(self, timeout: float, message: str) -> None:
        if timeout == 0:
            return
        handle = self._loop.call_later(
            timeout / 1000, lambda: self._fail(TimeoutError(message))
        )
        self._dispose_callbacks.append(handle.cancel)

    def _fail(self, error: Exception) -> None:
        if self._failure:
            return
        self._failure = error
        for fail in list(self._active_waits):
            fail(error)

    def wait_for_event(
        self,
        emitter: EventEmitter,
        event: str,
        predicate: Callable = None,
    ) -> asyncio.Future:
        """Starts to listen right away.

        Returns a future that settles with the event, or fails when the waiter
        fails first.
        """

        def listener(event_data: Any = None) -> None:
            self._evaluate_predicate(
                predicate, event_data, lambda: resolve(event_data), fail
            )

        emitter.on(event, listener)
        result, resolve, fail = self._start_wait(
            lambda: emitter.remove_listener(event, listener)
        )
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
                fail(error)

        def cancel() -> None:
            future.remove_done_callback(on_done)
            if not future.done():
                future.cancel()
            if dispose:
                dispose()

        future.add_done_callback(on_done)
        result, resolve, fail = self._start_wait(cancel)
        return result

    def _start_wait(
        self, dispose: Callable[[], None]
    ) -> Tuple[asyncio.Future, Callable[[Any], None], Callable[[Exception], None]]:
        """Returns the future of a wait, and the functions that settle it.

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
            if fail in self._active_waits:
                self._active_waits.remove(fail)
            dispose()
            return True

        def resolve(value: Any) -> None:
            if not finish():
                return
            if not result.done():
                result.set_result(value)
            if self._dispose_on_settle or result.cancelled():
                self.dispose()

        def fail(error: Exception) -> None:
            if not finish():
                return
            self._error = str(error)
            self.dispose()
            base_class = TimeoutError if isinstance(error, TimeoutError) else Error
            if not result.done():
                result.set_exception(
                    base_class(str(error) + format_log_recording(self._logs))
                )

        def on_result_done(_: asyncio.Future) -> None:
            # The caller cancelled the wait.
            if result.cancelled() and finish():
                self.dispose()

        result.add_done_callback(on_result_done)
        if self._failure:
            fail(self._failure)
        else:
            self._active_waits.append(fail)
        return result, resolve, fail

    def result(self) -> asyncio.Future:
        """The future of the last wait_for_event(), for a waiter that waits for
        one event: the waiter is disposed when it settles."""
        assert self._result
        self._dispose_on_settle = True
        return self._result

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        for dispose in self._dispose_callbacks:
            dispose()
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._wait_for_event_info_after(self._wait_id, self._error)

    def _evaluate_predicate(
        self,
        predicate: Optional[Callable],
        event_data: Any,
        on_match: Callable[[], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        if predicate is None:
            on_match()
            return
        try:
            result = predicate(event_data)
        except Exception as e:
            on_error(e)
            return
        if inspect.iscoroutine(result):

            async def _await_predicate(coro: Any) -> None:
                try:
                    matched = await coro
                except Exception as e:
                    on_error(e)
                    return
                if matched:
                    on_match()

            self._pending_tasks.append(self._loop.create_task(_await_predicate(result)))
            return
        if result:
            on_match()

    def log(self, message: str) -> None:
        self._logs.append(message)
        self._send_wait_for_event_info(
            {
                "waitId": self._wait_id,
                "phase": "log",
                "message": message,
            },
            is_internal=True,
        )


def format_log_recording(log: List[str]) -> str:
    if not log:
        return ""
    header = " logs "
    header_length = 60
    left_length = math.floor((header_length - len(header)) / 2)
    right_length = header_length - len(header) - left_length
    new_line = "\n"
    return f"{new_line}{'=' * left_length}{header}{'=' * right_length}{new_line}{new_line.join(log)}{new_line}{'=' * header_length}"
