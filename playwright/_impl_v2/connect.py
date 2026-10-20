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

"""Port of packages/playwright-core/src/client/connect.ts.

Python differences:

- connect_to_browser() takes the ConnectOptions object with the Python names of the
  options (endpoint, browser_name, headers, expose_network, slow_mo, timeout).
- There is no AbortSignal: connect_to_endpoint() takes the timeout as a number.
- raceAgainstDeadline() of packages/isomorphic/timeoutRunner.ts is ported here, as
  race_against_deadline().
- The send() and close() of JsonPipeTransport are not async functions, so that the
  message goes out at once, as upstream.
- Not ported: WebSocketTransport, the transport of the client in a web page
  (window.WebSocket), which has no LocalUtils; and the __testHookRedirectPortForwarding
  and __testHookBeforeCreateBrowser options of the JavaScript tests.
"""

import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    TypeVar,
    cast,
)

from playwright._impl._errors import Error
from playwright._impl_v2.browser import Browser
from playwright._impl_v2.connection import Connection
from playwright._impl_v2.events import Events
from playwright._impl_v2.internal_structures import HeadersArray
from playwright._impl_v2.isomorphic.string_utils import js_string
from playwright._impl_v2.isomorphic.time import monotonic_time
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.promise import (
    catch,
    clear_timeout,
    race,
    set_timeout,
    then,
)

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.local_utils import LocalUtils
    from playwright._impl_v2.playwright import Playwright
    from playwright._impl_v2.protocol_channels import JsonPipeChannel

T = TypeVar("T")


async def connect_to_browser(
    playwright: "Playwright", params: Dict[str, Any]
) -> Browser:
    deadline = monotonic_time() + params["timeout"] if params.get("timeout") else 0
    name_param = (
        {"x-playwright-browser": params["browser_name"]}
        if params.get("browser_name")
        else {}
    )
    headers = {**name_param, **(params.get("headers") or {})}
    connect_params: Dict[str, Any] = {
        "endpoint": params["endpoint"],
        "headers": headers,
        "exposeNetwork": params.get("expose_network"),
        "slowMo": params.get("slow_mo"),
    }
    # Not ported: the __testHookRedirectPortForwarding option of the JavaScript tests.
    connection = await connect_to_endpoint(
        playwright._connection, connect_params, params.get("timeout") or 0
    )
    browser: Optional[Browser] = None

    def on_close() -> None:
        # Emulate all pages, contexts and the browser closing upon disconnect.
        for context in browser.contexts if browser else []:
            for page in context.pages:
                page._on_close()
            context._on_close()
        set_timeout(lambda: browser._did_close() if browser else None, 0)

    connection.on("close", on_close)

    async def create_browser() -> Browser:
        nonlocal browser
        # Not ported: the __testHookBeforeCreateBrowser option of the JavaScript
        # tests.

        playwright = await connection.initialize_playwright()
        if not playwright._initializer.get("preLaunchedBrowser"):
            connection.close()
            raise Error(
                "Malformed endpoint. Did you use BrowserType.launchServer method?"
            )
        playwright.selectors = playwright.selectors
        browser = Browser.from_(playwright._initializer["preLaunchedBrowser"])
        browser._should_close_connection_on_close = True
        browser.on(Events.Browser.Disconnected, lambda _: connection.close())
        return browser

    result = await race_against_deadline(create_browser, deadline)
    if not result["timedOut"]:
        return result["result"]
    else:
        connection.close()
        raise Error(f"Timeout {js_string(params.get('timeout'))}ms exceeded")


