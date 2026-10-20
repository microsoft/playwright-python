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

"""Port of packages/playwright-core/src/client/waiter.ts.

Python: there is no AbortSignal, so rejectOnTimeout() takes the timeout only.
"""

import asyncio
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from playwright._impl.errors import TimeoutError
from playwright._impl.utils.crypto import create_guid
from playwright._impl.utils.stack_trace import rewrite_error_message
from playwright._impl.utils.tasks import completed, fire_and_forget, race
from playwright._impl.utils.zones import Zone, current_zone

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.channel_owner import ApiZone, ChannelOwner
    from playwright._impl.event_emitter import EventEmitter


class Waiter:
    def __init__(self, channel_owner: "ChannelOwner", event: str) -> None:
        self._failures: List["asyncio.Future[Any]"] = []
        self._immediate_error: Optional[Exception] = None
        self._logs: List[str] = []
        self._error: Optional[str] = None
        self._wait_id = create_guid()
        self._channel_owner = channel_owner
        self._saved_zone = current_zone().without("apiZone")

        title = f'Wait for event "{event}"'
        self._send_wait_info(
            {"waitId": self._wait_id, "phase": "before", "event": event},
            title=title,
        )
        self._dispose: List[Callable[[], None]] = [
            lambda: self._send_wait_info(
                {"waitId": self._wait_id, "phase": "after", "error": self._error},
                internal=True,
            ),
        ]

    @staticmethod
    def create_for_event(channel_owner: "ChannelOwner", event: str) -> "Waiter":
        return Waiter(channel_owner, event)

    def _send_wait_info(
        self, info: Any, title: Optional[str] = None, internal: bool = False
    ) -> None:
        from playwright._impl.channel_owner import ApiCallOptions

        # Fire-and-forget: server intentionally never replies, and we never throw to the caller.
        owner = self._channel_owner
        # Python: None is undefined in the info.
        info = {k: v for k, v in info.items() if v is not None}

        def send(options: Dict[str, Any]) -> None:
            # Python: `void promise`: the server never replies to __waitInfo__, and an
            # error of the send is dropped.
            try:
                owner._connection.send_message_to_server(
                    owner, "__waitInfo__", info, options
                )
            except Exception:
                pass

        def func(api_zone: "ApiZone") -> Awaitable[None]:
            if api_zone.internal or api_zone.reported:
                send({"internal": True, "timeout": 0})
                return completed(None)
            api_zone.reported = True
            # An outer `_wrapApiCall` may have set its own title (e.g. "Wait for navigation");
            # fall back to ours only when the outer zone left it blank. The title is read both by
            # `onApiCallBegin` (drives the test runner step title) and by `sendMessageToServer`
            # (drives the trace viewer action title), so set it on the zone itself.
            if not api_zone.title:
                api_zone.title = title
            owner._instrumentation.on_api_call_begin(
                api_zone,
                {"type": owner._type, "method": "__waitInfo__", "params": info},
            )
            send({**api_zone.options(), "timeout": 0})
            return completed(None)

        fire_and_forget(
            owner._wrap_api_call(func, ApiCallOptions(title=title, internal=internal))
        )

    def wait_for_event(
        self,
        emitter: "EventEmitter",
        event: str,
        predicate: Optional[Callable[[Any], Any]] = None,
    ) -> Awaitable[Any]:
        # Python: a plain def. The listener is registered at the call, as the JS async
        # function registers it before its first await; the result is the wait.
        promise, dispose = wait_for_event(emitter, event, self._saved_zone, predicate)
        return self.wait_for_promise(promise, dispose)

    def reject_on_event(
        self,
        emitter: "EventEmitter",
        event: str,
        error: Union[Exception, Callable[[], Exception]],
        predicate: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        # Python: promise.then(() => { throw ... }) raises in the listener instead:
        # the failure is set at the event, with no turn of the event loop in between,
        # as the microtask of then() runs before the next macrotask.
        def throw(event_arg: Any) -> Any:
            matched = predicate(event_arg) if predicate else True
            if inspect.isawaitable(matched):

                async def then_throw() -> bool:
                    if not await matched:
                        return False
                    raise error() if callable(error) else error

                return then_throw()
            if not matched:
                return False
            raise error() if callable(error) else error

        promise, dispose = wait_for_event(emitter, event, self._saved_zone, throw)
        self._reject_on(promise, dispose)

    def reject_on_timeout(self, timeout: Optional[float], timeout_message: str) -> None:
        # Python: { timeout, signal } is the timeout; there is no AbortSignal.
        if timeout:
            promise, dispose = wait_for_timeout(timeout)
            failure: "asyncio.Future[None]" = asyncio.get_running_loop().create_future()

            # Python: promise.then(() => { throw ... }) as a done callback.
            def throw(_: "asyncio.Future[None]") -> None:
                if not failure.done():
                    failure.set_exception(TimeoutError(timeout_message))

            promise.add_done_callback(throw)
            self._reject_on(failure, dispose)

    def reject_immediately(self, error: Exception) -> None:
        self._immediate_error = error

    def throw_if_immediately_rejected(self) -> None:
        if self._immediate_error:
            raise self._immediate_error

    def dispose(self) -> None:
        for dispose in self._dispose:
            dispose()

    async def wait_for_promise(
        self,
        promise: Awaitable[Any],
        dispose: Optional[Callable[[], None]] = None,
    ) -> Any:
        try:
            if self._immediate_error:
                raise self._immediate_error
            result = await race([promise, *self._failures])
            if dispose:
                dispose()
            return result
        except asyncio.CancelledError:
            # Python: the task that waits was cancelled, for example by an expect_*()
            # block that raised. Clean up as for an error.
            if dispose:
                dispose()
            self._error = "The operation was aborted"
            self.dispose()
            raise
        except Exception as e:
            if dispose:
                dispose()
            self._error = str(e)
            self.dispose()
            raise rewrite_error_message(
                e, str(e) + format_log_recording(self._logs)
            ) from None

    def log(self, s: str) -> None:
        self._logs.append(s)
        self._send_wait_info(
            {"waitId": self._wait_id, "phase": "log", "message": s}, internal=True
        )

    def _reject_on(
        self,
        failure: "asyncio.Future[Any]",
        dispose: Optional[Callable[[], None]] = None,
    ) -> None:
        # Python: the error of the failure is handled, as the rejection of the
        # promise is handled by the race.
        failure.add_done_callback(lambda f: f.cancelled() or f.exception())
        self._failures.append(failure)
        if dispose:
            self._dispose.append(dispose)


def wait_for_event(
    emitter: "EventEmitter",
    event: str,
    saved_zone: Zone,
    predicate: Optional[Callable[[Any], Any]] = None,
) -> Tuple["asyncio.Future[Any]", Callable[[], None]]:
    promise: "asyncio.Future[Any]" = asyncio.get_event_loop().create_future()

    # Python: a sync listener. The JS listener is an async function, which runs at
    # once up to its first await; so does this one, and an async predicate continues
    # in a task.
    def listener(event_arg: Any) -> Any:
        def settle(matched: bool) -> None:
            if not matched:
                return
            emitter.remove_listener(event, listener)
            if not promise.done():
                promise.set_result(event_arg)

        def fail(e: Exception) -> None:
            emitter.remove_listener(event, listener)
            if not promise.done():
                promise.set_exception(e)

        def run() -> Any:
            try:
                if not predicate:
                    settle(True)
                    return None
                matched = predicate(event_arg)
                if inspect.isawaitable(matched):

                    async def continuation() -> None:
                        try:
                            settle(bool(await matched))
                        except Exception as e:
                            fail(e)

                    # Python: started here, so that it runs in the saved zone.
                    return asyncio.ensure_future(continuation())
                settle(bool(matched))
            except Exception as e:
                fail(e)
            return None

        return saved_zone.run(run)

    emitter.add_listener(event, listener)

    def dispose() -> None:
        emitter.remove_listener(event, listener)

    return promise, dispose


def wait_for_timeout(
    timeout: float,
) -> Tuple["asyncio.Future[None]", Callable[[], None]]:
    loop = asyncio.get_running_loop()
    promise: "asyncio.Future[None]" = loop.create_future()

    def resolve() -> None:
        if not promise.done():
            promise.set_result(None)

    # Python: setTimeout() takes milliseconds; call_later() takes seconds.
    timeout_id = loop.call_later(timeout / 1000, resolve)

    def dispose() -> None:
        timeout_id.cancel()

    return promise, dispose


def format_log_recording(log: List[str]) -> str:
    if not log:
        return ""
    header = " logs "
    header_length = 60
    left_length = (header_length - len(header)) // 2
    right_length = header_length - len(header) - left_length
    return (
        f"\n{'=' * left_length}{header}{'=' * right_length}\n"
        + "\n".join(log)
        + f"\n{'=' * header_length}"
    )
