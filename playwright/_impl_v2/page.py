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

"""Port of packages/playwright-core/src/client/page.ts.

Python:
- The getters that the generated API reads without a call (context, main_frame,
  frames, url, video, viewport_size, workers) are properties.
- waitForNavigation(), waitForRequest(), waitForResponse() and waitForEvent() keep
  their JS names; the Python API calls wait_for_event() only. The expect_*()
  methods of the Python API are context managers around their promises, at the
  end of the class.
- A page function is JavaScript source, never a function. So assertMaxArguments(),
  assertEvaluateOptions(), the exposeFunctions option of addInitScript() and
  addInitScriptWithExposedFunctions() are not ported.
- A JS Set keeps the insertion order; _frames and _workers are dicts with None
  values, the ordered sets of Python.
- Not ported, as they are JavaScript only: coverage, ariaSnapshotJSON(),
  [Symbol.asyncDispose](), the AbortSignal options, and _expectScreenshot(), the
  backend of toHaveScreenshot() of @playwright/test.
"""

import asyncio
import base64
import inspect
import os
import re
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
    FilePayload,
    FloatRect,
    PdfMargins,
    Position,
    ViewportSize,
)
from playwright._impl._errors import Error
from playwright._impl_v2.artifact import Artifact
from playwright._impl_v2.channel_owner import (
    ChannelOwner,
    api_call,
    from_channel,
    internal,
)
from playwright._impl_v2.client_helper import evaluation_script
from playwright._impl_v2.console_message import ConsoleMessage
from playwright._impl_v2.disposable import DisposableObject, DisposableStub
from playwright._impl_v2.download import Download
from playwright._impl_v2.element_handle import (
    ElementHandle,
    determine_screenshot_type,
)
from playwright._impl_v2.errors import (
    TargetClosedError,
    is_target_closed_error,
    parse_error,
    serialize_error,
)
from playwright._impl_v2.event_context_manager import EventContextManagerImpl
from playwright._impl_v2.events import Events
from playwright._impl_v2.file_chooser import FileChooser
from playwright._impl_v2.file_utils import mkdir_if_needed
from playwright._impl_v2.frame import Frame, verify_load_state
from playwright._impl_v2.har_router import HarRouter
from playwright._impl_v2.input import Keyboard, Mouse, Touchscreen
from playwright._impl_v2.internal_structures import AriaRole
from playwright._impl_v2.isomorphic.headers import headers_object_to_array
from playwright._impl_v2.isomorphic.manual_promise import LongStandingScope
from playwright._impl_v2.isomorphic.string_utils import (
    js_string,
    trim_string_with_ellipsis,
)
from playwright._impl_v2.isomorphic.url_match import (
    URLMatch,
    url_matches,
    url_matches_equal,
)
from playwright._impl_v2.js_handle import JSHandle, parse_result, serialize_argument
from playwright._impl_v2.network import (
    Request,
    Response,
    Route,
    RouteHandler,
    WebSocket,
    WebSocketRoute,
    WebSocketRouteHandler,
    validate_headers,
)
from playwright._impl_v2.screencast import Screencast
from playwright._impl_v2.timeout_settings import NO_TIMEOUT, TimeoutSettings
from playwright._impl_v2.utils.promise import all_, catch, start
from playwright._impl_v2.video import Video
from playwright._impl_v2.waiter import Waiter
from playwright._impl_v2.web_storage import WebStorage
from playwright._impl_v2.worker import Worker

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.browser_context import BrowserContext
    from playwright._impl_v2.clock import Clock
    from playwright._impl_v2.fetch import APIRequestContext
    from playwright._impl_v2.locator import FrameLocator, Locator
    from playwright._impl_v2.network import (
        RouteHandlerCallback,
        WebSocketRouteHandlerCallback,
    )
    from playwright._impl_v2.protocol_channels import (
        BindingCallChannel,
        PageChannel,
    )
    from playwright._impl_v2.web_mcp import WebMCP

# Python: the option types of the Python API, from the generated API.
DocumentLoadState = Literal["commit", "domcontentloaded", "load", "networkidle"]
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]
ScrollBehavior = Literal["auto", "none"]
URLMatchRequest = Union[str, Pattern[str], Callable[["Request"], Any]]
URLMatchResponse = Union[str, Pattern[str], Callable[["Response"], Any]]


