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
import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Set,
    TypedDict,
    Union,
    cast,
)

from playwright._impl._api_structures import (
    ClientCertificate,
    Cookie,
    Geolocation,
    HttpCredentials,
    SetCookieParam,
    StorageState,
    ViewportSize,
    WebErrorLocation,
)
from playwright._impl._cdp_session import CDPSession
from playwright._impl._clock import Clock
from playwright._impl._connection import (
    ChannelOwner,
    api_call,
    from_channel,
    from_nullable_channel,
    internal,
)
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._credentials import Credentials
from playwright._impl._debugger import Debugger
from playwright._impl._dialog import Dialog
from playwright._impl._disposable import Disposable, DisposableStub
from playwright._impl._errors import Error, TargetClosedError, parse_error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._file_utils import mkdir_if_needed
from playwright._impl._frame import Frame
from playwright._impl._har_router import HarRouter
from playwright._impl._headers import headers_object_to_array
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    async_readfile,
    async_writefile,
    create_task_and_ignore_exception,
    evaluation_script,
    json_stringify,
)
from playwright._impl._network import (
    Request,
    Response,
    Route,
    RouteHandler,
    RouteHandlerCallback,
    WebSocketRoute,
    WebSocketRouteHandler,
    WebSocketRouteHandlerCallback,
    to_clear_cookies_params,
    validate_headers,
)
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._str_utils import js_string
from playwright._impl._timeout_settings import TimeoutSettings
from playwright._impl._tracing import Tracing
from playwright._impl._url_match import URLMatch, url_matches_equal
from playwright._impl._waiter import Waiter
from playwright._impl._web_error import WebError
from playwright._impl._whatwg_url import parse_url

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._browser import Browser
    from playwright._impl._fetch import APIRequestContext
    from playwright._impl._protocol_channels import BrowserContextChannel