async def connect_to_endpoint(
    parent_connection: Connection, params: Dict[str, Any], timeout: float
) -> Connection:
    local_utils = parent_connection.local_utils()
    # Not ported: WebSocketTransport, for the client in a web page, which has no
    # LocalUtils.
    assert local_utils
    transport: Transport = JsonPipeTransport(local_utils)
    connect_headers = await transport.connect(params, timeout)
    # Python: the connection runs in the event loop of its parent.
    connection = Connection(
        parent_connection._loop,
        local_utils,
        parent_connection._instrumentation,
        cast(List[Dict[str, str]], connect_headers),
    )
    connection.mark_as_remote()
    connection.on("close", lambda: transport.close())

    close_error: Optional[str] = None

    def on_transport_closed(reason: Optional[str] = None) -> None:
        connection.close(reason or close_error)

    transport.on_close(lambda reason: on_transport_closed(reason))

    # Python: onmessage returns nothing; upstream it returns the promise, which
    # nobody uses.
    def onmessage(message: Dict[str, Any]) -> None:
        catch(transport.send(message), lambda _: on_transport_closed())

    connection.onmessage = onmessage

    def on_message(message: Dict[str, Any]) -> None:
        nonlocal close_error
        try:
            connection.dispatch(message)
        except Exception as e:
            # Python: String(e) is the name and the message of the error.
            close_error = f"{e.name if isinstance(e, Error) else type(e).__name__}: {e}"
            catch(transport.close())

    transport.on_message(on_message)
    return connection


class Transport(Protocol):
    def connect(
        self, params: Dict[str, Any], timeout: float
    ) -> Awaitable[HeadersArray]: ...

    def send(self, message: Any) -> Awaitable[None]: ...

    def on_message(self, callback: Callable[[Any], None]) -> None: ...

    def on_close(self, callback: Callable[[Optional[str]], None]) -> None: ...

    def close(self) -> Awaitable[None]: ...


class JsonPipeTransport:
    def __init__(self, owner: "LocalUtils") -> None:
        self._pipe: Optional["JsonPipeChannel"] = None
        self._owner = owner

    async def connect(self, params: Dict[str, Any], timeout: float) -> HeadersArray:
        result = await self._owner._channel.connect(
            endpoint=params["endpoint"],
            headers=params.get("headers"),
            exposeNetwork=params.get("exposeNetwork"),
            slowMo=params.get("slowMo"),
            socksProxyRedirectPortForTest=params.get("socksProxyRedirectPortForTest"),
            timeout=timeout,
        )
        pipe, connect_headers = result["pipe"], result["headers"]
        self._pipe = pipe
        return connect_headers

    def send(self, message: Any) -> "asyncio.Future[None]":
        # Python: not an async def, so that the message goes out at once.
        assert self._pipe  # this._pipe!
        return self._pipe.send(message=message, timeout=NO_TIMEOUT)

    def on_message(self, callback: Callable[[Any], None]) -> None:
        assert self._pipe  # this._pipe!
        self._pipe.onMessage(lambda event: callback(event["message"]))

    def on_close(self, callback: Callable[[Optional[str]], None]) -> None:
        assert self._pipe  # this._pipe!
        self._pipe.onClosed(lambda event: callback(event["reason"]))

    def close(self) -> "asyncio.Future[None]":
        # Python: not an async def, so that the message goes out at once.
        assert self._pipe  # this._pipe!
        return catch(self._pipe.close(timeout=NO_TIMEOUT))


# Not ported: WebSocketTransport, the transport of the client in a web page
# (window.WebSocket).


# Python: port of raceAgainstDeadline() in packages/isomorphic/timeoutRunner.ts.
async def race_against_deadline(
    cb: Callable[[], Awaitable[T]], deadline: float
) -> Dict[str, Any]:
    timer: Optional[asyncio.TimerHandle] = None
    timed_out: "asyncio.Future[Dict[str, Any]]" = (
        asyncio.get_running_loop().create_future()
    )

    def resolve() -> None:
        if not timed_out.done():
            timed_out.set_result({"timedOut": True})

    if deadline:
        timer = set_timeout(resolve, max(0, deadline - monotonic_time()))
    try:
        # Note: not including "await" here truncates the async stack inside cb(), so always include it.
        return await race(
            [
                then(cb(), lambda result: {"result": result, "timedOut": False}),
                timed_out,
            ]
        )
    finally:
        clear_timeout(timer)