class Page(ChannelOwner):
    _channel: "PageChannel"

    @staticmethod
    def from_(page: "PageChannel") -> "Page":
        return from_channel(page)

    @staticmethod
    def from_nullable(page: Optional["PageChannel"]) -> Optional["Page"]:
        return Page.from_(page) if page else None

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.PageInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Python: the fields, in the order of their declarations.
        self._browser_context: "BrowserContext"
        self._owned_context: Optional["BrowserContext"] = None
        self._api_name = "Page"

        self._main_frame: Frame
        self._frames: Dict[Frame, None] = {}
        self._workers: Dict[Worker, None] = {}
        self._closed = False
        self._closed_or_crashed_scope = LongStandingScope()
        self._viewport_size: Optional[ViewportSize] = None
        self._routes: List[RouteHandler] = []
        self._web_socket_routes: List[WebSocketRouteHandler] = []

        # Not ported: coverage, JavaScript only.
        self.keyboard: Keyboard
        self.mouse: Mouse
        self.request: "APIRequestContext"
        self.touchscreen: Touchscreen
        self.clock: "Clock"
        self.screencast: Screencast
        self.local_storage: WebStorage
        self.session_storage: WebStorage
        self.webmcp: "WebMCP"

        self._bindings: Dict[str, Callable[..., Any]] = {}
        self._timeout_settings: TimeoutSettings
        self._video: Video
        self._opener: Optional["Page"]
        self._close_reason: Optional[str] = None
        self._close_was_called = False
        self._har_routers: List[HarRouter] = []

        self._locator_handlers: Dict[int, Dict[str, Any]] = {}
        self._evaluate_callbacks: List[Dict[str, Any]] = []

        self._instrumentation.on_page(self)
        self._browser_context = cast("BrowserContext", parent)
        self._timeout_settings = TimeoutSettings(
            self._browser_context._timeout_settings
        )

        self.keyboard = Keyboard(self)
        self.mouse = Mouse(self)
        self.request = self._browser_context.request
        self.touchscreen = Touchscreen(self)
        self.clock = self._browser_context.clock
        self.local_storage = WebStorage(self, "local")
        self.session_storage = WebStorage(self, "session")

        self._main_frame = Frame.from_(initializer["mainFrame"])
        self._main_frame._page = self
        self.webmcp = self._main_frame.webmcp
        self._frames[self._main_frame] = None
        self._viewport_size = initializer.get("viewportSize")
        self._closed = initializer["isClosed"]
        self._opener = Page.from_nullable(initializer.get("opener"))
        self._video = Video(
            self._connection,
            Artifact.from_(initializer["video"]) if initializer.get("video") else None,
        )
        self.screencast = Screencast(self)

        self._channel.onBindingCall(
            lambda event: self._on_binding(BindingCall.from_(event["binding"]))
        )
        self._channel.onClose(lambda: self._on_close())
        self._channel.onCrash(lambda: self._on_crash())

        def on_download(event: "channels.PageDownloadEvent") -> None:
            artifact_object = Artifact.from_(event["artifact"])
            download = Download(
                self, event["url"], event["suggestedFilename"], artifact_object
            )
            self.emit(Events.Page.Download, download)
            self._browser_context.emit(Events.BrowserContext.Download, download)

        self._channel.onDownload(on_download)
        self._channel.onFileChooser(
            lambda event: self.emit(
                Events.Page.FileChooser,
                FileChooser(
                    self, ElementHandle.from_(event["element"]), event["isMultiple"]
                ),
            )
        )
        self._channel.onFrameAttached(
            lambda event: self._on_frame_attached(Frame.from_(event["frame"]))
        )
        self._channel.onFrameDetached(
            lambda event: self._on_frame_detached(Frame.from_(event["frame"]))
        )
        self._channel.onLocatorHandlerTriggered(
            lambda event: self._on_locator_handler_triggered(event["uid"])
        )
        self._channel.onRoute(lambda event: self._on_route(Route.from_(event["route"])))
        self._channel.onWebSocketRoute(
            lambda event: self._on_web_socket_route(
                WebSocketRoute.from_(event["webSocketRoute"])
            )
        )

        def on_viewport_size_changed(
            event: "channels.PageViewportSizeChangedEvent",
        ) -> None:
            self._viewport_size = event["viewportSize"]

        self._channel.onViewportSizeChanged(on_viewport_size_changed)
        self._channel.onWebSocket(
            lambda event: self.emit(
                Events.Page.WebSocket, WebSocket.from_(event["webSocket"])
            )
        )
        self._channel.onWorker(
            lambda event: self._on_worker(Worker.from_(event["worker"]))
        )

        # Not ported: this.coverage = new Coverage(this._channel), JavaScript only.

        self.once(
            Events.Page.Close,
            lambda _: self._closed_or_crashed_scope.close(
                self._close_error_with_reason()
            ),
        )
        self.once(
            Events.Page.Crash,
            lambda _: self._closed_or_crashed_scope.close(TargetClosedError()),
        )

        self._set_event_to_subscription_mapping(
            {
                Events.Page.Console: "console",
                Events.Page.Dialog: "dialog",
                Events.Page.DialogClosed: "dialogClosed",
                Events.Page.Request: "request",
                Events.Page.Response: "response",
                Events.Page.RequestFinished: "requestFinished",
                Events.Page.RequestFailed: "requestFailed",
                Events.Page.FileChooser: "fileChooser",
            }
        )

    def _on_frame_attached(self, frame: Frame) -> None:
        frame._page = self
        self._frames[frame] = None
        if frame._parent_frame:
            frame._parent_frame._child_frames[frame] = None
        self.emit(Events.Page.FrameAttached, frame)
        self._browser_context.emit(Events.BrowserContext.FrameAttached, frame)

    def _on_frame_detached(self, frame: Frame) -> None:
        self._frames.pop(frame, None)
        frame._detached = True
        if frame._parent_frame:
            frame._parent_frame._child_frames.pop(frame, None)
        self.emit(Events.Page.FrameDetached, frame)
        self._browser_context.emit(Events.BrowserContext.FrameDetached, frame)

    async def _on_route(self, route: Route) -> None:
        route._context = self.context
        route_handlers = list(self._routes)
        for route_handler in route_handlers:
            # If the page was closed we stall all requests right away.
            if self._close_was_called or self._browser_context.is_closed():
                return
            if not route_handler.matches(route.request.url):
                continue
            # Python: indexOf() by identity.
            index = next(
                (i for i, r in enumerate(self._routes) if r is route_handler), -1
            )
            if index == -1:
                continue
            if route_handler.will_expire():
                self._routes.pop(index)
            handled = await route_handler.handle(route)
            if not self._routes:
                catch(self._disable_interception())
            if handled:
                return

        await self._browser_context._on_route(route)

    async def _on_web_socket_route(self, web_socket_route: WebSocketRoute) -> None:
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
            await self._browser_context._on_web_socket_route(web_socket_route)

    async def _on_binding(self, binding_call: "BindingCall") -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func:
            await binding_call.call(func)
            return
        await self._browser_context._on_binding(binding_call)

    def _on_worker(self, worker: Worker) -> None:
        self._workers[worker] = None
        worker._page = self
        self.emit(Events.Page.Worker, worker)

    def _on_close(self) -> None:
        self._closed = True
        self._browser_context._pages.pop(self, None)
        self._dispose_har_routers()
        self.emit(Events.Page.Close, self)
        self._browser_context.emit(Events.BrowserContext.PageClose, self)

    def _on_crash(self) -> None:
        self.emit(Events.Page.Crash, self)

    @property
    def context(self) -> "BrowserContext":
        return self._browser_context

    async def opener(self) -> Optional["Page"]:
        if not self._opener or self._opener.is_closed():
            return None
        return self._opener

    @property
    def main_frame(self) -> Frame:
        return self._main_frame

    def frame(self, name: Optional[str], url: Optional[URLMatch]) -> Optional[Frame]:
        # Python: frameSelector is the name and url parameters.
        assert name or url, "Either name or url matcher should be specified"

        def find(f: Frame) -> bool:
            if name:
                return f.name == name
            return url_matches(
                self._browser_context._options.get("baseURL"), f.url, url
            )

        return next((f for f in self.frames if find(f)), None)

    @property
    def frames(self) -> List[Frame]:
        return list(self._frames)

    def set_default_navigation_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)

    def set_default_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_default_timeout(timeout)

    @property
    def video(self) -> Optional[Video]:
        # Note: we are creating Video object lazily, because we do not know
        # BrowserContextOptions when constructing the page - it is assigned
        # too late during launchPersistentContext.
        # Python: an empty object is truthy in JS, so only an absent recordVideo is
        # false. A remote server sends {} for it.
        if self._browser_context._options.get("recordVideo") is None:
            return None
        return self._video

    async def pick_locator(self) -> "Locator":
        selector = (await self._channel.pickLocator(timeout=NO_TIMEOUT))["selector"]
        return self.locator(
            selector, has_text=None, has_not_text=None, has=None, has_not=None
        )

    async def cancel_pick_locator(self) -> None:
        await self._channel.cancelPickLocator(timeout=NO_TIMEOUT)

    async def hide_highlight(self) -> None:
        await self._channel.hideHighlight(timeout=NO_TIMEOUT)

    async def query_selector(
        self, selector: str, strict: Optional[bool]
    ) -> Optional[ElementHandle]:
        return await self._main_frame.query_selector(selector=selector, strict=strict)

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[float],
        state: Optional[Literal["attached", "detached", "hidden", "visible"]],
        strict: Optional[bool],
    ) -> Optional[ElementHandle]:
        return await self._main_frame.wait_for_selector(
            selector=selector, timeout=timeout, state=state, strict=strict
        )

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: Optional[Dict],
        timeout: Optional[float],
        strict: Optional[bool],
    ) -> None:
        return await self._main_frame.dispatch_event(
            selector=selector,
            type=type,
            event_init=event_init,
            timeout=timeout,
            strict=strict,
        )

    async def evaluate_handle(self, expression: str, arg: Any) -> JSHandle:
        # Not ported: assertMaxArguments(arguments.length, 3).
        return await self._main_frame.evaluate_handle(expression=expression, arg=arg)

    async def eval_on_selector(
        self, selector: str, expression: str, arg: Any, strict: Optional[bool]
    ) -> Any:
        # Not ported: assertMaxArguments(arguments.length, 3).
        # Python: $eval() has the strict option of the Python API.
        return await self._main_frame.eval_on_selector(
            selector=selector, expression=expression, arg=arg, strict=strict
        )

    async def eval_on_selector_all(
        self, selector: str, expression: str, arg: Any
    ) -> Any:
        # Not ported: assertMaxArguments(arguments.length, 3).
        return await self._main_frame.eval_on_selector_all(
            selector=selector, expression=expression, arg=arg
        )

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        return await self._main_frame.query_selector_all(selector=selector)

    async def add_script_tag(
        self,
        url: Optional[str],
        path: Optional[Union[str, Path]],
        content: Optional[str],
        type: Optional[str],
    ) -> ElementHandle:
        return await self._main_frame.add_script_tag(
            url=url, path=path, content=content, type=type
        )

    async def add_style_tag(
        self,
        url: Optional[str],
        path: Optional[Union[str, Path]],
        content: Optional[str],
    ) -> ElementHandle:
        return await self._main_frame.add_style_tag(url=url, path=path, content=content)

    async def expose_function(
        self, name: str, callback: Callable[..., Any]
    ) -> DisposableObject:
        result = await self._channel.exposeBinding(
            name=name, noGlobal=None, timeout=NO_TIMEOUT
        )

        def binding(source: Dict[str, Any], *args: Any) -> Any:
            return callback(*args)

        self._bindings[name] = binding
        return DisposableObject.from_(result["disposable"])

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

    async def _expose_evaluate_callback(
        self, name: str, callback: Callable[..., Any]
    ) -> None:
        disposable = await self._expose_callback_binding(name, callback)
        self._evaluate_callbacks.append({"name": name, "disposable": disposable})

    def _erase_evaluate_callbacks(self) -> None:
        for evaluate_callback in self._evaluate_callbacks:
            self._bindings.pop(evaluate_callback["name"], None)
            catch(evaluate_callback["disposable"].dispose())
        self._evaluate_callbacks = []

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        validate_headers(headers)
        await self._channel.setExtraHTTPHeaders(
            headers=headers_object_to_array(headers), timeout=NO_TIMEOUT
        )

    @property
    def url(self) -> str:
        return self._main_frame.url

    async def content(self, include_shadow: Optional[bool]) -> str:
        return await self._main_frame.content(include_shadow=include_shadow)

    async def set_content(
        self,
        html: str,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
    ) -> None:
        return await self._main_frame.set_content(
            html=html, timeout=timeout, wait_until=wait_until
        )

    async def goto(
        self,
        url: str,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
        referer: Optional[str],
    ) -> Optional[Response]:
        return await self._main_frame.goto(
            url=url, timeout=timeout, wait_until=wait_until, referer=referer
        )

    async def reload(
        self,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
    ) -> Optional[Response]:
        # Python: the Python name of the option, as the tests assert.
        wait_until = verify_load_state(
            "wait_until", "load" if wait_until is None else wait_until
        )
        return Response.from_nullable(
            (
                await self._channel.reload(
                    waitUntil=wait_until,
                    timeout=self._timeout_settings.navigation_timeout(timeout),
                )
            )["response"]
        )

    async def add_locator_handler(
        self,
        locator: "Locator",
        handler: Callable[..., Any],
        no_wait_after: Optional[bool],
        times: Optional[int],
    ) -> None:
        if locator._frame is not self._main_frame:
            raise Error("Locator must belong to the main frame of this page")
        if times == 0:
            return
        uid = (
            await self._channel.registerLocatorHandler(
                selector=locator._selector,
                noWaitAfter=no_wait_after,
                timeout=NO_TIMEOUT,
            )
        )["uid"]
        self._locator_handlers[uid] = {
            "locator": locator,
            "handler": handler,
            "times": times,
        }

    async def _on_locator_handler_triggered(self, uid: int) -> None:
        remove = False
        try:
            handler = self._locator_handlers.get(uid)
            if handler and handler["times"] != 0:
                if handler["times"] is not None:
                    handler["times"] -= 1
                # Python: the handler may return an awaitable, as a JS handler
                # returns a promise. The generated API passes it the arguments that
                # it takes, so a handler without arguments works too.
                result = handler["handler"](handler["locator"])
                if inspect.isawaitable(result):
                    await result
            remove = handler is not None and handler["times"] == 0
        finally:
            if remove:
                self._locator_handlers.pop(uid, None)
            catch(
                self._channel.resolveLocatorHandlerNoReply(
                    uid=uid, remove=remove, timeout=NO_TIMEOUT
                )
            )

    async def remove_locator_handler(self, locator: "Locator") -> None:
        # Python: a dict can not change while it is iterated; a Map can.
        for uid, data in list(self._locator_handlers.items()):
            if data["locator"]._equals(locator):
                self._locator_handlers.pop(uid, None)
                await catch(
                    self._channel.unregisterLocatorHandler(uid=uid, timeout=NO_TIMEOUT)
                )

    async def wait_for_load_state(
        self,
        state: Optional[Literal["domcontentloaded", "load", "networkidle"]],
        timeout: Optional[float],
    ) -> None:
        return await self._main_frame.wait_for_load_state(state=state, timeout=timeout)

    async def wait_for_navigation(
        self,
        url: Optional[URLMatch],
        wait_until: Optional[DocumentLoadState],
        timeout: Optional[float],
    ) -> Optional[Response]:
        # Python: options is the url, wait_until and timeout parameters.
        return await self._main_frame.wait_for_navigation(
            url=url, wait_until=wait_until, timeout=timeout
        )

    async def wait_for_url(
        self,
        url: URLMatch,
        wait_until: Optional[DocumentLoadState],
        timeout: Optional[float],
    ) -> None:
        return await self._main_frame.wait_for_url(
            url=url, wait_until=wait_until, timeout=timeout
        )

    @api_call()
    async def wait_for_request(
        self,
        url_or_predicate: URLMatchRequest,
        timeout: Optional[float],
    ) -> Request:
        async def predicate(request: Request) -> bool:
            if isinstance(url_or_predicate, (str, re.Pattern)):
                return url_matches(
                    self._browser_context._options.get("baseURL"),
                    request.url,
                    url_or_predicate,
                )
            # Python: the predicate may return an awaitable, as a JS predicate
            # returns a promise.
            result = url_or_predicate(request)
            if inspect.isawaitable(result):
                result = await result
            return result

        trimmed_url = trim_url(url_or_predicate)
        log_line = f"waiting for request {trimmed_url}" if trimmed_url else None
        return await self._wait_for_event(
            Events.Page.Request, predicate, timeout, log_line
        )

    @api_call()
    async def wait_for_response(
        self,
        url_or_predicate: URLMatchResponse,
        timeout: Optional[float],
    ) -> Response:
        async def predicate(response: Response) -> bool:
            if isinstance(url_or_predicate, (str, re.Pattern)):
                return url_matches(
                    self._browser_context._options.get("baseURL"),
                    response.url,
                    url_or_predicate,
                )
            # Python: the predicate may return an awaitable, as a JS predicate
            # returns a promise.
            result = url_or_predicate(response)
            if inspect.isawaitable(result):
                result = await result
            return result

        trimmed_url = trim_url(url_or_predicate)
        log_line = f"waiting for response {trimmed_url}" if trimmed_url else None
        return await self._wait_for_event(
            Events.Page.Response, predicate, timeout, log_line
        )

    @api_call()
    async def wait_for_event(
        self,
        event: str,
        predicate: Optional[Callable[..., Any]],
        timeout: Optional[float],
    ) -> Any:
        # Python: optionsOrPredicate is the predicate and timeout parameters.
        return await self._wait_for_event(
            event, predicate, timeout, f'waiting for event "{event}"'
        )

    def _close_error_with_reason(self) -> TargetClosedError:
        return TargetClosedError(
            self._close_reason or self._browser_context._effective_close_reason()
        )

    async def _wait_for_event(
        self,
        event: str,
        predicate: Optional[Callable[..., Any]],
        timeout: Optional[float],
        log_line: Optional[str],
    ) -> Any:
        # Python: optionsOrPredicate is the predicate and timeout parameters.
        timeout_options = self._timeout_settings.timeout(timeout)
        waiter = Waiter.create_for_event(self, event)
        if log_line:
            waiter.log(log_line)
        waiter.reject_on_timeout(
            timeout_options,
            # Python: String(number) of JS, so that 30000.0 prints 30000.
            f'Timeout {js_string(timeout_options)}ms exceeded while waiting for event "{event}"',
        )
        if event != Events.Page.Crash:
            waiter.reject_on_event(self, Events.Page.Crash, Error("Page crashed"))
        if event != Events.Page.Close:
            waiter.reject_on_event(
                self, Events.Page.Close, lambda: self._close_error_with_reason()
            )
        result = await waiter.wait_for_event(self, event, predicate)
        waiter.dispose()
        return result

    async def go_back(
        self,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
    ) -> Optional[Response]:
        # Python: the Python name of the option, as the tests assert.
        wait_until = verify_load_state(
            "wait_until", "load" if wait_until is None else wait_until
        )
        return Response.from_nullable(
            (
                await self._channel.goBack(
                    waitUntil=wait_until,
                    timeout=self._timeout_settings.navigation_timeout(timeout),
                )
            )["response"]
        )

    async def go_forward(
        self,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
    ) -> Optional[Response]:
        # Python: the Python name of the option, as the tests assert.
        wait_until = verify_load_state(
            "wait_until", "load" if wait_until is None else wait_until
        )
        return Response.from_nullable(
            (
                await self._channel.goForward(
                    waitUntil=wait_until,
                    timeout=self._timeout_settings.navigation_timeout(timeout),
                )
            )["response"]
        )

    async def request_gc(self) -> None:
        await self._channel.requestGC(timeout=NO_TIMEOUT)

    async def emulate_media(
        self,
        media: Optional[Literal["null", "print", "screen"]],
        color_scheme: Optional[Literal["dark", "light", "no-preference", "null"]],
        reduced_motion: Optional[Literal["no-preference", "null", "reduce"]],
        forced_colors: Optional[Literal["active", "none", "null"]],
        contrast: Optional[Literal["more", "no-preference", "null"]],
    ) -> None:
        # Python: None is undefined, and the string "null" is null.
        await self._channel.emulateMedia(
            media="no-override" if media == "null" else media,
            colorScheme="no-override" if color_scheme == "null" else color_scheme,
            reducedMotion=(
                "no-override" if reduced_motion == "null" else reduced_motion
            ),
            forcedColors="no-override" if forced_colors == "null" else forced_colors,
            contrast="no-override" if contrast == "null" else contrast,
            timeout=NO_TIMEOUT,
        )

    async def set_viewport_size(self, viewport_size: ViewportSize) -> None:
        self._viewport_size = viewport_size
        await self._channel.setViewportSize(
            viewportSize=viewport_size, timeout=NO_TIMEOUT
        )

    @property
    def viewport_size(self) -> Optional[ViewportSize]:
        return self._viewport_size or None

    async def evaluate(self, expression: str, arg: Any) -> Any:
        # Not ported: assertMaxArguments(arguments.length, 3).
        return await self._main_frame.evaluate(expression=expression, arg=arg)

    async def add_init_script(
        self, script: Optional[str], path: Optional[Union[str, Path]]
    ) -> DisposableObject:
        # Not ported: assertEvaluateOptions() and the exposeFunctions option; a
        # script is never a function.
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

    @api_call(title="Route requests")
    async def route(
        self,
        url: URLMatch,
        handler: "RouteHandlerCallback",
        times: Optional[int],
    ) -> DisposableStub:
        self._routes.insert(
            0,
            RouteHandler(
                self._browser_context._options.get("baseURL"), url, handler, times
            ),
        )
        await self._update_interception_patterns()
        return DisposableStub(lambda: self.unroute(url=url, handler=handler))

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Optional[Union[Pattern[str], str]],
        not_found: Optional[Literal["abort", "fallback"]],
        update: Optional[bool],
        update_content: Optional[Literal["attach", "embed"]],
        update_mode: Optional[Literal["full", "minimal"]],
    ) -> None:
        local_utils = self._connection.local_utils()
        if not local_utils:
            raise Error("Route from har is not supported in thin clients")
        if update:
            await self._browser_context.tracing._record_into_har(
                har=har,
                page=self,
                url=url,
                update_content=update_content,
                update_mode=update_mode,
            )
            return
        # Python: har can be a Path.
        har_router = await HarRouter.create(
            local_utils, str(har), not_found or "abort", url
        )
        self._har_routers.append(har_router)
        await har_router.add_page_route(self)

    @api_call(title="Route WebSockets")
    async def route_web_socket(
        self, url: URLMatch, handler: "WebSocketRouteHandlerCallback"
    ) -> None:
        self._web_socket_routes.insert(
            0,
            WebSocketRouteHandler(
                self._browser_context._options.get("baseURL"), url, handler
            ),
        )
        await self._update_web_socket_interception_patterns()

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
        self, url: URLMatch, handler: Optional["RouteHandlerCallback"]
    ) -> None:
        removed = []
        remaining = []
        for route in self._routes:
            # Python: handlers compare with ==, so that a bound method matches.
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
            promises = [route_handler.stop(behavior) for route_handler in removed]
            await all_(promises)
        await self._update_interception_patterns()

    @internal
    async def _disable_interception(self) -> None:
        await self._update_interception_patterns()

    async def _update_interception_patterns(self) -> None:
        patterns = RouteHandler.prepare_interception_patterns(self._routes)
        await self._channel.setNetworkInterceptionPatterns(
            patterns=patterns, timeout=NO_TIMEOUT
        )

    async def _update_web_socket_interception_patterns(self) -> None:
        patterns = WebSocketRouteHandler.prepare_interception_patterns(
            self._web_socket_routes
        )
        await self._channel.setWebSocketInterceptionPatterns(
            patterns=patterns, timeout=NO_TIMEOUT
        )

    async def screenshot(
        self,
        timeout: Optional[float],
        type: Optional[Literal["jpeg", "png", "webp"]],
        path: Optional[Union[str, Path]],
        quality: Optional[int],
        omit_background: Optional[bool],
        full_page: Optional[bool],
        clip: Optional[FloatRect],
        animations: Optional[Literal["allow", "disabled"]],
        caret: Optional[Literal["hide", "initial"]],
        scale: Optional[Literal["css", "device"]],
        mask: Optional[Sequence["Locator"]],
        mask_color: Optional[str],
        style: Optional[str],
    ) -> bytes:
        # Python: copy is the parameters of the call; its mask and type change.
        copy_mask: Optional[List["channels.PageScreenshotParamsMask"]] = None
        copy_type = type
        if not copy_type:
            copy_type = determine_screenshot_type(path, type)
        # Python: an empty array is truthy in JS.
        if mask is not None:
            copy_mask = [
                {
                    "frame": locator._frame._channel,
                    "selector": locator._selector,
                }
                for locator in mask
            ]
        result = await self._channel.screenshot(
            type=copy_type,
            quality=quality,
            fullPage=full_page,
            clip=clip,
            omitBackground=omit_background,
            caret=caret,
            animations=animations,
            scale=scale,
            mask=copy_mask,
            maskColor=mask_color,
            style=style,
            timeout=self._timeout_settings.timeout(timeout),
        )
        # Python: binary is base64 on the wire.
        binary = base64.b64decode(result["binary"])
        if path:
            await mkdir_if_needed(path)
            await _write_file(path, binary)
        return binary

    # Not ported: _expectScreenshot(), the backend of toHaveScreenshot() of
    # @playwright/test. The Python API has no screenshot assertion.

    async def title(self) -> str:
        return await self._main_frame.title()

    async def bring_to_front(self) -> None:
        await self._channel.bringToFront(timeout=NO_TIMEOUT)

    # Not ported: [Symbol.asyncDispose](). Python: the generated Page is an async
    # context manager that calls close().

    async def close(
        self, run_before_unload: Optional[bool], reason: Optional[str]
    ) -> None:
        self._close_reason = reason
        if not run_before_unload:
            self._close_was_called = True
        try:
            if self._owned_context:
                await self._owned_context.close(reason=None)
            elif run_before_unload:
                await self._channel.runBeforeUnload(timeout=NO_TIMEOUT)
            else:
                await self._channel.close(reason=reason, timeout=NO_TIMEOUT)
        except Exception as e:
            if is_target_closed_error(e) and not run_before_unload:
                return
            raise

    def is_closed(self) -> bool:
        return self._closed

    async def click(
        self,
        selector: str,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        delay: Optional[float],
        button: Optional[MouseButton],
        click_count: Optional[int],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        strict: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.click(
            selector=selector,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            click_count=click_count,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            trial=trial,
            strict=strict,
            scroll=scroll,
        )

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        source_position: Optional[Position],
        target_position: Optional[Position],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        timeout: Optional[float],
        strict: Optional[bool],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.drag_and_drop(
            source=source,
            target=target,
            source_position=source_position,
            target_position=target_position,
            force=force,
            no_wait_after=no_wait_after,
            timeout=timeout,
            strict=strict,
            trial=trial,
            steps=steps,
            scroll=scroll,
        )

    async def dblclick(
        self,
        selector: str,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        delay: Optional[float],
        button: Optional[MouseButton],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        await self._main_frame.dblclick(
            selector=selector,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            strict=strict,
            trial=trial,
            scroll=scroll,
        )

    async def tap(
        self,
        selector: str,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.tap(
            selector=selector,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            strict=strict,
            trial=trial,
            scroll=scroll,
        )

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        force: Optional[bool],
    ) -> None:
        return await self._main_frame.fill(
            selector=selector,
            value=value,
            timeout=timeout,
            no_wait_after=no_wait_after,
            strict=strict,
            force=force,
        )

    async def clear_console_messages(self) -> None:
        await self._channel.clearConsoleMessages(timeout=NO_TIMEOUT)

    async def console_messages(
        self, filter: Optional[Literal["all", "since-navigation"]]
    ) -> List[ConsoleMessage]:
        messages = (
            await self._channel.consoleMessages(filter=filter, timeout=NO_TIMEOUT)
        )["messages"]
        return [ConsoleMessage(message, self, None) for message in messages]

    async def clear_page_errors(self) -> None:
        await self._channel.clearPageErrors(timeout=NO_TIMEOUT)

    async def page_errors(
        self, filter: Optional[Literal["all", "since-navigation"]]
    ) -> List[Error]:
        errors = (await self._channel.pageErrors(filter=filter, timeout=NO_TIMEOUT))[
            "errors"
        ]
        return [parse_error(error) for error in errors]

    def locator(
        self,
        selector: str,
        has_text: Optional[Union[str, Pattern[str]]],
        has_not_text: Optional[Union[str, Pattern[str]]],
        has: Optional["Locator"],
        has_not: Optional["Locator"],
    ) -> "Locator":
        return self.main_frame.locator(
            selector=selector,
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )

    def get_by_test_id(self, test_id: Union[str, Pattern[str]]) -> "Locator":
        return self.main_frame.get_by_test_id(test_id=test_id)

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.main_frame.get_by_alt_text(text=text, exact=exact)

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.main_frame.get_by_label(text=text, exact=exact)

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.main_frame.get_by_placeholder(text=text, exact=exact)

    def get_by_ref(self, ref: str) -> "Locator":
        return self.locator(
            f"aria-ref={ref}", has_text=None, has_not_text=None, has=None, has_not=None
        )

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.main_frame.get_by_text(text=text, exact=exact)

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.main_frame.get_by_title(text=text, exact=exact)

    def get_by_role(
        self,
        role: AriaRole,
        checked: Optional[bool],
        disabled: Optional[bool],
        expanded: Optional[bool],
        include_hidden: Optional[bool],
        level: Optional[int],
        name: Optional[Union[str, Pattern[str]]],
        pressed: Optional[bool],
        selected: Optional[bool],
        exact: Optional[bool],
        description: Optional[Union[str, Pattern[str]]],
    ) -> "Locator":
        return self.main_frame.get_by_role(
            role=role,
            checked=checked,
            disabled=disabled,
            expanded=expanded,
            include_hidden=include_hidden,
            level=level,
            name=name,
            pressed=pressed,
            selected=selected,
            exact=exact,
            description=description,
        )

    def frame_locator(self, selector: Optional[str]) -> "FrameLocator":
        return self.main_frame.frame_locator(selector=selector)

    async def focus(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> None:
        return await self._main_frame.focus(
            selector=selector, strict=strict, timeout=timeout
        )

    async def text_content(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> Optional[str]:
        return await self._main_frame.text_content(
            selector=selector, strict=strict, timeout=timeout
        )

    async def inner_text(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> str:
        return await self._main_frame.inner_text(
            selector=selector, strict=strict, timeout=timeout
        )

    async def inner_html(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> str:
        return await self._main_frame.inner_html(
            selector=selector, strict=strict, timeout=timeout
        )

    async def get_attribute(
        self,
        selector: str,
        name: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> Optional[str]:
        return await self._main_frame.get_attribute(
            selector=selector, name=name, strict=strict, timeout=timeout
        )

    async def input_value(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> str:
        return await self._main_frame.input_value(
            selector=selector, strict=strict, timeout=timeout
        )

    async def is_checked(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> bool:
        return await self._main_frame.is_checked(
            selector=selector, strict=strict, timeout=timeout
        )

    async def is_disabled(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> bool:
        return await self._main_frame.is_disabled(
            selector=selector, strict=strict, timeout=timeout
        )

    async def is_editable(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> bool:
        return await self._main_frame.is_editable(
            selector=selector, strict=strict, timeout=timeout
        )

    async def is_enabled(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> bool:
        return await self._main_frame.is_enabled(
            selector=selector, strict=strict, timeout=timeout
        )

    async def is_hidden(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> bool:
        # Python: Frame.is_hidden() of the Python API takes no timeout; the option
        # of Page.is_hidden() is deprecated and does nothing.
        return await self._main_frame.is_hidden(selector=selector, strict=strict)

    async def is_visible(
        self, selector: str, strict: Optional[bool], timeout: Optional[float]
    ) -> bool:
        # Python: Frame.is_visible() of the Python API takes no timeout; the option
        # of Page.is_visible() is deprecated and does nothing.
        return await self._main_frame.is_visible(selector=selector, strict=strict)

    async def hover(
        self,
        selector: str,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.hover(
            selector=selector,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
            no_wait_after=no_wait_after,
            force=force,
            strict=strict,
            trial=trial,
            scroll=scroll,
        )

    async def select_option(
        self,
        selector: str,
        value: Optional[Union[str, Sequence[str]]],
        index: Optional[Union[int, Sequence[int]]],
        label: Optional[Union[str, Sequence[str]]],
        element: Optional[Union[ElementHandle, Sequence[ElementHandle]]],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
        strict: Optional[bool],
    ) -> List[str]:
        # Python: values is the value, index, label and element parameters.
        return await self._main_frame.select_option(
            selector=selector,
            value=value,
            index=index,
            label=label,
            element=element,
            timeout=timeout,
            no_wait_after=no_wait_after,
            force=force,
            strict=strict,
        )

    async def set_input_files(
        self,
        selector: str,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        timeout: Optional[float],
        strict: Optional[bool],
        no_wait_after: Optional[bool],
    ) -> None:
        return await self._main_frame.set_input_files(
            selector=selector,
            files=files,
            timeout=timeout,
            strict=strict,
            no_wait_after=no_wait_after,
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
    ) -> None:
        return await self._main_frame.type(
            selector=selector,
            text=text,
            delay=delay,
            timeout=timeout,
            no_wait_after=no_wait_after,
            strict=strict,
        )

    async def press(
        self,
        selector: str,
        key: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
    ) -> None:
        return await self._main_frame.press(
            selector=selector,
            key=key,
            delay=delay,
            timeout=timeout,
            no_wait_after=no_wait_after,
            strict=strict,
        )

    async def check(
        self,
        selector: str,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.check(
            selector=selector,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            strict=strict,
            trial=trial,
            scroll=scroll,
        )

    async def uncheck(
        self,
        selector: str,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.uncheck(
            selector=selector,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            strict=strict,
            trial=trial,
            scroll=scroll,
        )

    async def set_checked(
        self,
        selector: str,
        checked: bool,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[ScrollBehavior],
    ) -> None:
        return await self._main_frame.set_checked(
            selector=selector,
            checked=checked,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            strict=strict,
            trial=trial,
            scroll=scroll,
        )

    async def wait_for_timeout(self, timeout: float) -> None:
        return await self._main_frame.wait_for_timeout(timeout=timeout)

    async def wait_for_function(
        self,
        expression: str,
        arg: Any,
        timeout: Optional[float],
        polling: Optional[Union[float, Literal["raf"]]],
    ) -> JSHandle:
        return await self._main_frame.wait_for_function(
            expression=expression, arg=arg, timeout=timeout, polling=polling
        )

    async def requests(self) -> List[Request]:
        requests = (await self._channel.requests(timeout=NO_TIMEOUT))["requests"]
        return [Request.from_(request) for request in requests]

    @property
    def workers(self) -> List[Worker]:
        return list(self._workers)

    async def pause(self) -> None:
        # Not ported: the early return when a JS debugger is attached
        # (inspector.url() of Node.js).
        default_navigation_timeout = (
            self._browser_context._timeout_settings.default_navigation_timeout()
        )
        default_timeout = self._browser_context._timeout_settings.default_timeout()
        self._browser_context.set_default_navigation_timeout(0)
        self._browser_context.set_default_timeout(0)
        # Python: the Python API has no __testHookKeepTestTimeout option.
        self._instrumentation.on_will_pause({"keepTestTimeout": False})
        await self._closed_or_crashed_scope.safe_race(
            self.context._channel.pause(timeout=NO_TIMEOUT)
        )
        self._browser_context.set_default_navigation_timeout(default_navigation_timeout)
        self._browser_context.set_default_timeout(default_timeout)

    async def pdf(
        self,
        scale: Optional[float],
        display_header_footer: Optional[bool],
        header_template: Optional[str],
        footer_template: Optional[str],
        print_background: Optional[bool],
        landscape: Optional[bool],
        page_ranges: Optional[str],
        format: Optional[str],
        width: Optional[Union[str, float]],
        height: Optional[Union[str, float]],
        prefer_css_page_size: Optional[bool],
        margin: Optional[PdfMargins],
        path: Optional[Union[str, Path]],
        outline: Optional[bool],
        tagged: Optional[bool],
    ) -> bytes:
        # Python: transportOptions is the parameters of the call; width, height and
        # margin change. An empty object is truthy in JS, so None is the only false
        # margin.
        transport_width: Any = width
        transport_height: Any = height
        transport_margin: Any = None
        if margin is not None:
            transport_margin = dict(margin)
        if _is_number(width):
            # Python: String(number) of JS, so that 100.0 prints 100.
            transport_width = js_string(width) + "px"
        if _is_number(height):
            transport_height = js_string(height) + "px"
        for index in ["top", "right", "bottom", "left"]:
            if margin is not None and _is_number(margin.get(index)):
                transport_margin[index] = js_string(transport_margin[index]) + "px"
        result = await self._channel.pdf(
            scale=scale,
            displayHeaderFooter=display_header_footer,
            headerTemplate=header_template,
            footerTemplate=footer_template,
            printBackground=print_background,
            landscape=landscape,
            pageRanges=page_ranges,
            format=format,
            width=transport_width,
            height=transport_height,
            preferCSSPageSize=prefer_css_page_size,
            margin=transport_margin,
            tagged=tagged,
            outline=outline,
            timeout=NO_TIMEOUT,
        )
        # Python: binary is base64 on the wire.
        pdf = base64.b64decode(result["pdf"])
        if path:
            await _mkdir(os.path.dirname(path))
            await _write_file(path, pdf)
        return pdf

    async def aria_snapshot(
        self,
        timeout: Optional[float],
        depth: Optional[int],
        mode: Optional[Literal["ai", "default"]],
        boxes: Optional[bool],
    ) -> str:
        result = await self.main_frame._channel.ariaSnapshot(
            mode=mode,
            selector=None,
            depth=depth,
            boxes=boxes,
            timeout=self._timeout_settings.timeout(timeout),
        )
        return result["snapshot"]

    # Not ported: ariaSnapshotJSON(), JavaScript only (langs: js in the docs).

    async def _set_dock_tile(self, image: bytes) -> None:
        # Python: binary is base64 on the wire.
        await self._channel.setDockTile(
            image=base64.b64encode(image).decode(), timeout=NO_TIMEOUT
        )

    # Python only: the members of the Python API that upstream does not have.
    # The expect_*() methods are context managers around the promises of the
    # waitFor*() methods. The wait runs in a task, which starts before the action
    # in the with block makes the event happen; the call that starts it is the API
    # call, so its stack names the expect_*() method.

    def expect_navigation(
        self,
        url: Optional[URLMatch],
        wait_until: Optional[DocumentLoadState],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Response]:
        return self._main_frame.expect_navigation(
            url=url, wait_until=wait_until, timeout=timeout
        )

    def expect_request(
        self,
        url_or_predicate: URLMatchRequest,
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Request]:
        return EventContextManagerImpl(
            start(
                self.wait_for_request(
                    url_or_predicate=url_or_predicate, timeout=timeout
                )
            )
        )

    def expect_response(
        self,
        url_or_predicate: URLMatchResponse,
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Response]:
        return EventContextManagerImpl(
            start(
                self.wait_for_response(
                    url_or_predicate=url_or_predicate, timeout=timeout
                )
            )
        )

    def expect_event(
        self,
        event: str,
        predicate: Optional[Callable[..., Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl:
        return EventContextManagerImpl(
            start(
                self.wait_for_event(event=event, predicate=predicate, timeout=timeout)
            )
        )

    def expect_console_message(
        self,
        predicate: Optional[Callable[[ConsoleMessage], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(
            event=Events.Page.Console, predicate=predicate, timeout=timeout
        )

    def expect_download(
        self,
        predicate: Optional[Callable[[Download], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Download]:
        return self.expect_event(
            event=Events.Page.Download, predicate=predicate, timeout=timeout
        )

    def expect_file_chooser(
        self,
        predicate: Optional[Callable[[FileChooser], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[FileChooser]:
        return self.expect_event(
            event=Events.Page.FileChooser, predicate=predicate, timeout=timeout
        )

    def expect_popup(
        self,
        predicate: Optional[Callable[["Page"], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl["Page"]:
        return self.expect_event(
            event=Events.Page.Popup, predicate=predicate, timeout=timeout
        )

    def expect_request_finished(
        self,
        predicate: Optional[Callable[[Request], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Request]:
        return self.expect_event(
            event=Events.Page.RequestFinished, predicate=predicate, timeout=timeout
        )

    def expect_websocket(
        self,
        predicate: Optional[Callable[[WebSocket], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[WebSocket]:
        return self.expect_event(
            event=Events.Page.WebSocket, predicate=predicate, timeout=timeout
        )

    def expect_worker(
        self,
        predicate: Optional[Callable[[Worker], Any]],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Worker]:
        return self.expect_event(
            event=Events.Page.Worker, predicate=predicate, timeout=timeout
        )

    def __repr__(self) -> str:
        return f"<Page url={self.url!r}>"


class BindingCall(ChannelOwner):
    _channel: "BindingCallChannel"

    @staticmethod
    def from_(channel: "BindingCallChannel") -> "BindingCall":
        return from_channel(channel)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.BindingCallInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def call(self, func: Callable[..., Any]) -> None:
        try:
            frame = Frame.from_(self._initializer["frame"])
            page = cast(Page, frame._page)
            source = {
                "context": page.context,
                "page": page,
                "frame": frame,
            }
            # Python: the callback may return an awaitable, as a JS callback returns
            # a promise.
            result = func(
                source, *[parse_result(arg) for arg in self._initializer["args"]]
            )
            if inspect.isawaitable(result):
                result = await result
            # Python: _to_impl() turns the API objects of the result into impl objects.
            catch(
                self._channel.resolve(
                    result=serialize_argument(_to_impl(result)), timeout=NO_TIMEOUT
                )
            )
        except Exception as e:
            catch(self._channel.reject(error=serialize_error(e), timeout=NO_TIMEOUT))


def trim_url(param: Any) -> Optional[str]:
    if isinstance(param, re.Pattern):
        # Python: the flags of a JavaScript RegExp, in the order of
        # RegExp.prototype.flags.
        flags = "".join(
            flag
            for flag, bit in (
                ("i", re.IGNORECASE),
                ("m", re.MULTILINE),
                ("s", re.DOTALL),
            )
            if param.flags & bit
        )
        return f"/{trim_string_with_ellipsis(param.pattern, 50)}/{flags}"
    if isinstance(param, str):
        return f'"{trim_string_with_ellipsis(param, 50)}"'
    return None


# Not ported: addInitScriptWithExposedFunctions(). It takes an init script that is a
# function, and a script is JavaScript source in Python.


def _is_number(value: Any) -> bool:
    # Python: typeof value === 'number'. bool is an int in Python.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


async def _mkdir(dir: str) -> None:
    # Python: fs.promises.mkdir(dir, { recursive: true }) in a thread. The dirname of
    # a file name is '' in Python and '.' in Node.js.
    def mkdir() -> None:
        os.makedirs(dir or ".", exist_ok=True)

    await asyncio.get_running_loop().run_in_executor(None, mkdir)


async def _write_file(path: Union[str, Path], data: bytes) -> None:
    # Python: fs.promises.writeFile(path, data) in a thread.
    def write() -> None:
        with open(path, "wb") as file:
            file.write(data)

    await asyncio.get_running_loop().run_in_executor(None, write)


def _to_impl(value: Any) -> Any:
    # Python: a callback of the Python API returns the objects of the API, such as
    # a JSHandle. serialize_argument() takes their impl objects.
    if isinstance(value, dict):
        return {key: _to_impl(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_impl(item) for item in value]
    impl = getattr(value, "_impl_obj", None)
    return impl if impl is not None else value
