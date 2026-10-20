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

"""Port of packages/playwright-core/src/client/browserContext.ts.

Python differences:

- The API methods take the parameters of the Python API. Where upstream passes the
  options object on, the port passes a dict of the options with their Python names,
  without the options that are None (undefined): see to_options().
  prepare_browser_context_params() returns the parameters of the protocol, by their
  protocol names; the spread of the options is the list of the context options of
  the protocol.
- The Python API writes `viewport: null` as no_viewport=True, and null as "null" in
  color_scheme, reduced_motion, forced_colors and contrast. The record_video_*
  options are recordVideo, and the record_har_* options are recordHar.
- A JS Set keeps the order of insertion: a set of objects is a dict with None values.
- A binary value of the protocol is a base64 string.
- Not ported, JavaScript only: setHTTPCredentials(), the arg and exposeFunctions
  options of addInitScript(), and [Symbol.asyncDispose]().
"""

import asyncio
import base64
import json
import os
from pathlib import Path
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
)
from playwright._impl_v2 import network
from playwright._impl_v2.cdp_session import CDPSession
from playwright._impl_v2.channel_owner import (
    ChannelOwner,
    api_call,
    from_channel,
    internal,
)
from playwright._impl_v2.client_helper import evaluation_script
from playwright._impl_v2.clock import Clock
from playwright._impl_v2.console_message import ConsoleMessage
from playwright._impl_v2.credentials import Credentials
from playwright._impl_v2.debugger import Debugger
from playwright._impl_v2.dialog import Dialog
from playwright._impl_v2.disposable import DisposableObject, DisposableStub
from playwright._impl_v2.errors import Error, TargetClosedError, parse_error
from playwright._impl_v2.event_context_manager import EventContextManagerImpl
from playwright._impl_v2.events import Events
from playwright._impl_v2.fetch import APIRequestContext
from playwright._impl_v2.file_utils import mkdir_if_needed
from playwright._impl_v2.frame import Frame
from playwright._impl_v2.har_router import HarRouter
from playwright._impl_v2.isomorphic.headers import headers_object_to_array
from playwright._impl_v2.isomorphic.string_utils import js_string
from playwright._impl_v2.isomorphic.url_match import URLMatch, url_matches_equal
from playwright._impl_v2.page import BindingCall, Page
from playwright._impl_v2.timeout_settings import NO_TIMEOUT, TimeoutSettings
from playwright._impl_v2.tracing import Tracing
from playwright._impl_v2.utils.promise import all_, catch, start_eager
from playwright._impl_v2.utils.whatwg_url import parse_url
from playwright._impl_v2.waiter import Waiter
from playwright._impl_v2.web_error import WebError
from playwright._impl_v2.worker import Worker

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.browser import Browser
    from playwright._impl_v2.protocol_channels import BrowserContextChannel

# Python: an object with the optional methods actionAdded(page, action, code),
# actionUpdated(page, action, code) and signalAdded(page, signal, code), in
# snake_case.
RecorderEventSink = Any


