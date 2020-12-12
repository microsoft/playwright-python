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
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast

from playwright._accessibility import Accessibility
from playwright._connection import ChannelOwner, from_channel, from_nullable_channel
from playwright._console_message import ConsoleMessage
from playwright._dialog import Dialog
from playwright._download import Download
from playwright._element_handle import ElementHandle, ValuesToSelect
from playwright._event_context_manager import EventContextManagerImpl
from playwright._file_chooser import FileChooser
from playwright._frame import Frame
from playwright._helper import (
    ColorScheme,
    DocumentLoadState,
    KeyboardModifier,
    MouseButton,
    PendingWaitEvent,
    RouteHandler,
    RouteHandlerEntry,
    TimeoutSettings,
    URLMatch,
    URLMatcher,
    is_function_body,
    is_safe_close_error,
    locals_to_params,
    parse_error,
    serialize_error,
)
from playwright._input import Keyboard, Mouse, Touchscreen
from playwright._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._network import Request, Response, Route, serialize_headers
from playwright._types import (
    Error,
    FilePayload,
    FloatRect,
    IntSize,
    MousePosition,
    PdfMargins,
)
from playwright._video import Video
from playwright._wait_helper import WaitHelper

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._browser_context import BrowserContext


class Page(ChannelOwner):

    Events = SimpleNamespace(
        Close="close",
        Crash="crash",
        Console="console",
        Dialog="dialog",
        Download="download",
        FileChooser="filechooser",
        DOMContentLoaded="domcontentloaded",
        PageError="pageerror",
        Request="request",
        Response="response",
        RequestFailed="requestfailed",
        RequestFinished="requestfinished",
        FrameAttached="frameattached",
        FrameDetached="framedetached",
        FrameNavigated="framenavigated",
        Load="load",
        Popup="popup",
        WebSocket="websocket",
        Worker="worker",
    )
    accessibility: Accessibility
    keyboard: Keyboard
    mouse: Mouse
    touchscreen: Touchscreen

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.accessibility = Accessibility(self._channel)
        self.keyboard = Keyboard(self._channel)
        self.mouse = Mouse(self._channel)
        self.touchscreen = Touchscreen(self._channel)

        self._main_frame: Frame = from_channel(initializer["mainFrame"])
        self._main_frame._page = self
        self._frames = [self._main_frame]
        self._viewport_size = initializer.get("viewportSize")
        self._is_closed = False
        self._workers: List["Worker"] = []
        self._bindings: Dict[str, Any] = {}
        self._pending_wait_for_events: List[PendingWaitEvent] = []
        self._routes: List[RouteHandlerEntry] = []
        self._owned_context: Optional["BrowserContext"] = None
        self._timeout_settings: TimeoutSettings = TimeoutSettings(None)
        self._video: Optional[Video] = None

        self._channel.on(
            "bindingCall",
            lambda params: self._on_binding(from_channel(params["binding"])),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._channel.on(
            "console",
            lambda params: self.emit(
                Page.Events.Console, from_channel(params["message"])
            ),
        )
        self._channel.on("crash", lambda _: self._on_crash())
        self._channel.on(
            "dialog",
            lambda params: self.emit(
                Page.Events.Dialog, from_channel(params["dialog"])
            ),
        )
        self._channel.on(
            "domcontentloaded", lambda _: self.emit(Page.Events.DOMContentLoaded)
        )
        self._channel.on(
            "download",
            lambda params: self.emit(
                Page.Events.Download, from_channel(params["download"])
            ),
        )
        self._channel.on(
            "fileChooser",
            lambda params: self.emit(
                Page.Events.FileChooser,
                FileChooser(
                    self, from_channel(params["element"]), params["isMultiple"]
                ),
            ),
        )
        self._channel.on(
            "frameAttached",
            lambda params: self._on_frame_attached(from_channel(params["frame"])),
        )
        self._channel.on(
            "frameDetached",
            lambda params: self._on_frame_detached(from_channel(params["frame"])),
        )
        self._channel.on("load", lambda _: self.emit(Page.Events.Load))
        self._channel.on(
            "pageError",
            lambda params: self.emit(
                Page.Events.PageError, parse_error(params["error"]["error"])
            ),
        )
        self._channel.on(
            "popup",
            lambda params: self.emit(Page.Events.Popup, from_channel(params["page"])),
        )
        self._channel.on(
            "request",
            lambda params: self.emit(
                Page.Events.Request, from_channel(params["request"])
            ),
        )
        self._channel.on(
            "requestFailed",
            lambda params: self._on_request_failed(
                from_channel(params["request"]),
                params["responseEndTiming"],
                params["failureText"],
            ),
        )
        self._channel.on(
            "requestFinished",
            lambda params: self._on_request_finished(
                from_channel(params["request"]), params["responseEndTiming"]
            ),
        )
        self._channel.on(
            "response",
            lambda params: self.emit(
                Page.Events.Response, from_channel(params["response"])
            ),
        )
        self._channel.on(
            "route",
            lambda params: self._on_route(
                from_channel(params["route"]), from_channel(params["request"])
            ),
        )
        self._channel.on(
            "video",
            lambda params: cast(Video, self.video)._set_relative_path(
                params["relativePath"]
            ),
        )
        self._channel.on(
            "webSocket",
            lambda params: self.emit(
                Page.Events.WebSocket, from_channel(params["webSocket"])
            ),
        )
        self._channel.on(
            "worker", lambda params: self._on_worker(from_channel(params["worker"]))
        )

    def _set_browser_context(self, context: "BrowserContext") -> None:
        self._browser_context = context
        self._timeout_settings = TimeoutSettings(context._timeout_settings)

    def _on_request_failed(
        self,
        request: Request,
        response_end_timing: float,
        failure_text: str = None,
    ) -> None:
        request._failure_text = failure_text
        if request._timing:
            request._timing["responseEnd"] = response_end_timing
        self.emit(Page.Events.RequestFailed, request)

    def _on_request_finished(
        self, request: Request, response_end_timing: float
    ) -> None:
        if request._timing:
            request._timing["responseEnd"] = response_end_timing
        self.emit(Page.Events.RequestFinished, request)

    def _on_frame_attached(self, frame: Frame) -> None:
        frame._page = self
        self._frames.append(frame)
        self.emit(Page.Events.FrameAttached, frame)

    def _on_frame_detached(self, frame: Frame) -> None:
        self._frames.remove(frame)
        frame._detached = True
        self.emit(Page.Events.FrameDetached, frame)

    def _on_route(self, route: Route, request: Request) -> None:
        for handler_entry in self._routes:
            if handler_entry.matcher.matches(request.url):
                handler_entry.handler(route, request)
                return
        self._browser_context._on_route(route, request)

    def _on_binding(self, binding_call: "BindingCall") -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func:
            asyncio.create_task(binding_call.call(func))
        self._browser_context._on_binding(binding_call)

    def _on_worker(self, worker: "Worker") -> None:
        self._workers.append(worker)
        worker._page = self
        self.emit(Page.Events.Worker, worker)

    def _on_close(self) -> None:
        self._is_closed = True
        self._browser_context._pages.remove(self)
        self._reject_pending_operations(False)
        self.emit(Page.Events.Close)

    def _on_crash(self) -> None:
        self._reject_pending_operations(True)
        self.emit(Page.Events.Crash)

    def _reject_pending_operations(self, is_crash: bool) -> None:
        for pending_event in self._pending_wait_for_events:
            pending_event.reject(is_crash, "Page")

    def _add_event_handler(self, event: str, k: Any, v: Any) -> None:
        if event == Page.Events.FileChooser and len(self.listeners(event)) == 0:
            self._channel.send_no_reply(
                "setFileChooserInterceptedNoReply", {"intercepted": True}
            )
        super()._add_event_handler(event, k, v)

    def remove_listener(self, event: str, f: Any) -> None:
        super().remove_listener(event, f)
        if event == Page.Events.FileChooser and len(self.listeners(event)) == 0:
            self._channel.send_no_reply(
                "setFileChooserInterceptedNoReply", {"intercepted": False}
            )

    @property
    def context(self) -> "BrowserContext":
        return self._browser_context

    async def opener(self) -> Optional["Page"]:
        return from_nullable_channel(await self._channel.send("opener"))

    @property
    def mainFrame(self) -> Frame:
        return self._main_frame

    def frame(self, name: str = None, url: URLMatch = None) -> Optional[Frame]:
        matcher = URLMatcher(url) if url else None
        for frame in self._frames:
            if name and frame.name == name:
                return frame
            if url and matcher and matcher.matches(frame.url):
                return frame
        return None

    @property
    def frames(self) -> List[Frame]:
        return self._frames.copy()

    def setDefaultNavigationTimeout(self, timeout: int) -> None:
        self._timeout_settings.set_navigation_timeout(timeout)
        self._channel.send_no_reply(
            "setDefaultNavigationTimeoutNoReply", dict(timeout=timeout)
        )

    def setDefaultTimeout(self, timeout: int) -> None:
        self._timeout_settings.set_timeout(timeout)
        self._channel.send_no_reply("setDefaultTimeoutNoReply", dict(timeout=timeout))

    async def querySelector(self, selector: str) -> Optional[ElementHandle]:
        return await self._main_frame.querySelector(selector)

    async def querySelectorAll(self, selector: str) -> List[ElementHandle]:
        return await self._main_frame.querySelectorAll(selector)

    async def waitForSelector(
        self,
        selector: str,
        timeout: int = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> Optional[ElementHandle]:
        return await self._main_frame.waitForSelector(**locals_to_params(locals()))

    async def dispatchEvent(
        self, selector: str, type: str, eventInit: Dict = None, timeout: int = None
    ) -> None:
        return await self._main_frame.dispatchEvent(**locals_to_params(locals()))

    async def evaluate(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
    ) -> Any:
        return await self._main_frame.evaluate(expression, arg, force_expr=force_expr)

    async def evaluateHandle(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
    ) -> JSHandle:
        return await self._main_frame.evaluateHandle(
            expression, arg, force_expr=force_expr
        )

    async def evalOnSelector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        force_expr: bool = None,
    ) -> Any:
        return await self._main_frame.evalOnSelector(
            selector, expression, arg, force_expr=force_expr
        )

    async def evalOnSelectorAll(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        force_expr: bool = None,
    ) -> Any:
        return await self._main_frame.evalOnSelectorAll(
            selector, expression, arg, force_expr=force_expr
        )

    async def addScriptTag(
        self,
        url: str = None,
        path: Union[str, Path] = None,
        content: str = None,
        type: str = None,
    ) -> ElementHandle:
        return await self._main_frame.addScriptTag(**locals_to_params(locals()))

    async def addStyleTag(
        self, url: str = None, path: Union[str, Path] = None, content: str = None
    ) -> ElementHandle:
        return await self._main_frame.addStyleTag(**locals_to_params(locals()))

    async def exposeFunction(self, name: str, binding: Callable) -> None:
        await self.exposeBinding(name, lambda source, *args: binding(*args))

    async def exposeBinding(
        self, name: str, binding: Callable, handle: bool = None
    ) -> None:
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        if name in self._browser_context._bindings:
            raise Error(
                f'Function "{name}" has been already registered in the browser context'
            )
        self._bindings[name] = binding
        await self._channel.send(
            "exposeBinding", dict(name=name, needsHandle=handle or False)
        )

    async def setExtraHTTPHeaders(self, headers: Dict[str, str]) -> None:
        await self._channel.send(
            "setExtraHTTPHeaders", dict(headers=serialize_headers(headers))
        )

    @property
    def url(self) -> str:
        return self._main_frame.url

    async def content(self) -> str:
        return await self._main_frame.content()

    async def setContent(
        self,
        html: str,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
    ) -> None:
        return await self._main_frame.setContent(**locals_to_params(locals()))

    async def goto(
        self,
        url: str,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
        referer: str = None,
    ) -> Optional[Response]:
        return await self._main_frame.goto(**locals_to_params(locals()))

    async def reload(
        self,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("reload", locals_to_params(locals()))
        )

    async def waitForLoadState(
        self, state: DocumentLoadState = None, timeout: int = None
    ) -> None:
        return await self._main_frame.waitForLoadState(**locals_to_params(locals()))

    async def waitForNavigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: int = None,
    ) -> Optional[Response]:
        return await self._main_frame.waitForNavigation(**locals_to_params(locals()))

    async def waitForRequest(
        self,
        url: URLMatch = None,
        predicate: Callable[[Request], bool] = None,
        timeout: int = None,
    ) -> Request:
        matcher = URLMatcher(url) if url else None

        def my_predicate(request: Request) -> bool:
            if matcher:
                return matcher.matches(request.url)
            if predicate:
                return predicate(request)
            return True

        return cast(
            Request,
            await self.waitForEvent(
                Page.Events.Request, predicate=my_predicate, timeout=timeout
            ),
        )

    async def waitForResponse(
        self,
        url: URLMatch = None,
        predicate: Callable[[Response], bool] = None,
        timeout: int = None,
    ) -> Response:
        matcher = URLMatcher(url) if url else None

        def my_predicate(response: Response) -> bool:
            if matcher:
                return matcher.matches(response.url)
            if predicate:
                return predicate(response)
            return True

        return cast(
            Response,
            await self.waitForEvent(
                Page.Events.Response, predicate=my_predicate, timeout=timeout
            ),
        )

    async def waitForEvent(
        self, event: str, predicate: Callable[[Any], bool] = None, timeout: int = None
    ) -> Any:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        wait_helper = WaitHelper(self._loop)
        wait_helper.reject_on_timeout(
            timeout, f'Timeout while waiting for event "${event}"'
        )
        if event != Page.Events.Crash:
            wait_helper.reject_on_event(self, Page.Events.Crash, Error("Page crashed"))
        if event != Page.Events.Close:
            wait_helper.reject_on_event(self, Page.Events.Close, Error("Page closed"))
        return await wait_helper.wait_for_event(self, event, predicate)

    async def goBack(
        self,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("goBack", locals_to_params(locals()))
        )

    async def goForward(
        self,
        timeout: int = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("goForward", locals_to_params(locals()))
        )

    async def emulateMedia(
        self,
        media: Literal["print", "screen"] = None,
        colorScheme: ColorScheme = None,
    ) -> None:
        await self._channel.send("emulateMedia", locals_to_params(locals()))

    async def setViewportSize(self, width: int, height: int) -> None:
        self._viewport_size = dict(width=width, height=height)
        await self._channel.send(
            "setViewportSize", dict(viewportSize=locals_to_params(locals()))
        )

    def viewportSize(self) -> Optional[IntSize]:
        return self._viewport_size

    async def bringToFront(self) -> None:
        await self._channel.send("bringToFront")

    async def addInitScript(
        self, source: str = None, path: Union[str, Path] = None
    ) -> None:
        if path:
            with open(path, "r") as file:
                source = file.read()
        if not isinstance(source, str):
            raise Error("Either path or source parameter must be specified")
        await self._channel.send("addInitScript", dict(source=source))

    async def route(self, url: URLMatch, handler: RouteHandler) -> None:
        self._routes.append(RouteHandlerEntry(URLMatcher(url), handler))
        if len(self._routes) == 1:
            await self._channel.send(
                "setNetworkInterceptionEnabled", dict(enabled=True)
            )

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandler] = None
    ) -> None:
        self._routes = list(
            filter(
                lambda r: r.matcher.match != url or (handler and r.handler != handler),
                self._routes,
            )
        )
        if len(self._routes) == 0:
            await self._channel.send(
                "setNetworkInterceptionEnabled", dict(enabled=False)
            )

    async def screenshot(
        self,
        timeout: int = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        fullPage: bool = None,
        clip: FloatRect = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        encoded_binary = await self._channel.send("screenshot", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            with open(path, "wb") as fd:
                fd.write(decoded_binary)
        return decoded_binary

    async def title(self) -> str:
        return await self._main_frame.title()

    async def close(self, runBeforeUnload: bool = None) -> None:
        try:
            await self._channel.send("close", locals_to_params(locals()))
            if self._owned_context:
                await self._owned_context.close()
        except Exception as e:
            if not is_safe_close_error(e):
                raise e

    def isClosed(self) -> bool:
        return self._is_closed

    async def click(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
        delay: int = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.click(**locals_to_params(locals()))

    async def dblclick(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
        delay: int = None,
        button: MouseButton = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.dblclick(**locals_to_params(locals()))

    async def tap(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.tap(**locals_to_params(locals()))

    async def fill(
        self, selector: str, value: str, timeout: int = None, noWaitAfter: bool = None
    ) -> None:
        return await self._main_frame.fill(**locals_to_params(locals()))

    async def focus(self, selector: str, timeout: int = None) -> None:
        return await self._main_frame.focus(**locals_to_params(locals()))

    async def textContent(self, selector: str, timeout: int = None) -> Optional[str]:
        return await self._main_frame.textContent(**locals_to_params(locals()))

    async def innerText(self, selector: str, timeout: int = None) -> str:
        return await self._main_frame.innerText(**locals_to_params(locals()))

    async def innerHTML(self, selector: str, timeout: int = None) -> str:
        return await self._main_frame.innerHTML(**locals_to_params(locals()))

    async def getAttribute(
        self, selector: str, name: str, timeout: int = None
    ) -> Optional[str]:
        return await self._main_frame.getAttribute(**locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: MousePosition = None,
        timeout: int = None,
        force: bool = None,
    ) -> None:
        return await self._main_frame.hover(**locals_to_params(locals()))

    async def selectOption(
        self,
        selector: str,
        values: ValuesToSelect,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> List[str]:
        params = locals_to_params(locals())
        if "values" not in params:
            params["values"] = None
        return await self._main_frame.selectOption(**params)

    async def setInputFiles(
        self,
        selector: str,
        files: Union[str, FilePayload, List[str], List[FilePayload]],
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.setInputFiles(**locals_to_params(locals()))

    async def type(
        self,
        selector: str,
        text: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.type(**locals_to_params(locals()))

    async def press(
        self,
        selector: str,
        key: str,
        delay: int = None,
        timeout: int = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.press(**locals_to_params(locals()))

    async def check(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.check(**locals_to_params(locals()))

    async def uncheck(
        self,
        selector: str,
        timeout: int = None,
        force: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.uncheck(**locals_to_params(locals()))

    async def waitForTimeout(self, timeout: int) -> None:
        await self._main_frame.waitForTimeout(timeout)

    async def waitForFunction(
        self,
        expression: str,
        arg: Serializable = None,
        force_expr: bool = None,
        timeout: int = None,
        polling: Union[int, Literal["raf"]] = None,
    ) -> JSHandle:
        if not is_function_body(expression):
            force_expr = True
        return await self._main_frame.waitForFunction(**locals_to_params(locals()))

    @property
    def workers(self) -> List["Worker"]:
        return self._workers.copy()

    async def pdf(
        self,
        scale: int = None,
        displayHeaderFooter: bool = None,
        headerTemplate: str = None,
        footerTemplate: str = None,
        printBackground: bool = None,
        landscape: bool = None,
        pageRanges: str = None,
        format: str = None,
        width: Union[str, float] = None,
        height: Union[str, float] = None,
        preferCSSPageSize: bool = None,
        margin: PdfMargins = None,
        path: Union[str, Path] = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        encoded_binary = await self._channel.send("pdf", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            with open(path, "wb") as fd:
                fd.write(decoded_binary)
        return decoded_binary

    @property
    def video(
        self,
    ) -> Optional[Video]:
        context_options = self._browser_context._options
        if "recordVideo" not in context_options:
            return None
        if not self._video:
            self._video = Video(self)
            if "videoRelativePath" in self._initializer:
                self._video._set_relative_path(self._initializer["videoRelativePath"])
        return self._video

    def expect_event(
        self,
        event: str,
        predicate: Callable[[Any], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl:
        return EventContextManagerImpl(self.waitForEvent(event, predicate, timeout))

    def expect_console_message(
        self,
        predicate: Callable[[ConsoleMessage], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return EventContextManagerImpl(self.waitForEvent("console", predicate, timeout))

    def expect_dialog(
        self,
        predicate: Callable[[Dialog], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Dialog]:
        return EventContextManagerImpl(self.waitForEvent("dialog", predicate, timeout))

    def expect_download(
        self,
        predicate: Callable[[Download], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Download]:
        return EventContextManagerImpl(
            self.waitForEvent("download", predicate, timeout)
        )

    def expect_file_chooser(
        self,
        predicate: Callable[[FileChooser], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[FileChooser]:
        return EventContextManagerImpl(
            self.waitForEvent("filechooser", predicate, timeout)
        )

    def expect_load_state(
        self,
        state: DocumentLoadState = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Optional[Response]]:
        return EventContextManagerImpl(self.waitForLoadState(state, timeout))

    def expect_navigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Optional[Response]]:
        return EventContextManagerImpl(self.waitForNavigation(url, waitUntil, timeout))

    def expect_popup(
        self,
        predicate: Callable[["Page"], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl["Page"]:
        return EventContextManagerImpl(self.waitForEvent("popup", predicate, timeout))

    def expect_request(
        self,
        url: URLMatch = None,
        predicate: Callable[[Request], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Request]:
        return EventContextManagerImpl(self.waitForRequest(url, predicate, timeout))

    def expect_response(
        self,
        url: URLMatch = None,
        predicate: Callable[[Request], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl[Response]:
        return EventContextManagerImpl(self.waitForResponse(url, predicate, timeout))

    def expect_worker(
        self,
        predicate: Callable[["Worker"], bool] = None,
        timeout: int = None,
    ) -> EventContextManagerImpl["Worker"]:
        return EventContextManagerImpl(self.waitForEvent("worker", predicate, timeout))


class Worker(ChannelOwner):
    Events = SimpleNamespace(Close="close")

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on("close", lambda _: self._on_close())
        self._page: Optional[Page] = None
        self._context: Optional["BrowserContext"] = None

    def _on_close(self) -> None:
        if self._page:
            self._page._workers.remove(self)
        if self._context:
            self._context._service_workers.remove(self)
        self.emit(Worker.Events.Close, self)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def evaluate(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
    ) -> Any:
        if not is_function_body(expression):
            force_expr = True
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
    ) -> JSHandle:
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )


class BindingCall(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def call(self, func: Callable) -> None:
        try:
            frame = from_channel(self._initializer["frame"])
            source = dict(context=frame._page.context, page=frame._page, frame=frame)
            if self._initializer.get("handle"):
                result = func(source, from_channel(self._initializer["handle"]))
            else:
                func_args = list(map(parse_result, self._initializer["args"]))
                result = func(source, *func_args)
            if asyncio.isfuture(result):
                result = await result
            await self._channel.send("resolve", dict(result=serialize_argument(result)))
        except Exception as e:
            tb = sys.exc_info()[2]
            asyncio.create_task(
                self._channel.send("reject", dict(error=serialize_error(e, tb)))
            )