class BrowserContext(ChannelOwner):
    _channel: "BrowserContextChannel"

    Events = SimpleNamespace(
        # Deprecated in v1.56, never emitted anymore.
        BackgroundPage="backgroundpage",
        Close="close",
        Console="console",
        Dialog="dialog",
        DialogClosed="dialogclosed",
        Download="download",
        FrameAttached="frameattached",
        FrameDetached="framedetached",
        FrameNavigated="framenavigated",
        Page="page",
        PageClose="pageclose",
        PageLoad="pageload",
        WebError="weberror",
        ServiceWorker="serviceworker",
        Request="request",
        Response="response",
        RequestFailed="requestfailed",
        RequestFinished="requestfinished",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._pages: List[Page] = []
        self._routes: List[RouteHandler] = []
        self._web_socket_routes: List[WebSocketRouteHandler] = []
        # Browser is null for browser contexts created outside of normal browser, e.g. android or electron.
        self._browser: Optional["Browser"] = None
        self._bindings: Dict[str, Any] = {}
        self._owner_page: Optional[Page] = None
        self._service_workers: Set[Worker] = set()
        self._closing_status: Literal["none", "closing", "closed"] = "none"
        self._close_reason: Optional[str] = None
        self._har_routers: List[HarRouter] = []

        self._options: Dict[str, Any] = initializer["options"]
        self._timeout_settings = TimeoutSettings(None)
        self._debugger: Debugger = cast(Debugger, from_channel(initializer["debugger"]))
        self._tracing = cast(Tracing, from_channel(initializer["tracing"]))
        self._request: "APIRequestContext" = from_channel(initializer["requestContext"])
        self._request._timeout_settings = self._timeout_settings
        self._clock = Clock(self)
        self._credentials = Credentials(self)

        self._channel.onBindingCall(
            lambda event: self._loop.create_task(
                self._on_binding(from_channel(event["binding"]))
            )
        )
        self._channel.onClose(lambda: self._on_close())
        self._channel.onPage(lambda event: self._on_page(from_channel(event["page"])))
        self._channel.onRoute(
            lambda event: self._loop.create_task(
                self._on_route(
                    from_channel(event["route"]),
                )
            ),
        )
        self._channel.onWebSocketRoute(
            lambda event: self._loop.create_task(
                self._on_web_socket_route(
                    from_channel(event["webSocketRoute"]),
                )
            ),
        )
        self._channel.onServiceWorker(
            lambda event: self._on_service_worker(from_channel(event["worker"]))
        )
        self._channel.onConsole(self._on_console_message)
        self._channel.onPageError(
            lambda event: self._on_page_error(
                parse_error(event["error"]),
                from_channel(event["page"]),
                event["location"],
            ),
        )
        self._channel.onDialog(
            lambda event: self._on_dialog(from_channel(event["dialog"]))
        )
        self._channel.onDialogClosed(
            lambda event: self._on_dialog_closed(from_channel(event["dialog"]))
        )
        self._channel.onRequest(
            lambda event: self._on_request(
                from_channel(event["request"]),
                from_nullable_channel(event["page"]),
            ),
        )
        self._channel.onRequestFailed(
            lambda event: self._on_request_failed(
                from_channel(event["request"]),
                event["responseEndTiming"],
                event["failureText"],
                from_nullable_channel(event["page"]),
            ),
        )
        self._channel.onRequestFinished(
            lambda event: self._on_request_finished(
                from_channel(event["request"]),
                from_nullable_channel(event["response"]),
                event["responseEndTiming"],
                from_nullable_channel(event["page"]),
            ),
        )
        self._channel.onResponse(
            lambda event: self._on_response(
                from_channel(event["response"]),
                from_nullable_channel(event["page"]),
            ),
        )
        self._closed_future: asyncio.Future = self._loop.create_future()
        self.once(
            self.Events.Close, lambda context: self._closed_future.set_result(True)
        )

        self._set_event_to_subscription_mapping(
            {
                BrowserContext.Events.Console: "console",
                BrowserContext.Events.Dialog: "dialog",
                BrowserContext.Events.DialogClosed: "dialogClosed",
                BrowserContext.Events.Request: "request",
                BrowserContext.Events.Response: "response",
                BrowserContext.Events.RequestFinished: "requestFinished",
                BrowserContext.Events.RequestFailed: "requestFailed",
            }
        )

    def __repr__(self) -> str:
        return f"<BrowserContext browser={self.browser}>"

    async def _initialize_har_from_options(
        self,
        record_har_path: Optional[Union[Path, str]],
        record_har_content: Optional[HarContentPolicy],
        record_har_omit_content: Optional[bool],
        record_har_url_filter: Optional[Union[Pattern[str], str]],
        record_har_mode: Optional[HarMode],
    ) -> None:
        if not record_har_path:
            return
        record_har_path = str(record_har_path)
        default_policy: HarContentPolicy = (
            "attach" if record_har_path.endswith(".zip") else "embed"
        )
        content_policy: HarContentPolicy = record_har_content or (
            "omit" if record_har_omit_content is True else default_policy
        )
        await self._tracing._record_into_har(
            har=record_har_path,
            page=None,
            url=record_har_url_filter,
            update_content=content_policy,
            update_mode=(record_har_mode or "full"),
        )

    def _on_page(self, page: Page) -> None:
        self._pages.append(page)
        self.emit(BrowserContext.Events.Page, page)
        if page._opener and not page._opener.is_closed():
            page._opener.emit(Page.Events.Popup, page)

    def _on_request(self, request: Request, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Request, request)
        if page:
            page.emit(Page.Events.Request, request)

    def _on_response(self, response: Response, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Response, response)
        if page:
            page.emit(Page.Events.Response, response)

    def _on_request_failed(
        self,
        request: Request,
        response_end_timing: float,
        failure_text: Optional[str],
        page: Optional[Page],
    ) -> None:
        request._failure_text = failure_text or None
        request._set_response_end_timing(response_end_timing)
        self.emit(BrowserContext.Events.RequestFailed, request)
        if page:
            page.emit(Page.Events.RequestFailed, request)

    def _on_request_finished(
        self,
        request: Request,
        response: Optional[Response],
        response_end_timing: float,
        page: Optional[Page],
    ) -> None:
        request._set_response_end_timing(response_end_timing)
        self.emit(BrowserContext.Events.RequestFinished, request)
        if page:
            page.emit(Page.Events.RequestFinished, request)
        if response:
            response._finished_future.set_result(True)

    async def _on_route(self, route: Route) -> None:
        route._context = self
        page = route.request._safe_page()
        route_handlers = self._routes.copy()
        for route_handler in route_handlers:
            # If the page or the context was closed we stall all requests right away.
            if (page and page._close_was_called) or self.is_closed():
                return
            if not route_handler.matches(route.request.url):
                continue
            if route_handler not in self._routes:
                continue
            if route_handler.will_expire():
                self._routes.remove(route_handler)
            handled = await route_handler.handle(route)
            if not self._routes:
                create_task_and_ignore_exception(
                    self._loop, self._disable_interception()
                )
            if handled:
                return
        try:
            # If the page is closed or unrouteAll() was called without waiting and interception disabled,
            # the method will throw an error - silence it.
            await route._inner_continue(True)
        except Exception:
            pass

    async def _on_web_socket_route(self, web_socket_route: WebSocketRoute) -> None:
        route_handler = next(
            (
                route_handler
                for route_handler in self._web_socket_routes
                if route_handler.matches(web_socket_route.url)
            ),
            None,
        )
        if route_handler:
            await route_handler.handle(web_socket_route)
        else:
            web_socket_route.connect_to_server()

    async def _on_binding(self, binding_call: BindingCall) -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func is None:
            return
        await binding_call.call(func)

    def _on_service_worker(self, worker: Worker) -> None:
        worker._context = self
        self._service_workers.add(worker)
        self.emit(BrowserContext.Events.ServiceWorker, worker)

    def _on_console_message(self, event: "channels.BrowserContextConsoleEvent") -> None:
        worker: Optional[Worker] = from_nullable_channel(event["worker"])
        page: Optional[Page] = from_nullable_channel(event["page"])
        message = ConsoleMessage(
            event, page, worker, self._loop, self._dispatcher_fiber
        )
        if worker:
            worker.emit(Worker.Events.Console, message)
        if page:
            page.emit(Page.Events.Console, message)
        if worker and worker in self._service_workers:
            # A service worker's messages go to the pages in its scope too.
            scope = self._service_worker_scope(worker)
            for scope_page in self._pages:
                if scope and scope_page.url.startswith(scope):
                    scope_page.emit(Page.Events.Console, message)
        self.emit(BrowserContext.Events.Console, message)

    def _on_page_error(
        self, error: Error, page: Page, location: WebErrorLocation
    ) -> None:
        self.emit(
            BrowserContext.Events.WebError,
            WebError(self._loop, self._dispatcher_fiber, page, error, location),
        )
        if page:
            page.emit(Page.Events.PageError, error)

    def _on_dialog(self, dialog: Dialog) -> None:
        has_listeners = self.emit(BrowserContext.Events.Dialog, dialog)
        page = dialog.page
        if page:
            has_listeners = page.emit(Page.Events.Dialog, dialog) or has_listeners
        if not has_listeners:
            # Although we do similar handling on the server side, we still need this logic
            # on the client side due to a possible race condition between two async calls:
            # a) removing "dialog" listener subscription (client->server)
            # b) actual "dialog" event (server->client)
            if dialog.type == "beforeunload":
                create_task_and_ignore_exception(
                    self._loop, dialog._channel.accept(promptText=None)
                )
            else:
                create_task_and_ignore_exception(self._loop, dialog._channel.dismiss())

    def _on_dialog_closed(self, dialog: Dialog) -> None:
        self.emit(BrowserContext.Events.DialogClosed, dialog)
        page = dialog.page
        if page:
            page.emit(Page.Events.DialogClosed, dialog)

    # Upstream: BrowserContext._serviceWorkerScope().
    def _service_worker_scope(self, service_worker: Worker) -> Optional[str]:
        url = parse_url(".", service_worker.url)
        if url is None:
            return None
        scope = url.href
        if not scope.endswith("/"):
            scope += "/"
        return scope

    def set_default_navigation_timeout(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_timeout(timeout)

    @property
    def browser(self) -> Optional["Browser"]:
        return self._browser

    @property
    def pages(self) -> List[Page]:
        return self._pages.copy()

    def is_closed(self) -> bool:
        return self._closing_status != "none"

    async def new_page(self) -> Page:
        if self._owner_page:
            raise Error("Please use browser.new_context()")
        return from_channel((await self._channel.newPage())["page"])

    async def cookies(self, urls: Optional[Union[str, Sequence[str]]]) -> List[Cookie]:
        if not urls:
            urls = []
        if isinstance(urls, str):
            urls = [urls]
        result = await self._channel.cookies(urls=urls)
        return cast(List[Cookie], result["cookies"])

    async def add_cookies(self, cookies: Sequence[SetCookieParam]) -> None:
        await self._channel.addCookies(
            cookies=cast("Sequence[channels.SetNetworkCookie]", cookies)
        )

    async def clear_cookies(
        self,
        name: Optional[Union[str, Pattern[str]]],
        domain: Optional[Union[str, Pattern[str]]],
        path: Optional[Union[str, Pattern[str]]],
    ) -> None:
        await self._channel.clearCookies(**to_clear_cookies_params(name, domain, path))

    async def grant_permissions(
        self, permissions: Sequence[str], origin: Optional[str]
    ) -> None:
        await self._channel.grantPermissions(permissions=permissions, origin=origin)

    async def clear_permissions(self) -> None:
        await self._channel.clearPermissions()

    async def set_geolocation(self, geolocation: Optional[Geolocation]) -> None:
        await self._channel.setGeolocation(
            geolocation=cast(
                "Optional[channels.BrowserContextSetGeolocationParamsGeolocation]",
                geolocation,
            )
        )

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        validate_headers(headers)
        await self._channel.setExtraHTTPHeaders(
            headers=headers_object_to_array(headers)
        )

    async def set_offline(self, offline: bool) -> None:
        await self._channel.setOffline(offline=offline)

    async def add_init_script(
        self, script: Optional[str], path: Optional[Union[str, Path]]
    ) -> Disposable:
        source = await evaluation_script(script, path)
        result = await self._channel.addInitScript(source=source)
        return from_channel(result["disposable"])

    async def expose_binding(self, name: str, callback: Callable) -> Disposable:
        result = await self._channel.exposeBinding(name=name, noGlobal=None)
        self._bindings[name] = callback
        return from_channel(result["disposable"])

    async def expose_function(self, name: str, callback: Callable) -> Disposable:
        result = await self._channel.exposeBinding(name=name, noGlobal=None)
        self._bindings[name] = lambda source, *args: callback(*args)
        return from_channel(result["disposable"])

    @api_call(title="Route requests")
    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: Optional[int]
    ) -> DisposableStub:
        self._routes.insert(
            0,
            RouteHandler(self._options.get("baseURL"), url, handler, times),
        )
        await self._update_interception_patterns()
        return DisposableStub(lambda: self.unroute(url=url, handler=handler), self)

    @api_call(title="Route WebSockets")
    async def route_web_socket(
        self, url: URLMatch, handler: WebSocketRouteHandlerCallback
    ) -> None:
        self._web_socket_routes.insert(
            0,
            WebSocketRouteHandler(self._options.get("baseURL"), url, handler),
        )
        await self._update_web_socket_interception_patterns()

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Optional[Union[Pattern[str], str]],
        not_found: Optional[Literal["abort", "fallback"]],
        update: Optional[bool],
        update_content: Optional[Literal["attach", "embed"]],
        update_mode: Optional[HarMode],
    ) -> None:
        local_utils = self._connection.local_utils
        if update:
            await self._tracing._record_into_har(
                har=har,
                page=None,
                url=url,
                update_content=update_content,
                update_mode=update_mode,
            )
            return
        har_router = await HarRouter.create(
            local_utils=local_utils,
            file=str(har),
            not_found_action=not_found or "abort",
            url_match=url,
        )
        self._har_routers.append(har_router)
        await har_router.add_context_route(self)

    def _dispose_har_routers(self) -> None:
        for router in self._har_routers:
            router.dispose()
        self._har_routers = []

    @api_call(title="Unroute requests")
    async def unroute_all(
        self, behavior: Optional[Literal["default", "ignoreErrors", "wait"]]
    ) -> None:
        await self._unroute_internal(self._routes, [], behavior)
        self._dispose_har_routers()

    @api_call(title="Unroute requests")
    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback]
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            if url_matches_equal(route.url, url) and (
                not handler or route.handler == handler
            ):
                removed.append(route)
            else:
                remaining.append(route)
        await self._unroute_internal(removed, remaining, "default")

    async def _unroute_internal(
        self,
        removed: List[RouteHandler],
        remaining: List[RouteHandler],
        behavior: Optional[Literal["default", "ignoreErrors", "wait"]],
    ) -> None:
        self._routes = remaining
        if behavior and behavior != "default":
            await asyncio.gather(
                *[route_handler.stop(behavior) for route_handler in removed]
            )
        await self._update_interception_patterns()

    @internal
    async def _disable_interception(self) -> None:
        await self._update_interception_patterns()

    async def _update_interception_patterns(self) -> None:
        await self._channel.setNetworkInterceptionPatterns(
            patterns=RouteHandler.prepare_interception_patterns(self._routes)
        )

    async def _update_web_socket_interception_patterns(self) -> None:
        await self._channel.setWebSocketInterceptionPatterns(
            patterns=WebSocketRouteHandler.prepare_interception_patterns(
                self._web_socket_routes
            )
        )

    def _effective_close_reason(self) -> Optional[str]:
        if self._close_reason:
            return self._close_reason
        if self._browser:
            return self._browser._close_reason
        return None

    # Port of waitForEvent() in browserContext.ts.
    @api_call
    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        timeout = self._timeout_settings.timeout(timeout)
        waiter = Waiter.create_for_event(self, event)
        waiter.reject_on_timeout(
            timeout,
            f'Timeout {js_string(timeout)}ms exceeded while waiting for event "{event}"',
        )
        if event != BrowserContext.Events.Close:
            waiter.reject_on_event(
                self,
                BrowserContext.Events.Close,
                lambda: TargetClosedError(self._effective_close_reason()),
            )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    @api_call
    async def wait_for_event(
        self, event: str, predicate: Optional[Callable], timeout: Optional[float]
    ) -> Any:
        async with self.expect_event(
            event=event, predicate=predicate, timeout=timeout
        ) as event_info:
            pass
        return await event_info

    def expect_console_message(
        self,
        predicate: Optional[Callable[[ConsoleMessage], bool]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(
            event=BrowserContext.Events.Console, predicate=predicate, timeout=timeout
        )

    def expect_page(
        self,
        predicate: Optional[Callable[[Page], bool]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Page]:
        return self.expect_event(
            event=BrowserContext.Events.Page, predicate=predicate, timeout=timeout
        )

    async def storage_state(
        self,
        path: Optional[Union[str, Path]],
        indexed_db: Optional[bool],
        opfs: Optional[bool],
        credentials: Optional[bool],
    ) -> StorageState:
        result = await self._channel.storageState(
            indexedDB=indexed_db, opfs=opfs, credentials=credentials
        )
        # Leave out the fields that the driver did not send, such as "credentials".
        state = {key: value for key, value in result.items() if value is not None}
        if path:
            mkdir_if_needed(path)
            # JSON.stringify(state, undefined, 2), written as UTF-8.
            await async_writefile(path, json_stringify(state, indent=2).encode())
        return cast(StorageState, state)

    async def set_storage_state(
        self, storage_state: Union[StorageState, str, Path]
    ) -> None:
        await self._channel.setStorageState(
            storageState=await prepare_storage_state(storage_state)
        )

    @property
    def background_pages(self) -> List[Page]:
        return []

    @property
    def service_workers(self) -> List[Worker]:
        return list(self._service_workers)

    async def new_cdp_session(self, page: Union[Page, Frame]) -> CDPSession:
        if not isinstance(page, Page) and not isinstance(page, Frame):
            raise Error("page: expected Page or Frame")
        result = await self._channel.newCDPSession(
            page=None if isinstance(page, Frame) else page._channel,
            frame=None if isinstance(page, Page) else page._channel,
        )
        return from_channel(result["session"])

    @property
    def tracing(self) -> Tracing:
        return self._tracing

    @property
    def debugger(self) -> Debugger:
        return self._debugger

    @property
    def request(self) -> "APIRequestContext":
        return self._request

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def credentials(self) -> Credentials:
        return self._credentials

    def _on_close(self) -> None:
        self._closing_status = "closed"
        if self._browser:
            if self in self._browser._contexts:
                self._browser._contexts.remove(self)
            if self._browser._browser_type:
                self._browser._browser_type._playwright.selectors._contexts_for_selectors.discard(
                    self
                )
        self._dispose_har_routers()
        self._tracing._reset_stack_counter()
        self._request._tracing._reset_stack_counter()
        self.emit(BrowserContext.Events.Close, self)

    async def close(self, reason: Optional[str]) -> None:
        if self.is_closed():
            return
        self._close_reason = reason
        self._closing_status = "closing"

        await self.request.dispose(reason=reason)

        # Upstream: BrowserContext.close() in client/browserContext.ts closes the
        # context even when saving the HAR fails, and throws the error after.
        har_error: Optional[Exception] = None
        try:
            await self._tracing._export_all_hars()
        except Exception as error:
            har_error = error
        await self._channel.close(reason=reason)
        await self._closed_future
        if har_error:
            raise har_error


async def prepare_storage_state(
    storage_state: Union[StorageState, str, Path],
) -> "channels.BrowserNewContextParamsStorageState":
    if isinstance(storage_state, dict):
        return cast("channels.BrowserNewContextParamsStorageState", storage_state)
    try:
        return json.loads((await async_readfile(storage_state)).decode())
    except Exception as error:
        raise Error(
            f"Error reading storage state from {storage_state}:\n{error}"
        ) from error


# channels.BrowserNewContextParams in browserContext.ts, without "proxy" and
# "storageState": they are context options of Browser.newContext() only, and
# BrowserType.launchPersistentContext() passes "proxy" as a launch option.
class BrowserContextParams(TypedDict):
    noDefaultViewport: Optional[bool]
    viewport: Optional["channels.BrowserNewContextParamsViewport"]
    screen: Optional["channels.BrowserNewContextParamsScreen"]
    ignoreHTTPSErrors: Optional[bool]
    clientCertificates: Optional[
        List["channels.BrowserNewContextParamsClientCertificates"]
    ]
    javaScriptEnabled: Optional[bool]
    bypassCSP: Optional[bool]
    userAgent: Optional[str]
    locale: Optional[str]
    timezoneId: Optional[str]
    geolocation: Optional["channels.BrowserNewContextParamsGeolocation"]
    permissions: Optional[Sequence[str]]
    extraHTTPHeaders: Optional[List["channels.NameValue"]]
    offline: Optional[bool]
    httpCredentials: Optional[List["channels.HttpCredentials"]]
    deviceScaleFactor: Optional[float]
    isMobile: Optional[bool]
    hasTouch: Optional[bool]
    colorScheme: Optional[Literal["dark", "light", "no-preference", "no-override"]]
    reducedMotion: Optional[Literal["reduce", "no-preference", "no-override"]]
    forcedColors: Optional[Literal["active", "none", "no-override"]]
    acceptDownloads: Optional[Literal["accept", "deny"]]
    contrast: Optional[Literal["no-preference", "more", "no-override"]]
    baseURL: Optional[str]
    recordVideo: Optional["channels.BrowserNewContextParamsRecordVideo"]
    strictSelectors: Optional[bool]
    serviceWorkers: Optional[Literal["allow", "block"]]
    selectorEngines: Optional[Sequence["channels.SelectorEngine"]]
    testIdAttributeName: Optional[str]


async def prepare_browser_context_params(
    viewport: Optional[ViewportSize],
    screen: Optional[ViewportSize],
    no_viewport: Optional[bool],
    ignore_https_errors: Optional[bool],
    java_script_enabled: Optional[bool],
    bypass_csp: Optional[bool],
    user_agent: Optional[str],
    locale: Optional[str],
    timezone_id: Optional[str],
    geolocation: Optional[Geolocation],
    permissions: Optional[Sequence[str]],
    extra_http_headers: Optional[Dict[str, str]],
    offline: Optional[bool],
    http_credentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
    device_scale_factor: Optional[float],
    is_mobile: Optional[bool],
    has_touch: Optional[bool],
    color_scheme: Optional[ColorScheme],
    reduced_motion: Optional[ReducedMotion],
    forced_colors: Optional[ForcedColors],
    contrast: Optional[Contrast],
    accept_downloads: Optional[bool],
    base_url: Optional[str],
    record_video_dir: Optional[Union[Path, str]],
    record_video_size: Optional[ViewportSize],
    record_video_fps: Optional[int],
    strict_selectors: Optional[bool],
    service_workers: Optional[ServiceWorkersPolicy],
    client_certificates: Optional[List[ClientCertificate]],
    selector_engines: Sequence["channels.SelectorEngine"],
    test_id_attribute_name: Optional[str],
) -> BrowserContextParams:
    if extra_http_headers:
        validate_headers(extra_http_headers)
    return {
        "noDefaultViewport": bool(no_viewport),
        "viewport": viewport,
        "screen": screen,
        "ignoreHTTPSErrors": ignore_https_errors,
        "clientCertificates": await to_client_certificates_protocol(
            client_certificates
        ),
        "javaScriptEnabled": java_script_enabled,
        "bypassCSP": bypass_csp,
        "userAgent": user_agent,
        "locale": locale,
        "timezoneId": timezone_id,
        "geolocation": cast(
            "Optional[channels.BrowserNewContextParamsGeolocation]", geolocation
        ),
        "permissions": permissions,
        "extraHTTPHeaders": (
            headers_object_to_array(extra_http_headers)
            if extra_http_headers is not None
            else None
        ),
        "offline": offline,
        "httpCredentials": to_http_credentials_protocol(http_credentials),
        "deviceScaleFactor": device_scale_factor,
        "isMobile": is_mobile,
        "hasTouch": has_touch,
        "colorScheme": "no-override" if color_scheme == "null" else color_scheme,
        "reducedMotion": "no-override" if reduced_motion == "null" else reduced_motion,
        "forcedColors": "no-override" if forced_colors == "null" else forced_colors,
        "contrast": "no-override" if contrast == "null" else contrast,
        "acceptDownloads": to_accept_downloads_protocol(accept_downloads),
        "baseURL": base_url,
        "recordVideo": (
            {
                "dir": os.path.abspath(record_video_dir),
                "size": record_video_size,
                "fps": record_video_fps,
            }
            if record_video_dir is not None
            else None
        ),
        "strictSelectors": strict_selectors,
        "serviceWorkers": service_workers,
        "selectorEngines": selector_engines,
        "testIdAttributeName": test_id_attribute_name,
    }


def to_http_credentials_protocol(
    credentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
) -> Optional[List["channels.HttpCredentials"]]:
    if credentials is None:
        return None
    credentials_list = (
        [credentials] if isinstance(credentials, dict) else list(credentials)
    )
    # The protocol does not accept null fields in the objects of an array.
    return [
        cast(
            "channels.HttpCredentials",
            {key: value for key, value in item.items() if value is not None},
        )
        for item in credentials_list
    ] or None


def to_accept_downloads_protocol(
    accept_downloads: Optional[bool],
) -> Optional[Literal["accept", "deny"]]:
    if accept_downloads is None:
        return None
    return "accept" if accept_downloads else "deny"


async def to_client_certificates_protocol(
    certs: Optional[List[ClientCertificate]],
) -> Optional[List["channels.BrowserNewContextParamsClientCertificates"]]:
    if certs is None:
        return None

    async def bufferize_content(
        value: Optional[bytes], file_path: Optional[Union[str, Path]]
    ) -> Optional[str]:
        # Binary protocol values are base64 strings.
        if value is not None:
            return base64.b64encode(value).decode()
        if file_path:
            return base64.b64encode(await async_readfile(file_path)).decode()
        return None

    result: List["channels.BrowserNewContextParamsClientCertificates"] = []
    for cert in certs:
        # The protocol does not accept null fields in the objects of an array.
        item: "channels.BrowserNewContextParamsClientCertificates" = {
            "origin": cert["origin"]
        }
        cert_value = await bufferize_content(cert.get("cert"), cert.get("certPath"))
        if cert_value is not None:
            item["cert"] = cert_value
        key_value = await bufferize_content(cert.get("key"), cert.get("keyPath"))
        if key_value is not None:
            item["key"] = key_value
        pfx_value = await bufferize_content(cert.get("pfx"), cert.get("pfxPath"))
        if pfx_value is not None:
            item["pfx"] = pfx_value
        passphrase = cert.get("passphrase")
        if passphrase is not None:
            item["passphrase"] = passphrase
        result.append(item)
    return result