class BrowserContext(ChannelOwner):
    _channel: "BrowserContextChannel"

    @staticmethod
    def from_(context: "BrowserContextChannel") -> "BrowserContext":
        return from_channel(context)

    @staticmethod
    def from_nullable(
        context: Optional["BrowserContextChannel"],
    ) -> Optional["BrowserContext"]:
        return BrowserContext.from_(context) if context else None

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.BrowserContextInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Python: the fields, in the order of their declarations.
        self._pages: Dict[Page, None] = {}
        self._routes: List[network.RouteHandler] = []
        self._web_socket_routes: List[network.WebSocketRouteHandler] = []
        # Browser is null for browser contexts created outside of normal browser, e.g. android or electron.
        self._browser: Optional["Browser"] = None
        self._bindings: Dict[str, Callable[..., Any]] = {}
        self._timeout_settings: TimeoutSettings
        self._owner_page: Optional[Page] = None
        self._for_reuse = False
        self._closed_promise: "asyncio.Future[None]"
        self._options: Dict[str, Any]

        self.debugger: Debugger
        self.request: APIRequestContext
        self.tracing: Tracing
        self.clock: Clock
        self.credentials: Credentials

        self._service_workers: Dict[Worker, None] = {}
        self._closing_status: Literal["none", "closing", "closed"] = "none"
        self._close_reason: Optional[str] = None
        self._har_routers: List[HarRouter] = []
        self._on_recorder_event_sink: Optional[RecorderEventSink] = None

        self._options = cast(Dict[str, Any], initializer["options"])
        self._timeout_settings = TimeoutSettings()
        self.debugger = Debugger.from_(initializer["debugger"])
        self.tracing = Tracing.from_(initializer["tracing"])
        self.request = APIRequestContext.from_(initializer["requestContext"])
        self.request._timeout_settings = self._timeout_settings
        self.clock = Clock(self)
        self.credentials = Credentials(self)

        # Python: an arrow function with statements is a local function.
        self._channel.onBindingCall(
            lambda event: self._on_binding(BindingCall.from_(event["binding"]))
        )
        self._channel.onClose(lambda: self._on_close())
        self._channel.onPage(lambda event: self._on_page(Page.from_(event["page"])))
        self._channel.onRoute(
            lambda event: self._on_route(network.Route.from_(event["route"]))
        )
        self._channel.onWebSocketRoute(
            lambda event: self._on_web_socket_route(
                network.WebSocketRoute.from_(event["webSocketRoute"])
            )
        )

        def on_service_worker(
            event: "channels.BrowserContextServiceWorkerEvent",
        ) -> None:
            service_worker = Worker.from_(event["worker"])
            service_worker._context = self
            self._service_workers[service_worker] = None
            self.emit(Events.BrowserContext.ServiceWorker, service_worker)

        self._channel.onServiceWorker(on_service_worker)

        def on_console(event: "channels.BrowserContextConsoleEvent") -> None:
            worker = Worker.from_nullable(event["worker"])
            page = Page.from_nullable(event["page"])
            console_message = ConsoleMessage(event, page, worker)
            if worker:
                worker.emit(Events.Worker.Console, console_message)
            if page:
                page.emit(Events.Page.Console, console_message)
            if worker and worker in self._service_workers:
                scope = self._service_worker_scope(worker)
                # Python: a for loop has no scope of its own, so the page of the loop
                # is scope_page.
                for scope_page in list(self._pages):
                    if scope and scope_page.url.startswith(scope):
                        scope_page.emit(Events.Page.Console, console_message)
            self.emit(Events.BrowserContext.Console, console_message)

        self._channel.onConsole(on_console)

        def on_page_error(event: "channels.BrowserContextPageErrorEvent") -> None:
            page_object = Page.from_(event["page"])
            parsed_error = parse_error(event["error"])
            self.emit(
                Events.BrowserContext.WebError,
                WebError(page_object, parsed_error, event["location"]),
            )
            if page_object:
                page_object.emit(Events.Page.PageError, parsed_error)

        self._channel.onPageError(on_page_error)

        def on_dialog(event: "channels.BrowserContextDialogEvent") -> None:
            dialog = event["dialog"]
            dialog_object = Dialog.from_(dialog)
            has_listeners = self.emit(Events.BrowserContext.Dialog, dialog_object)
            page = dialog_object.page
            if page:
                has_listeners = (
                    page.emit(Events.Page.Dialog, dialog_object) or has_listeners
                )
            if not has_listeners:
                # Although we do similar handling on the server side, we still need this logic
                # on the client side due to a possible race condition between two async calls:
                # a) removing "dialog" listener subscription (client->server)
                # b) actual "dialog" event (server->client)
                if dialog_object.type == "beforeunload":
                    catch(dialog.accept(promptText=None, timeout=NO_TIMEOUT))
                else:
                    catch(dialog.dismiss(timeout=NO_TIMEOUT))

        self._channel.onDialog(on_dialog)

        def on_dialog_closed(event: "channels.BrowserContextDialogClosedEvent") -> None:
            dialog_object = Dialog.from_(event["dialog"])
            self.emit(Events.BrowserContext.DialogClosed, dialog_object)
            page = dialog_object.page
            if page:
                page.emit(Events.Page.DialogClosed, dialog_object)

        self._channel.onDialogClosed(on_dialog_closed)
        self._channel.onRequest(
            lambda event: self._on_request(
                network.Request.from_(event["request"]),
                Page.from_nullable(event["page"]),
            )
        )
        self._channel.onRequestFailed(
            lambda event: self._on_request_failed(
                network.Request.from_(event["request"]),
                event["responseEndTiming"],
                event["failureText"],
                Page.from_nullable(event["page"]),
            )
        )
        self._channel.onRequestFinished(
            lambda params: self._on_request_finished(params)
        )
        self._channel.onResponse(
            lambda event: self._on_response(
                network.Response.from_(event["response"]),
                Page.from_nullable(event["page"]),
            )
        )

        def on_recorder_event(
            event: "channels.BrowserContextRecorderEventEvent",
        ) -> None:
            # Python: `sink?.method?.(...)`: the sink and its methods are optional.
            sink = self._on_recorder_event_sink
            if event["event"] == "actionAdded":
                action_added = getattr(sink, "action_added", None)
                if action_added:
                    action_added(
                        Page.from_(event["page"]), event["data"], event["code"]
                    )
            elif event["event"] == "actionUpdated":
                action_updated = getattr(sink, "action_updated", None)
                if action_updated:
                    action_updated(
                        Page.from_(event["page"]), event["data"], event["code"]
                    )
            elif event["event"] == "signalAdded":
                signal_added = getattr(sink, "signal_added", None)
                if signal_added:
                    signal_added(
                        Page.from_(event["page"]), event["data"], event["code"]
                    )

        self._channel.onRecorderEvent(on_recorder_event)
        self._closed_promise = self._loop.create_future()
        self.once(
            Events.BrowserContext.Close,
            lambda context: self._closed_promise.set_result(None),
        )

        self._set_event_to_subscription_mapping(
            {
                Events.BrowserContext.Console: "console",
                Events.BrowserContext.Dialog: "dialog",
                Events.BrowserContext.DialogClosed: "dialogClosed",
                Events.BrowserContext.Request: "request",
                Events.BrowserContext.Response: "response",
                Events.BrowserContext.RequestFinished: "requestFinished",
                Events.BrowserContext.RequestFailed: "requestFailed",
            }
        )

    async def _initialize_har_from_options(
        self,
        record_har_path: Optional[Union[str, Path]],
        record_har_omit_content: Optional[bool],
        record_har_content: Optional[Literal["omit", "embed", "attach"]],
        record_har_mode: Optional[Literal["full", "minimal"]],
        record_har_url_filter: Optional[Union[str, Pattern[str]]],
    ) -> None:
        # Python: recordHar is the record_har_* options; recordHar.path is
        # record_har_path.
        if not record_har_path:
            return
        default_content: Literal["attach", "embed"] = (
            "attach" if str(record_har_path).endswith(".zip") else "embed"
        )
        await self.tracing._record_into_har(
            har=record_har_path,
            page=None,
            url=record_har_url_filter,
            update_content=(
                record_har_content
                if record_har_content is not None
                else ("omit" if record_har_omit_content else default_content)
            ),
            update_mode=record_har_mode if record_har_mode is not None else "full",
        )

    def _on_page(self, page: Page) -> None:
        self._pages[page] = None
        self.emit(Events.BrowserContext.Page, page)
        if page._opener and not page._opener.is_closed():
            page._opener.emit(Events.Page.Popup, page)

    def _on_request(self, request: network.Request, page: Optional[Page]) -> None:
        self.emit(Events.BrowserContext.Request, request)
        if page:
            page.emit(Events.Page.Request, request)

    def _on_response(self, response: network.Response, page: Optional[Page]) -> None:
        self.emit(Events.BrowserContext.Response, response)
        if page:
            page.emit(Events.Page.Response, response)

    def _on_request_failed(
        self,
        request: network.Request,
        response_end_timing: float,
        failure_text: Optional[str],
        page: Optional[Page],
    ) -> None:
        request._failure_text = failure_text or None
        request._set_response_end_timing(response_end_timing)
        self.emit(Events.BrowserContext.RequestFailed, request)
        if page:
            page.emit(Events.Page.RequestFailed, request)

    def _on_request_finished(
        self, params: "channels.BrowserContextRequestFinishedEvent"
    ) -> None:
        response_end_timing = params["responseEndTiming"]
        request = network.Request.from_(params["request"])
        response = network.Response.from_nullable(params["response"])
        page = Page.from_nullable(params["page"])
        request._set_response_end_timing(response_end_timing)
        self.emit(Events.BrowserContext.RequestFinished, request)
        if page:
            page.emit(Events.Page.RequestFinished, request)
        if response:
            response._finished_promise.resolve(None)

    async def _on_route(self, route: network.Route) -> None:
        route._context = self
        page = route.request._safe_page()
        route_handlers = self._routes[:]
        for route_handler in route_handlers:
            # If the page or the context was closed we stall all requests right away.
            if (page and page._close_was_called) or self.is_closed():
                return
            if not route_handler.matches(route.request.url):
                continue
            index = (
                self._routes.index(route_handler)
                if route_handler in self._routes
                else -1
            )
            if index == -1:
                continue
            if route_handler.will_expire():
                del self._routes[index]
            handled = await route_handler.handle(route)
            if not self._routes:
                catch(self._disable_interception())
            if handled:
                return
        # If the page is closed or unrouteAll() was called without waiting and interception disabled,
        # the method will throw an error - silence it.
        await catch(route._inner_continue(is_fallback=True))

    async def _on_web_socket_route(
        self, web_socket_route: network.WebSocketRoute
    ) -> None:
        route_handler = next(
            (
                route
                for route in self._web_socket_routes
                if route.matches(web_socket_route.url)
            ),
            None,
        )
        if route_handler:
            await route_handler.handle(web_socket_route)
        else:
            web_socket_route.connect_to_server()

    async def _on_binding(self, binding_call: BindingCall) -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if not func:
            return
        await binding_call.call(func)

    def _service_worker_scope(self, service_worker: Worker) -> Optional[str]:
        # Python: parse_url() returns None where new URL() throws.
        parsed = parse_url(".", service_worker.url)
        if parsed is None:
            return None
        url = parsed.href
        if not url.endswith("/"):
            url += "/"
        return url

    def set_default_navigation_timeout(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._timeout_settings.set_default_timeout(timeout)

    @property
    def browser(self) -> Optional["Browser"]:
        return self._browser

    @property
    def pages(self) -> List[Page]:
        return list(self._pages)

    def is_closed(self) -> bool:
        return self._closing_status != "none"

    async def new_page(self) -> Page:
        if self._owner_page:
            # Python: the message names the Python method.
            raise Error("Please use browser.new_context()")
        return Page.from_((await self._channel.newPage(timeout=NO_TIMEOUT))["page"])

    async def cookies(self, urls: Optional[Union[str, Sequence[str]]]) -> List[Cookie]:
        if not urls:
            urls = []
        if urls and isinstance(urls, str):
            urls = [urls]
        return cast(
            List[Cookie],
            (await self._channel.cookies(urls=urls, timeout=NO_TIMEOUT))["cookies"],
        )

    async def add_cookies(self, cookies: Sequence[SetCookieParam]) -> None:
        await self._channel.addCookies(
            cookies=cast("Sequence[channels.SetNetworkCookie]", cookies),
            timeout=NO_TIMEOUT,
        )

    async def clear_cookies(
        self,
        name: Optional[Union[str, Pattern[str]]],
        domain: Optional[Union[str, Pattern[str]]],
        path: Optional[Union[str, Pattern[str]]],
    ) -> None:
        await self._channel.clearCookies(
            **network.to_clear_cookies_params(name=name, domain=domain, path=path),
            timeout=NO_TIMEOUT,
        )

    async def grant_permissions(
        self, permissions: Sequence[str], origin: Optional[str]
    ) -> None:
        await self._channel.grantPermissions(
            permissions=permissions, origin=origin, timeout=NO_TIMEOUT
        )

    async def clear_permissions(self) -> None:
        await self._channel.clearPermissions(timeout=NO_TIMEOUT)

    async def set_geolocation(self, geolocation: Optional[Geolocation]) -> None:
        # Python: None is both null and undefined.
        await self._channel.setGeolocation(
            geolocation=cast(
                "Optional[channels.BrowserContextSetGeolocationParamsGeolocation]",
                geolocation,
            ),
            timeout=NO_TIMEOUT,
        )

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        network.validate_headers(headers)
        await self._channel.setExtraHTTPHeaders(
            headers=headers_object_to_array(headers), timeout=NO_TIMEOUT
        )

    async def set_offline(self, offline: bool) -> None:
        await self._channel.setOffline(offline=offline, timeout=NO_TIMEOUT)

    # Not ported: setHTTPCredentials() (JavaScript only).

    async def add_init_script(
        self, script: Optional[str], path: Optional[Union[str, Path]]
    ) -> DisposableObject:
        # Not ported: assertEvaluateOptions() and the exposeFunctions option, with
        # addInitScriptWithExposedFunctions() (JavaScript only); a script is never a
        # function, so there is no arg.
        # Python: the script and path parameters are the string and the { path }
        # forms of the script.
        source = await evaluation_script(
            script if script is not None else {"path": path}
        )
        return DisposableObject.from_(
            (await self._channel.addInitScript(source=source, timeout=NO_TIMEOUT))[
                "disposable"
            ]
        )

    async def expose_binding(
        self, name: str, callback: Callable[..., Any]
    ) -> DisposableObject:
        result = await self._channel.exposeBinding(
            name=name, noGlobal=None, timeout=NO_TIMEOUT
        )
        self._bindings[name] = callback
        return DisposableObject.from_(result["disposable"])

    async def _expose_callback_binding(
        self, name: str, callback: Callable[..., Any]
    ) -> DisposableObject:
        self._bindings[name] = lambda source, *args: callback(*args)
        result = await self._channel.exposeBinding(
            name=name, noGlobal=True, timeout=NO_TIMEOUT
        )
        return DisposableObject.from_(result["disposable"])

    async def expose_function(
        self, name: str, callback: Callable[..., Any]
    ) -> DisposableObject:
        result = await self._channel.exposeBinding(
            name=name, noGlobal=None, timeout=NO_TIMEOUT
        )

        def binding(source: Any, *args: Any) -> Any:
            return callback(*args)

        self._bindings[name] = binding
        return DisposableObject.from_(result["disposable"])

    @api_call(title="Route requests")
    async def route(
        self,
        url: URLMatch,
        handler: network.RouteHandlerCallback,
        times: Optional[int],
    ) -> DisposableStub:
        self._routes.insert(
            0,
            network.RouteHandler(
                base_url=self._options.get("baseURL"),
                url=url,
                handler=handler,
                times=times,
            ),
        )
        await self._update_interception_patterns()
        return DisposableStub(lambda: self.unroute(url=url, handler=handler))

    @api_call(title="Route WebSockets")
    async def route_web_socket(
        self, url: URLMatch, handler: network.WebSocketRouteHandlerCallback
    ) -> None:
        self._web_socket_routes.insert(
            0,
            network.WebSocketRouteHandler(
                base_url=self._options.get("baseURL"), url=url, handler=handler
            ),
        )
        await self._update_web_socket_interception_patterns()

    async def route_from_har(
        self,
        har: Union[str, Path],
        url: Optional[Union[str, Pattern[str]]],
        not_found: Optional[Literal["abort", "fallback"]],
        update: Optional[bool],
        update_content: Optional[Literal["attach", "embed"]],
        update_mode: Optional[Literal["minimal", "full"]],
    ) -> None:
        local_utils = self._connection.local_utils()
        if not local_utils:
            raise Error("Route from har is not supported in thin clients")
        if update:
            # Python: _record_into_har() takes the url, update_content and update_mode
            # options of the options object.
            await self.tracing._record_into_har(
                har=har,
                page=None,
                url=url,
                update_content=update_content,
                update_mode=update_mode,
            )
            return
        # Python: the path can be a pathlib.Path.
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
        self, behavior: Optional[Literal["wait", "ignoreErrors", "default"]]
    ) -> None:
        await self._unroute_internal(self._routes, [], behavior)
        self._dispose_har_routers()

    @api_call(title="Unroute requests")
    async def unroute(
        self, url: URLMatch, handler: Optional[network.RouteHandlerCallback]
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            # Python: handlers compare with ==, as listeners do: a bound method is a
            # new object each time that it is looked up.
            if url_matches_equal(route.url, url) and (
                not handler or route.handler == handler
            ):
                removed.append(route)
            else:
                remaining.append(route)
        await self._unroute_internal(removed, remaining, "default")

    async def _unroute_internal(
        self,
        removed: List[network.RouteHandler],
        remaining: List[network.RouteHandler],
        behavior: Optional[Literal["wait", "ignoreErrors", "default"]],
    ) -> None:
        self._routes = remaining
        if behavior and behavior != "default":
            promises = [route_handler.stop(behavior) for route_handler in removed]
            await all_(promises)
        await self._update_interception_patterns()

    @internal
    async def _disable_interception(self) -> None:
        await self._update_interception_patterns()

    async def _update_interception_patterns(self) -> None:
        patterns = network.RouteHandler.prepare_interception_patterns(self._routes)
        await self._channel.setNetworkInterceptionPatterns(
            patterns=patterns, timeout=NO_TIMEOUT
        )

    async def _update_web_socket_interception_patterns(self) -> None:
        patterns = network.WebSocketRouteHandler.prepare_interception_patterns(
            self._web_socket_routes
        )
        await self._channel.setWebSocketInterceptionPatterns(
            patterns=patterns, timeout=NO_TIMEOUT
        )

    def _effective_close_reason(self) -> Optional[str]:
        return self._close_reason or (
            self._browser._close_reason if self._browser else None
        )

    @api_call()
    async def wait_for_event(
        self,
        event: str,
        predicate: Optional[Callable[..., Any]],
        timeout: Optional[float],
    ) -> Any:
        # Python: optionsOrPredicate is the predicate and timeout parameters, and
        # timeout() returns the timeout itself.
        timeout_options = self._timeout_settings.timeout(timeout)
        waiter = Waiter.create_for_event(self, event)
        waiter.reject_on_timeout(
            timeout_options,
            f'Timeout {js_string(timeout_options)}ms exceeded while waiting for event "{event}"',
        )
        if event != Events.BrowserContext.Close:
            waiter.reject_on_event(
                self,
                Events.BrowserContext.Close,
                lambda: TargetClosedError(self._effective_close_reason()),
            )
        result = await waiter.wait_for_event(self, event, predicate)
        waiter.dispose()
        return result

    async def storage_state(
        self,
        path: Optional[Union[str, Path]],
        indexed_db: Optional[bool],
        opfs: Optional[bool],
        credentials: Optional[bool],
    ) -> StorageState:
        result = await self._channel.storageState(
            indexedDB=indexed_db,
            opfs=opfs,
            credentials=credentials,
            timeout=NO_TIMEOUT,
        )
        # Python: a field that the driver left out is None in the result. Upstream it
        # is undefined, and JSON.stringify() leaves it out.
        state = {key: value for key, value in result.items() if value is not None}
        if path:
            await mkdir_if_needed(path)
            # Python: JSON.stringify(state, undefined, 2), written as UTF-8.
            await write_file(
                path, json.dumps(state, indent=2, ensure_ascii=False).encode("utf-8")
            )
        return cast(StorageState, state)

    async def set_storage_state(
        self, storage_state: Union[str, Path, StorageState]
    ) -> None:
        state = await prepare_storage_state(storage_state)
        await self._channel.setStorageState(storageState=state, timeout=NO_TIMEOUT)

    @property
    def background_pages(self) -> List[Page]:
        return []

    @property
    def service_workers(self) -> List[Worker]:
        return list(self._service_workers)

    async def new_cdp_session(self, page: Union[Page, Frame]) -> CDPSession:
        # channelOwner.ts's validation messages don't handle the pseudo-union type, so we're explicit here
        if not isinstance(page, Page) and not isinstance(page, Frame):
            raise Error("page: expected Page or Frame")
        result = await self._channel.newCDPSession(
            page=page._channel if isinstance(page, Page) else None,
            frame=None if isinstance(page, Page) else page._channel,
            timeout=NO_TIMEOUT,
        )
        return CDPSession.from_(result["session"])

    def _on_close(self) -> None:
        self._closing_status = "closed"
        if self._browser:
            self._browser._contexts.pop(self, None)
            self._browser._browser_type._contexts.pop(self, None)
            self._browser._browser_type._playwright.selectors._contexts_for_selectors.discard(
                self
            )
        self._dispose_har_routers()
        self.tracing._reset_stack_counter()
        self.request.tracing._reset_stack_counter()
        self.emit(Events.BrowserContext.Close, self)

    # Not ported: [Symbol.asyncDispose](). Python: the generated API is an async
    # context manager that calls close().

    async def close(self, reason: Optional[str]) -> None:
        if self.is_closed():
            return
        self._close_reason = reason
        self._closing_status = "closing"
        await self.request.dispose(reason=reason)
        await self._instrumentation.run_before_close_browser_context(self)
        har_error = await catch(self.tracing._export_all_hars(), lambda e: e)
        await self._channel.close(reason=reason, timeout=NO_TIMEOUT)
        await self._closed_promise
        if har_error:
            raise har_error

    async def _show_recorder(self, params: Dict[str, Any]) -> None:
        await self._channel.showRecorder(
            language=params.get("language"),
            mode=params.get("mode"),
            pauseOnNextStatement=params.get("pauseOnNextStatement"),
            testIdAttributeName=params.get("testIdAttributeName"),
            launchOptions=params.get("launchOptions"),
            contextOptions=params.get("contextOptions"),
            device=params.get("device"),
            saveStorage=params.get("saveStorage"),
            outputFile=params.get("outputFile"),
            handleSIGINT=params.get("handleSIGINT"),
            omitCallTracking=params.get("omitCallTracking"),
            timeout=NO_TIMEOUT,
        )

    async def _start_recording(
        self, params: Dict[str, Any], event_sink: RecorderEventSink
    ) -> None:
        self._on_recorder_event_sink = event_sink
        await self._channel.startRecording(
            language=params.get("language"), timeout=NO_TIMEOUT
        )

    async def _stop_recording(self) -> None:
        try:
            await self._channel.stopRecording(timeout=NO_TIMEOUT)
        finally:
            self._on_recorder_event_sink = None

    async def _expose_console_api(self) -> None:
        await self._channel.exposeConsoleApi(timeout=NO_TIMEOUT)

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

    def expect_console_message(
        self,
        predicate: Optional[Callable[[ConsoleMessage], bool]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(
            event=Events.BrowserContext.Console, predicate=predicate, timeout=timeout
        )

    def expect_page(
        self,
        predicate: Optional[Callable[[Page], bool]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Page]:
        return self.expect_event(
            event=Events.BrowserContext.Page, predicate=predicate, timeout=timeout
        )

    def __repr__(self) -> str:
        return f"<BrowserContext browser={self.browser}>"


async def prepare_storage_state(
    storage_state: Union[str, Path, StorageState],
) -> "channels.BrowserNewContextParamsStorageState":
    # Python: a path can be a pathlib.Path.
    if not isinstance(storage_state, (str, Path)):
        return cast("channels.BrowserNewContextParamsStorageState", storage_state)
    try:
        # Python: readFile(path, 'utf8') replaces the bytes that are not UTF-8.
        return json.loads(
            (await _read_file(storage_state)).decode("utf-8", errors="replace")
        )
    except Exception as e:
        # Python: rewrite_error_message() can not change the message of an OSError,
        # which formats it from its fields, so this raises an Error with the message.
        raise Error(
            f"Error reading storage state from {storage_state}:\n" + str(e)
        ) from e


async def prepare_browser_context_params(options: Dict[str, Any]) -> Dict[str, Any]:
    # Python: options has the Python names of the options, and the selectorEngines
    # and testIdAttributeName of Selectors._with_selector_options(). The result has
    # the parameters of newContext(), by their protocol names.
    if options.get("extra_http_headers"):
        network.validate_headers(options["extra_http_headers"])
    context_params: Dict[str, Any] = {
        # Python: { ...options }, the context options of the protocol.
        "screen": options.get("screen"),
        "ignoreHTTPSErrors": options.get("ignore_https_errors"),
        "javaScriptEnabled": options.get("java_script_enabled"),
        "bypassCSP": options.get("bypass_csp"),
        "userAgent": options.get("user_agent"),
        "locale": options.get("locale"),
        "timezoneId": options.get("timezone_id"),
        "geolocation": options.get("geolocation"),
        "permissions": options.get("permissions"),
        "offline": options.get("offline"),
        "deviceScaleFactor": options.get("device_scale_factor"),
        "isMobile": options.get("is_mobile"),
        "hasTouch": options.get("has_touch"),
        "baseURL": options.get("base_url"),
        # Python: recordVideo is the record_video_dir, record_video_size and
        # record_video_fps options.
        "recordVideo": (
            {
                "dir": options["record_video_dir"],
                "size": options.get("record_video_size"),
                "fps": options.get("record_video_fps"),
            }
            if options.get("record_video_dir") is not None
            else None
        ),
        "strictSelectors": options.get("strict_selectors"),
        "selectorEngines": options.get("selectorEngines"),
        "testIdAttributeName": options.get("testIdAttributeName"),
        "proxy": options.get("proxy"),
        # Python: `viewport: null` is no_viewport=True.
        "viewport": None if options.get("no_viewport") else options.get("viewport"),
        "noDefaultViewport": bool(options.get("no_viewport")),
        "extraHTTPHeaders": (
            headers_object_to_array(options["extra_http_headers"])
            if options.get("extra_http_headers") is not None
            else None
        ),
        "storageState": (
            await prepare_storage_state(options["storage_state"])
            if options.get("storage_state")
            else None
        ),
        "serviceWorkers": options.get("service_workers"),
        # Python: null is "null".
        "colorScheme": (
            "no-override"
            if options.get("color_scheme") == "null"
            else options.get("color_scheme")
        ),
        "reducedMotion": (
            "no-override"
            if options.get("reduced_motion") == "null"
            else options.get("reduced_motion")
        ),
        "forcedColors": (
            "no-override"
            if options.get("forced_colors") == "null"
            else options.get("forced_colors")
        ),
        "contrast": (
            "no-override"
            if options.get("contrast") == "null"
            else options.get("contrast")
        ),
        "acceptDownloads": to_accept_downloads_protocol(
            options.get("accept_downloads")
        ),
        "clientCertificates": await to_client_certificates_protocol(
            options.get("client_certificates")
        ),
        "httpCredentials": to_http_credentials_protocol(
            options.get("http_credentials")
        ),
    }
    if context_params["recordVideo"] and context_params["recordVideo"]["dir"]:
        context_params["recordVideo"]["dir"] = os.path.abspath(
            context_params["recordVideo"]["dir"]
        )
    return context_params


def to_http_credentials_protocol(
    credentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
) -> Optional[List["channels.HttpCredentials"]]:
    # Python: `!credentials`; an object is truthy in JavaScript.
    if credentials is None:
        return None
    list_ = (
        list(credentials) if isinstance(credentials, (list, tuple)) else [credentials]
    )
    return cast(List["channels.HttpCredentials"], list_) if len(list_) else None


def to_accept_downloads_protocol(
    accept_downloads: Optional[bool],
) -> Optional[Literal["accept", "deny"]]:
    if accept_downloads is None:
        return None
    if accept_downloads:
        return "accept"
    return "deny"


async def to_client_certificates_protocol(
    certs: Optional[Sequence[ClientCertificate]],
) -> Optional[List["channels.BrowserNewContextParamsClientCertificates"]]:
    # Python: `!certs`; an array is truthy in JavaScript.
    if certs is None:
        return None

    async def bufferize_content(
        value: Optional[bytes], file_path: Optional[Union[str, Path]]
    ) -> Optional[str]:
        # Python: a binary value of the protocol is a base64 string. A Buffer is
        # truthy in JavaScript, even when it is empty.
        if value is not None:
            return base64.b64encode(value).decode()
        if file_path:
            return base64.b64encode(await _read_file(file_path)).decode()
        return None

    async def to_protocol(cert: ClientCertificate) -> Dict[str, Any]:
        return {
            "origin": cert["origin"],
            "cert": await bufferize_content(cert.get("cert"), cert.get("certPath")),
            "key": await bufferize_content(cert.get("key"), cert.get("keyPath")),
            "pfx": await bufferize_content(cert.get("pfx"), cert.get("pfxPath")),
            "passphrase": cert.get("passphrase"),
        }

    return cast(
        List["channels.BrowserNewContextParamsClientCertificates"],
        await all_([to_protocol(cert) for cert in certs]),
    )


# Python only: helpers that upstream does not need.


def to_options(**options: Any) -> Dict[str, Any]:
    """The options object of an API method, from its parameters.

    None is undefined: the dict has the options that are set, by their Python names.
    """
    return {name: value for name, value in options.items() if value is not None}


async def _read_file(path: Union[str, Path]) -> bytes:
    # fs.promises.readFile(): reads in a thread.
    def read() -> bytes:
        with open(path, "rb") as file:
            return file.read()

    return await asyncio.get_running_loop().run_in_executor(None, read)


async def write_file(path: Union[str, Path], data: bytes) -> None:
    # fs.promises.writeFile(): writes in a thread.
    def write() -> None:
        with open(path, "wb") as file:
            file.write(data)

    await asyncio.get_running_loop().run_in_executor(None, write)
