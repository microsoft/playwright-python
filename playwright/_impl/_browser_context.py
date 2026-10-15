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
import json
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
    Union,
    cast,
)

from playwright._impl._api_structures import (
    Cookie,
    Geolocation,
    RecordVideoSize,
    SetCookieParam,
    StorageState,
    WebErrorLocation,
)
from playwright._impl._cdp_session import CDPSession
from playwright._impl._clock import Clock
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._credentials import Credentials
from playwright._impl._debugger import Debugger
from playwright._impl._dialog import Dialog
from playwright._impl._disposable import Disposable, DisposableStub
from playwright._impl._errors import Error, TargetClosedError, parse_error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._fetch import APIRequestContext
from playwright._impl._frame import Frame
from playwright._impl._har_router import HarRouter
from playwright._impl._headers import serialize_headers
from playwright._impl._helper import (
    HarContentPolicy,
    HarMode,
    RouteFromHarNotFoundPolicy,
    RouteHandler,
    RouteHandlerCallback,
    URLMatch,
    WebSocketRouteHandlerCallback,
    async_readfile,
    async_writefile,
    create_task_and_ignore_exception,
    to_impl,
)
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocketRoute,
    WebSocketRouteHandler,
)
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._timeout_settings import TimeoutSettings
from playwright._impl._tracing import Tracing
from playwright._impl._waiter import Waiter
from playwright._impl._web_error import WebError

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._browser import Browser
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
        # Browser is null for browser contexts created outside of normal browser, e.g. android or electron.
        # circular import workaround:
        self._browser: Optional["Browser"] = None
        if parent.__class__.__name__ == "Browser":
            self._browser = cast("Browser", parent)
        self._pages: List[Page] = []
        self._routes: List[RouteHandler] = []
        self._web_socket_routes: List[WebSocketRouteHandler] = []
        self._bindings: Dict[str, Any] = {}
        self._timeout_settings = TimeoutSettings(None)
        self._owner_page: Optional[Page] = None
        self._options: Dict[str, Any] = initializer["options"]
        self._service_workers: Set[Worker] = set()
        self._base_url: Optional[str] = self._options.get("baseURL")
        self._videos_dir: Optional[str] = self._options.get("recordVideo")
        self._tracing = cast(Tracing, from_channel(initializer["tracing"]))
        self._debugger: Debugger = cast(Debugger, from_channel(initializer["debugger"]))
        self._request: APIRequestContext = from_channel(initializer["requestContext"])
        self._request._timeout_settings = self._timeout_settings
        self._clock = Clock(self)
        self._credentials = Credentials(self)
        self._channel.onBindingCall(
            lambda event: self._on_binding(from_channel(event["binding"]))
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

        self._channel.onDialog(
            lambda event: self._on_dialog(from_channel(event["dialog"]))
        )
        self._channel.onDialogClosed(
            lambda event: self._on_dialog_closed(from_channel(event["dialog"]))
        )
        self._channel.onPageError(
            lambda event: self._on_page_error(
                parse_error(event["error"]["error"]),
                from_nullable_channel(event["page"]),
                event["location"],
            ),
        )
        self._channel.onRequest(
            lambda event: self._on_request(
                from_channel(event["request"]),
                from_nullable_channel(event["page"]),
            ),
        )
        self._channel.onResponse(
            lambda event: self._on_response(
                from_channel(event["response"]),
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
        self._closed_future: asyncio.Future = asyncio.Future()
        self.once(
            self.Events.Close, lambda context: self._closed_future.set_result(True)
        )
        self._close_reason: Optional[str] = None
        self._har_routers: List[HarRouter] = []
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
        self._closing_or_closed = False

    def __repr__(self) -> str:
        return f"<BrowserContext browser={self.browser}>"

    def _on_page(self, page: Page) -> None:
        self._pages.append(page)
        self.emit(BrowserContext.Events.Page, page)
        if page._opener and not page._opener.is_closed():
            page._opener.emit(Page.Events.Popup, page)

    async def _on_route(self, route: Route) -> None:
        route._context = self
        page = route.request._safe_page()
        route_handlers = self._routes.copy()
        for route_handler in route_handlers:
            # If the page or the context was closed we stall all requests right away.
            if (page and page._close_was_called) or self._closing_or_closed:
                return
            if not route_handler.matches(route.request.url):
                continue
            if route_handler not in self._routes:
                continue
            if route_handler.will_expire:
                self._routes.remove(route_handler)
            try:
                handled = await route_handler.handle(route)
            finally:
                if len(self._routes) == 0:
                    create_task_and_ignore_exception(
                        self._loop,
                        self._connection.wrap_api_call(
                            lambda: self._update_interception_patterns(), True
                        ),
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

    def _on_binding(self, binding_call: BindingCall) -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func is None:
            return
        asyncio.create_task(binding_call.call(func))

    def set_default_navigation_timeout(self, timeout: float) -> None:
        return self._set_default_navigation_timeout_impl(timeout)

    def _set_default_navigation_timeout_impl(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)

    def set_default_timeout(self, timeout: float) -> None:
        return self._set_default_timeout_impl(timeout)

    def _set_default_timeout_impl(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_timeout(timeout)

    @property
    def pages(self) -> List[Page]:
        return self._pages.copy()

    @property
    def browser(self) -> Optional["Browser"]:
        return self._browser

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

    async def new_page(self) -> Page:
        if self._owner_page:
            raise Error("Please use browser.new_context()")
        return from_channel((await self._channel.newPage())["page"])

    async def cookies(self, urls: Optional[Union[str, Sequence[str]]]) -> List[Cookie]:
        if urls is None:
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
        await self._channel.clearCookies(
            name=name if isinstance(name, str) else None,
            nameRegexSource=name.pattern if isinstance(name, Pattern) else None,
            nameRegexFlags=(
                escape_regex_flags(name) if isinstance(name, Pattern) else None
            ),
            domain=domain if isinstance(domain, str) else None,
            domainRegexSource=domain.pattern if isinstance(domain, Pattern) else None,
            domainRegexFlags=(
                escape_regex_flags(domain) if isinstance(domain, Pattern) else None
            ),
            path=path if isinstance(path, str) else None,
            pathRegexSource=path.pattern if isinstance(path, Pattern) else None,
            pathRegexFlags=(
                escape_regex_flags(path) if isinstance(path, Pattern) else None
            ),
        )

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
        await self._channel.setExtraHTTPHeaders(headers=serialize_headers(headers))

    async def set_offline(self, offline: bool) -> None:
        await self._channel.setOffline(offline=offline)

    async def add_init_script(
        self, script: Optional[str], path: Optional[Union[str, Path]]
    ) -> Disposable:
        if path:
            script = (await async_readfile(path)).decode()
        if not isinstance(script, str):
            raise Error("Either path or script parameter must be specified")
        result = await self._channel.addInitScript(source=script)
        return from_channel(result["disposable"])

    async def expose_binding(self, name: str, callback: Callable) -> Disposable:
        for page in self._pages:
            if name in page._bindings:
                raise Error(
                    f'Function "{name}" has been already registered in one of the pages'
                )
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        self._bindings[name] = callback
        result = await self._channel.exposeBinding(name=name, noGlobal=None)
        return from_channel(result["disposable"])

    async def expose_function(self, name: str, callback: Callable) -> Disposable:
        return await self.expose_binding(
            name=name, callback=lambda source, *args: callback(*args)
        )

    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: Optional[int]
    ) -> DisposableStub:
        self._routes.insert(
            0,
            RouteHandler(
                self._base_url,
                url,
                handler,
                True if self._dispatcher_fiber else False,
                times,
            ),
        )
        await self._update_interception_patterns()
        return DisposableStub(lambda: self.unroute(url=url, handler=handler), self)

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback]
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            if route.url != url or (handler and route.handler != handler):
                remaining.append(route)
            else:
                removed.append(route)
        await self._unroute_internal(removed, remaining, "default")

    async def _unroute_internal(
        self,
        removed: List[RouteHandler],
        remaining: List[RouteHandler],
        behavior: Literal["default", "ignoreErrors", "wait"] = None,
    ) -> None:
        self._routes = remaining
        if behavior is not None and behavior != "default":
            await asyncio.gather(*map(lambda router: router.stop(behavior), removed))  # type: ignore
        await self._update_interception_patterns()

    async def route_web_socket(
        self, url: URLMatch, handler: WebSocketRouteHandlerCallback
    ) -> None:
        self._web_socket_routes.insert(
            0,
            WebSocketRouteHandler(self._base_url, url, handler),
        )
        await self._update_web_socket_interception_patterns()

    def _dispose_har_routers(self) -> None:
        for router in self._har_routers:
            router.dispose()
        self._har_routers = []

    async def unroute_all(
        self, behavior: Optional[Literal["default", "ignoreErrors", "wait"]]
    ) -> None:
        await self._unroute_internal(self._routes, [], behavior)
        self._dispose_har_routers()

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Optional[Union[Pattern[str], str]],
        not_found: Optional[RouteFromHarNotFoundPolicy],
        update: Optional[bool],
        update_content: Optional[Literal["attach", "embed"]],
        update_mode: Optional[HarMode],
    ) -> None:
        if update:
            await self._tracing._record_into_har(
                har=har,
                page=None,
                url=url,
                update_content=update_content,
                update_mode=update_mode,
            )
            return
        router = await HarRouter.create(
            local_utils=self._connection.local_utils,
            file=str(har),
            not_found_action=not_found or "abort",
            url_matcher=url,
        )
        self._har_routers.append(router)
        await router.add_context_route(self)

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

    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        waiter = Waiter(self, f"browser_context.expect_event({event})")
        waiter.reject_on_timeout(
            timeout, f'Timeout {timeout}ms exceeded while waiting for event "{event}"'
        )
        if event != BrowserContext.Events.Close:
            waiter.reject_on_event(
                self, BrowserContext.Events.Close, lambda: TargetClosedError()
            )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    def _on_close(self) -> None:
        self._closing_or_closed = True
        if self._browser:
            if self in self._browser._contexts:
                self._browser._contexts.remove(self)
            assert self._browser._browser_type is not None
            if (
                self
                in self._browser._browser_type._playwright.selectors._contexts_for_selectors
            ):
                self._browser._browser_type._playwright.selectors._contexts_for_selectors.remove(
                    self
                )

        self._dispose_har_routers()
        self._tracing._reset_stack_counter()
        self._request._tracing._reset_stack_counter()
        self.emit(BrowserContext.Events.Close, self)

    def is_closed(self) -> bool:
        return self._closing_or_closed

    async def close(self, reason: Optional[str]) -> None:
        if self._closing_or_closed:
            return
        self._close_reason = reason
        self._closing_or_closed = True

        await self.request.dispose(reason=reason)

        async def _inner_close() -> None:
            await self._tracing._export_all_hars()

        await self._channel._connection.wrap_api_call(_inner_close, True)
        await self._channel.close(reason=reason)
        await self._closed_future

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
            await async_writefile(path, json.dumps(state))
        return cast(StorageState, state)

    async def set_storage_state(
        self, storage_state: Union[StorageState, str, Path]
    ) -> None:
        await self._channel.setStorageState(
            storageState=await to_storage_state_params(storage_state)
        )

    def _effective_close_reason(self) -> Optional[str]:
        if self._close_reason:
            return self._close_reason
        if self._browser:
            return self._browser._close_reason
        return None

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
            event=Page.Events.Console, predicate=predicate, timeout=timeout
        )

    def expect_page(
        self,
        predicate: Optional[Callable[[Page], bool]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Page]:
        return self.expect_event(
            event=BrowserContext.Events.Page, predicate=predicate, timeout=timeout
        )

    def _on_service_worker(self, worker: Worker) -> None:
        worker._context = self
        self._service_workers.add(worker)
        self.emit(BrowserContext.Events.ServiceWorker, worker)

    def _on_request_failed(
        self,
        request: Request,
        response_end_timing: float,
        failure_text: Optional[str],
        page: Optional[Page],
    ) -> None:
        request._failure_text = failure_text
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

    def _on_console_message(self, event: "channels.BrowserContextConsoleEvent") -> None:
        message = ConsoleMessage(event, self._loop, self._dispatcher_fiber)
        worker = message.worker
        if worker:
            worker.emit(Worker.Events.Console, message)
        page = message.page
        if page:
            page.emit(Page.Events.Console, message)
        self.emit(BrowserContext.Events.Console, message)

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
                    self._loop, dialog.accept(prompt_text=None)
                )
            else:
                create_task_and_ignore_exception(self._loop, dialog.dismiss())

    def _on_dialog_closed(self, dialog: Dialog) -> None:
        self.emit(BrowserContext.Events.DialogClosed, dialog)
        page = dialog.page
        if page:
            page.emit(Page.Events.DialogClosed, dialog)

    def _on_page_error(
        self, error: Error, page: Optional[Page], location: WebErrorLocation
    ) -> None:
        self.emit(
            BrowserContext.Events.WebError,
            WebError(self._loop, self._dispatcher_fiber, page, error, location),
        )
        if page:
            page.emit(Page.Events.PageError, error)

    def _on_request(self, request: Request, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Request, request)
        if page:
            page.emit(Page.Events.Request, request)

    def _on_response(self, response: Response, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Response, response)
        if page:
            page.emit(Page.Events.Response, response)

    @property
    def background_pages(self) -> List[Page]:
        return []

    @property
    def service_workers(self) -> List[Worker]:
        return list(self._service_workers)

    async def new_cdp_session(self, page: Union[Page, Frame]) -> CDPSession:
        page = to_impl(page)
        if isinstance(page, Page):
            result = await self._channel.newCDPSession(page=page._channel, frame=None)
        elif isinstance(page, Frame):
            result = await self._channel.newCDPSession(page=None, frame=page._channel)
        else:
            raise Error("page: expected Page or Frame")
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


def to_record_video_params(
    record_video_dir: Optional[Union[str, Path]],
    record_video_size: Optional[RecordVideoSize],
    record_video_fps: Optional[int],
) -> "Optional[channels.BrowserNewContextParamsRecordVideo]":
    if record_video_dir is None:
        return None
    return {
        "dir": str(Path(record_video_dir).absolute()),
        "size": record_video_size,
        "fps": record_video_fps,
    }


def to_accept_downloads_params(
    accept_downloads: Optional[bool],
) -> Optional[Literal["accept", "deny"]]:
    if accept_downloads is None:
        return None
    return "accept" if accept_downloads else "deny"


async def to_storage_state_params(
    storage_state: Optional[Union[StorageState, str, Path]],
) -> "Optional[channels.BrowserNewContextParamsStorageState]":
    if storage_state is None:
        return None
    if isinstance(storage_state, dict):
        return cast("channels.BrowserNewContextParamsStorageState", storage_state)
    return json.loads((await async_readfile(storage_state)).decode())
