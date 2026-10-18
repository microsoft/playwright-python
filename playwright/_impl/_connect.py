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

"""Port of packages/playwright-core/src/client/connect.ts."""

import asyncio
from typing import TYPE_CHECKING, Dict, Optional, cast

from pyee.asyncio import AsyncIOEventEmitter

from playwright._impl._connection import Connection, from_channel
from playwright._impl._errors import Error
from playwright._impl._helper import ParsedMessagePayload
from playwright._impl._str_utils import js_string
from playwright._impl._time import monotonic_time
from playwright._impl._transport import Transport

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser import Browser
    from playwright._impl._playwright import Playwright
    from playwright._impl._protocol_channels import JsonPipeChannel


async def connect_to_browser(
    playwright: "Playwright",
    browser_name: Optional[str],
    endpoint: str,
    headers: Optional[Dict[str, str]],
    expose_network: Optional[str],
    slow_mo: Optional[float],
    timeout: Optional[float],
) -> "Browser":
    deadline = monotonic_time() + timeout if timeout else 0
    name_param = {"x-playwright-browser": browser_name} if browser_name else {}
    connection = await connect_to_endpoint(
        playwright._connection,
        endpoint=endpoint,
        headers={**name_param, **(headers or {})},
        expose_network=expose_network,
        slow_mo=slow_mo,
        timeout=timeout or 0,
    )
    browser: Optional["Browser"] = None

    def on_close() -> None:
        # Emulate all pages, contexts and the browser closing upon disconnect.
        for context in browser.contexts if browser else []:
            for page in context.pages:
                page._on_close()
            context._on_close()
        if browser:
            # setTimeout(() => browser._didClose(), 0): the API calls that the
            # closure rejects fail before "disconnected". The sync API resumes its
            # greenlet one loop iteration after the call fails, so there the event
            # waits one more iteration.
            loop = connection._loop
            if connection._is_sync:
                loop.call_soon(loop.call_soon, browser._did_close)
            else:
                loop.call_soon(browser._did_close)

    connection.on("close", on_close)

    async def create_browser() -> "Browser":
        nonlocal browser
        remote_playwright: "Playwright" = await connection.playwright_future
        pre_launched_browser = remote_playwright._initializer.get("preLaunchedBrowser")
        if not pre_launched_browser:
            connection.close()
            raise Error(
                "Malformed endpoint. Did you use BrowserType.launchServer method?"
            )
        browser = cast("Browser", from_channel(pre_launched_browser))
        browser._should_close_connection_on_close = True
        browser.on(browser.Events.Disconnected, lambda _: connection.close())
        return browser

    # raceAgainstDeadline() in connect.ts.
    try:
        return await asyncio.wait_for(
            create_browser(),
            max(0, deadline - monotonic_time()) / 1000 if deadline else None,
        )
    except asyncio.TimeoutError:
        connection.close()
        raise Error(f"Timeout {js_string(timeout)}ms exceeded")
    except asyncio.CancelledError:
        # Python only: the caller's task was cancelled.
        connection.close()
        raise


async def connect_to_endpoint(
    parent_connection: Connection,
    endpoint: str,
    headers: Dict[str, str],
    expose_network: Optional[str],
    slow_mo: Optional[float],
    timeout: float,
) -> Connection:
    local_utils = parent_connection.local_utils
    # JsonPipeTransport.connect() in connect.ts. The Python transport connects in
    # Connection.run(), which takes no parameters.
    result = await local_utils._channel.connect(
        endpoint=endpoint,
        headers=headers,
        exposeNetwork=expose_network,
        slowMo=slow_mo,
        socksProxyRedirectPortForTest=None,
        timeout=timeout,
    )
    transport = JsonPipeTransport(parent_connection._loop, result["pipe"])
    connection = Connection(
        parent_connection._dispatcher_fiber,
        transport,
        parent_connection._loop,
        local_utils=local_utils,
    )
    connection.mark_as_remote()
    connection.on("close", transport.request_stop)

    close_error: Optional[str] = None

    def on_transport_closed(reason: Optional[str] = None) -> None:
        connection.close(reason or close_error)

    transport.on("close", on_transport_closed)

    def on_message(message: ParsedMessagePayload) -> None:
        nonlocal close_error
        try:
            connection.dispatch(message)
        except Exception as e:
            close_error = str(e)
            transport.request_stop()

    transport.on_message = on_message

    # The Python connection runs in its own task, and stops with the parent.
    connection._is_sync = parent_connection._is_sync
    parent_connection._child_ws_connections.append(connection)
    parent_connection._loop.create_task(connection.run())
    return connection


class JsonPipeTransport(AsyncIOEventEmitter, Transport):
    """Port of JsonPipeTransport in connect.ts, behind the Transport interface of
    _transport.py: connect_to_endpoint() connects the pipe, on_message is an
    attribute, and "close" is an event."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        pipe: "JsonPipeChannel",
    ) -> None:
        super().__init__(loop)
        Transport.__init__(self, loop)
        self._pipe = pipe
        self._stopped_future: asyncio.Future = loop.create_future()

    async def connect(self) -> None:
        # onMessage() and onClose() in connect.ts.
        self._pipe.onMessage(lambda event: self.on_message(event["message"]))
        self._pipe.onClosed(lambda event: self._on_closed(event["reason"]))

    def _on_closed(self, reason: Optional[str]) -> None:
        self.emit("close", reason)
        if not self._stopped_future.done():
            self._stopped_future.set_result(None)

    async def run(self) -> None:
        await self._stopped_future

    def send(self, message: Dict) -> None:
        # The transport sends synchronously, so this does not wait for the reply. A
        # failed send closes the connection, as onTransportClosed() in connect.ts.
        try:
            self._pipe.send_no_reply("send", {"message": message}, is_internal=True)
        except Error:
            self.emit("close", None)

    def request_stop(self) -> None:
        # close() in connect.ts, which ignores the errors.
        try:
            self._pipe.send_no_reply("close", is_internal=True)
        except Error:
            pass

    def dispose(self) -> None:
        self.on_error_future.cancel()
        self._stopped_future.cancel()

    async def wait_until_stopped(self) -> None:
        await self._stopped_future
