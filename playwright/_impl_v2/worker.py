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

"""Port of packages/playwright-core/src/client/worker.ts.

Python: url is a property, as the generated API reads it. The Python API calls
expect_event(), a context manager around the promise of waitForEvent(). A page
function is JavaScript source, never a function, so assertMaxArguments() is not
ported: the signature takes one argument.
"""

from typing import TYPE_CHECKING, Any, Callable, Optional

from playwright._impl_v2.channel_owner import ChannelOwner, api_call, from_channel
from playwright._impl_v2.console_message import ConsoleMessage
from playwright._impl_v2.errors import TargetClosedError, is_target_closed_error
from playwright._impl_v2.event_context_manager import EventContextManagerImpl
from playwright._impl_v2.events import Events
from playwright._impl_v2.isomorphic.manual_promise import LongStandingScope
from playwright._impl_v2.isomorphic.string_utils import js_string
from playwright._impl_v2.js_handle import JSHandle, parse_result, serialize_argument
from playwright._impl_v2.timeout_settings import NO_TIMEOUT, TimeoutSettings
from playwright._impl_v2.utils.promise import start_eager
from playwright._impl_v2.waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.browser_context import BrowserContext
    from playwright._impl_v2.page import Page
    from playwright._impl_v2.protocol_channels import WorkerChannel


class Worker(ChannelOwner):
    _channel: "WorkerChannel"

    @staticmethod
    def from_nullable(worker: Optional["WorkerChannel"]) -> Optional["Worker"]:
        return Worker.from_(worker) if worker else None

    @staticmethod
    def from_(worker: "WorkerChannel") -> "Worker":
        return from_channel(worker)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.WorkerInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._page: Optional["Page"] = None  # Set for web workers.
        self._context: Optional["BrowserContext"] = None  # Set for service workers.
        self._closed_scope = LongStandingScope()
        self._close_reason: Optional[str] = None

        self._set_event_to_subscription_mapping(
            {
                Events.Worker.Console: "console",
            }
        )
        # Note: we only receive console events here for workers from "chromium._connectToWorker".
        self._channel.onConsole(
            lambda event: self.emit(
                Events.Worker.Console, ConsoleMessage(event, None, self)
            )
        )

        def on_close() -> None:
            if self._page:
                # Python: Set.delete() on the ordered set of the page.
                self._page._workers.pop(self, None)
            if self._context:
                # Python: Set.delete() on the ordered set of the context.
                self._context._service_workers.pop(self, None)
            self.emit(Events.Worker.Close, self)

        self._channel.onClose(on_close)
        self.once(
            Events.Worker.Close,
            lambda _: self._closed_scope.close(self._close_error_with_reason()),
        )

    def _close_error_with_reason(self) -> TargetClosedError:
        if self._close_reason:
            return TargetClosedError(self._close_reason)
        return (
            self._page and self._page._close_error_with_reason()
        ) or TargetClosedError()

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def evaluate(self, expression: str, arg: Any) -> Any:
        # Not ported: assertMaxArguments(arguments.length, 2).
        result = await self._channel.evaluateExpression(
            expression=expression,
            # Python: the expression is a string, which can be a function. JS passes
            # typeof pageFunction === 'function', which is false for a string; None
            # lets the server detect a function, as the Python API documents.
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def evaluate_handle(self, expression: str, arg: Any) -> JSHandle:
        # Not ported: assertMaxArguments(arguments.length, 2).
        result = await self._channel.evaluateExpressionHandle(
            expression=expression,
            # Python: see evaluate().
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return JSHandle.from_(result["handle"])

    @api_call()
    async def wait_for_event(
        self,
        event: str,
        predicate: Optional[Callable[..., Any]],
        timeout: Optional[float],
    ) -> Any:
        # Python: optionsOrPredicate is the predicate and timeout parameters.
        timeout_settings = (
            self._page._timeout_settings
            if self._page
            else (
                self._context._timeout_settings if self._context else TimeoutSettings()
            )
        )
        timeout_options = timeout_settings.timeout(timeout)
        waiter = Waiter.create_for_event(self, event)
        waiter.reject_on_timeout(
            timeout_options,
            # Python: String(number) of JS, so that 30000.0 prints 30000.
            f'Timeout {js_string(timeout_options)}ms exceeded while waiting for event "{event}"',
        )
        if event != Events.Worker.Close:
            waiter.reject_on_event(
                self, Events.Worker.Close, lambda: self._close_error_with_reason()
            )
        result = await waiter.wait_for_event(self, event, predicate)
        waiter.dispose()
        return result

    async def _disconnect(self, reason: Optional[str]) -> None:
        # Python: options is the reason parameter.
        self._close_reason = reason
        try:
            await self._channel.disconnect(reason=reason, timeout=NO_TIMEOUT)
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise

    # Python only: the members of the Python API that upstream does not have.

    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable[..., Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        # Python: waitForEvent() as a context manager. The wait runs in a task, which
        # starts before the action in the with block makes the event happen.
        return EventContextManagerImpl(
            start_eager(
                self.wait_for_event(event=event, predicate=predicate, timeout=timeout)
            )
        )

    def __repr__(self) -> str:
        return f"<Worker url={self.url!r}>"
