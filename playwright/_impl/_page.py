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
import inspect
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Pattern,
    Union,
    cast,
)

from playwright._impl._accessibility import Accessibility
from playwright._impl._api_structures import (
    AriaRole,
    FilePayload,
    FloatRect,
    PdfMargins,
    Position,
    ViewportSize,
)
from playwright._impl._api_types import Error
from playwright._impl._artifact import Artifact
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._download import Download
from playwright._impl._element_handle import ElementHandle
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._file_chooser import FileChooser
from playwright._impl._frame import Frame
from playwright._impl._har_router import HarRouter
from playwright._impl._helper import (
    ColorScheme,
    DocumentLoadState,
    ForcedColors,
    HarMode,
    KeyboardModifier,
    MouseButton,
    ReducedMotion,
    RouteFromHarNotFoundPolicy,
    RouteHandler,
    RouteHandlerCallback,
    TimeoutSettings,
    URLMatch,
    URLMatcher,
    URLMatchRequest,
    URLMatchResponse,
    async_readfile,
    async_writefile,
    is_safe_close_error,
    locals_to_params,
    make_dirs_for_file,
    serialize_error,
)
from playwright._impl._input import Keyboard, Mouse, Touchscreen
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl._network import Request, Response, Route, serialize_headers
from playwright._impl._video import Video
from playwright._impl._wait_helper import WaitHelper

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._fetch import APIRequestContext
    from playwright._impl._locator import FrameLocator, Locator
    from playwright._impl._network import WebSocket


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
        self._browser_context = cast("BrowserContext", parent)
        self.accessibility = Accessibility(self._channel)
        self.keyboard = Keyboard(self._channel)
        self.mouse = Mouse(self._channel)
        self.touchscreen = Touchscreen(self._channel)

        self._main_frame: Frame = from_channel(initializer["mainFrame"])
        self._main_frame._page = self
        self._frames = [self._main_frame]
        self._viewport_size: Optional[ViewportSize] = initializer.get("viewportSize")
        self._is_closed = False
        self._workers: List["Worker"] = []
        self._bindings: Dict[str, Any] = {}
        self._routes: List[RouteHandler] = []
        self._owned_context: Optional["BrowserContext"] = None
        self._timeout_settings: TimeoutSettings = TimeoutSettings(
            self._browser_context._timeout_settings
        )
        self._video: Optional[Video] = None
        self._opener = cast("Page", from_nullable_channel(initializer.get("opener")))

        self._channel.on(
            "bindingCall",
            lambda params: self._on_binding(from_channel(params["binding"])),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._channel.on("crash", lambda _: self._on_crash())
        self._channel.on("download", lambda params: self._on_download(params))
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
        self._channel.on(
            "route",
            lambda params: asyncio.create_task(
                self._on_route(from_channel(params["route"]))
            ),
        )
        self._channel.on("video", lambda params: self._on_video(params))
        self._channel.on(
            "webSocket",
            lambda params: self.emit(
                Page.Events.WebSocket, from_channel(params["webSocket"])
            ),
        )
        self._channel.on(
            "worker", lambda params: self._on_worker(from_channel(params["worker"]))
        )
        self._closed_or_crashed_future: asyncio.Future = asyncio.Future()
        self.on(
            Page.Events.Close,
            lambda _: self._closed_or_crashed_future.set_result(True)
            if not self._closed_or_crashed_future.done()
            else None,
        )
        self.on(
            Page.Events.Crash,
            lambda _: self._closed_or_crashed_future.set_result(True)
            if not self._closed_or_crashed_future.done()
            else None,
        )

        self._set_event_to_subscription_mapping(
            {
                Page.Events.Console: "console",
                Page.Events.Dialog: "dialog",
                Page.Events.Request: "request",
                Page.Events.Response: "response",
                Page.Events.RequestFinished: "requestFinished",
                Page.Events.RequestFailed: "requestFailed",
                Page.Events.FileChooser: "fileChooser",
            }
        )

    def __repr__(self) -> str:
        return f"<Page url={self.url!r}>"

    def _on_frame_attached(self, frame: Frame) -> None:
        frame._page = self
        self._frames.append(frame)
        self.emit(Page.Events.FrameAttached, frame)

    def _on_frame_detached(self, frame: Frame) -> None:
        self._frames.remove(frame)
        frame._detached = True
        self.emit(Page.Events.FrameDetached, frame)

    async def _on_route(self, route: Route) -> None:
        route._context = self.context
        route_handlers = self._routes.copy()
        for route_handler in route_handlers:
            if not route_handler.matches(route.request.url):
                continue
            if route_handler.will_expire:
                self._routes.remove(route_handler)
            try:
                handled = await route_handler.handle(route)
            finally:
                if len(self._routes) == 0:
                    asyncio.create_task(
                        self._connection.wrap_api_call(
                            lambda: self._update_interception_patterns(), True
                        )
                    )
            if handled:
                return
        await self._browser_context._on_route(route)

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
        if self in self._browser_context._pages:
            self._browser_context._pages.remove(self)
        if self in self._browser_context._background_pages:
            self._browser_context._background_pages.remove(self)
        self.emit(Page.Events.Close, self)

    def _on_crash(self) -> None:
        self.emit(Page.Events.Crash, self)

    def _on_download(self, params: Any) -> None:
        url = params["url"]
        suggested_filename = params["suggestedFilename"]
        artifact = cast(Artifact, from_channel(params["artifact"]))
        self.emit(
            Page.Events.Download, Download(self, url, suggested_filename, artifact)
        )

    def _on_video(self, params: Any) -> None:
        artifact = from_channel(params["artifact"])
        cast(Video, self.video)._artifact_ready(artifact)

    @property
    def context(self) -> "BrowserContext":
        return self._browser_context

    async def opener(self) -> Optional["Page"]:
        if self._opener and self._opener.is_closed():
            return None
        return self._opener

    @property
    def main_frame(self) -> Frame:
        return self._main_frame

    def frame(self, name: str = None, url: URLMatch = None) -> Optional[Frame]:
        matcher = (
            URLMatcher(self._browser_context._options.get("baseURL"), url)
            if url
            else None
        )
        for frame in self._frames:
            if name and frame.name == name:
                return frame
            if url and matcher and matcher.matches(frame.url):
                return frame
        return None

    @property
    def frames(self) -> List[Frame]:
        return self._frames.copy()

    def set_default_navigation_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_default_navigation_timeout(timeout)
        self._channel.send_no_reply(
            "setDefaultNavigationTimeoutNoReply", dict(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_default_timeout(timeout)
        self._channel.send_no_reply("setDefaultTimeoutNoReply", dict(timeout=timeout))

    async def query_selector(
        self,
        selector: str,
        strict: bool = None,
    ) -> Optional[ElementHandle]:
        return await self._main_frame.query_selector(selector, strict)

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        return await self._main_frame.query_selector_all(selector)

    async def wait_for_selector(
        self,
        selector: str,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
        strict: bool = None,
    ) -> Optional[ElementHandle]:
        return await self._main_frame.wait_for_selector(**locals_to_params(locals()))

    async def is_checked(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_checked(**locals_to_params(locals()))

    async def is_disabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_disabled(**locals_to_params(locals()))

    async def is_editable(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_editable(**locals_to_params(locals()))

    async def is_enabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_enabled(**locals_to_params(locals()))

    async def is_hidden(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_hidden(**locals_to_params(locals()))

    async def is_visible(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._main_frame.is_visible(**locals_to_params(locals()))

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        eventInit: Dict = None,
        timeout: float = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.dispatch_event(**locals_to_params(locals()))

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return await self._main_frame.evaluate(expression, arg)

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> JSHandle:
        return await self._main_frame.evaluate_handle(expression, arg)

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        strict: bool = None,
    ) -> Any:
        return await self._main_frame.eval_on_selector(
            selector, expression, arg, strict
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return await self._main_frame.eval_on_selector_all(selector, expression, arg)

    async def add_script_tag(
        self,
        url: str = None,
        path: Union[str, Path] = None,
        content: str = None,
        type: str = None,
    ) -> ElementHandle:
        return await self._main_frame.add_script_tag(**locals_to_params(locals()))

    async def add_style_tag(
        self, url: str = None, path: Union[str, Path] = None, content: str = None
    ) -> ElementHandle:
        return await self._main_frame.add_style_tag(**locals_to_params(locals()))

    async def expose_function(self, name: str, callback: Callable) -> None:
        await self.expose_binding(name, lambda source, *args: callback(*args))

    async def expose_binding(
        self, name: str, callback: Callable, handle: bool = None
    ) -> None:
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        if name in self._browser_context._bindings:
            raise Error(
                f'Function "{name}" has been already registered in the browser context'
            )
        self._bindings[name] = callback
        await self._channel.send(
            "exposeBinding", dict(name=name, needsHandle=handle or False)
        )

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        await self._channel.send(
            "setExtraHTTPHeaders", dict(headers=serialize_headers(headers))
        )

    @property
    def url(self) -> str:
        return self._main_frame.url

    async def content(self) -> str:
        return await self._main_frame.content()

    async def set_content(
        self,
        html: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> None:
        return await self._main_frame.set_content(**locals_to_params(locals()))

    async def goto(
        self,
        url: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
        referer: str = None,
    ) -> Optional[Response]:
        return await self._main_frame.goto(**locals_to_params(locals()))

    async def reload(
        self,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("reload", locals_to_params(locals()))
        )

    async def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None,
    ) -> None:
        return await self._main_frame.wait_for_load_state(**locals_to_params(locals()))

    async def wait_for_url(
        self,
        url: URLMatch,
        wait_until: DocumentLoadState = None,
        timeout: float = None,
    ) -> None:
        return await self._main_frame.wait_for_url(**locals_to_params(locals()))

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    async def go_back(
        self,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("goBack", locals_to_params(locals()))
        )

    async def go_forward(
        self,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> Optional[Response]:
        return from_nullable_channel(
            await self._channel.send("goForward", locals_to_params(locals()))
        )

    async def emulate_media(
        self,
        media: Literal["null", "print", "screen"] = None,
        colorScheme: ColorScheme = None,
        reducedMotion: ReducedMotion = None,
        forcedColors: ForcedColors = None,
    ) -> None:
        params = locals_to_params(locals())
        if "media" in params:
            params["media"] = "no-override" if params["media"] == "null" else media
        if "colorScheme" in params:
            params["colorScheme"] = (
                "no-override" if params["colorScheme"] == "null" else colorScheme
            )
        if "reducedMotion" in params:
            params["reducedMotion"] = (
                "no-override" if params["reducedMotion"] == "null" else reducedMotion
            )
        if "forcedColors" in params:
            params["forcedColors"] = (
                "no-override" if params["forcedColors"] == "null" else forcedColors
            )
        await self._channel.send("emulateMedia", params)

    async def set_viewport_size(self, viewportSize: ViewportSize) -> None:
        self._viewport_size = viewportSize
        await self._channel.send("setViewportSize", locals_to_params(locals()))

    @property
    def viewport_size(self) -> Optional[ViewportSize]:
        return self._viewport_size

    async def bring_to_front(self) -> None:
        await self._channel.send("bringToFront")

    async def add_init_script(
        self, script: str = None, path: Union[str, Path] = None
    ) -> None:
        if path:
            script = (await async_readfile(path)).decode()
        if not isinstance(script, str):
            raise Error("Either path or script parameter must be specified")
        await self._channel.send("addInitScript", dict(source=script))

    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: int = None
    ) -> None:
        self._routes.insert(
            0,
            RouteHandler(
                URLMatcher(self._browser_context._options.get("baseURL"), url),
                handler,
                True if self._dispatcher_fiber else False,
                times,
            ),
        )
        await self._update_interception_patterns()

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback] = None
    ) -> None:
        self._routes = list(
            filter(
                lambda r: r.matcher.match != url or (handler and r.handler != handler),
                self._routes,
            )
        )
        await self._update_interception_patterns()

    async def route_from_har(
        self,
        har: Union[Path, str],
        url: Union[Pattern[str], str] = None,
        not_found: RouteFromHarNotFoundPolicy = None,
        update: bool = None,
        update_content: Literal["attach", "embed"] = None,
        update_mode: HarMode = None,
    ) -> None:
        if update:
            await self._browser_context._record_into_har(
                har=har,
                page=self,
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
        await router.add_page_route(self)

    async def _update_interception_patterns(self) -> None:
        patterns = RouteHandler.prepare_interception_patterns(self._routes)
        await self._channel.send(
            "setNetworkInterceptionPatterns", {"patterns": patterns}
        )

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, Path] = None,
        quality: int = None,
        omitBackground: bool = None,
        fullPage: bool = None,
        clip: FloatRect = None,
        animations: Literal["allow", "disabled"] = None,
        caret: Literal["hide", "initial"] = None,
        scale: Literal["css", "device"] = None,
        mask: List["Locator"] = None,
        mask_color: str = None,
    ) -> bytes:
        params = locals_to_params(locals())
        if "path" in params:
            del params["path"]
        if "mask" in params:
            params["mask"] = list(
                map(
                    lambda locator: (
                        {
                            "frame": locator._frame._channel,
                            "selector": locator._selector,
                        }
                    ),
                    params["mask"],
                )
            )
        encoded_binary = await self._channel.send("screenshot", params)
        decoded_binary = base64.b64decode(encoded_binary)
        if path:
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    async def title(self) -> str:
        return await self._main_frame.title()

    async def close(self, runBeforeUnload: bool = None) -> None:
        try:
            await self._channel.send("close", locals_to_params(locals()))
            if self._owned_context:
                await self._owned_context.close()
        except Exception as e:
            if not is_safe_close_error(e) and not runBeforeUnload:
                raise e

    def is_closed(self) -> bool:
        return self._is_closed

    async def click(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.click(**locals_to_params(locals()))

    async def dblclick(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.dblclick(**locals_to_params(locals()))

    async def tap(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.tap(**locals_to_params(locals()))

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        force: bool = None,
    ) -> None:
        return await self._main_frame.fill(**locals_to_params(locals()))

    def locator(
        self,
        selector: str,
        has_text: Union[str, Pattern[str]] = None,
        has_not_text: Union[str, Pattern[str]] = None,
        has: "Locator" = None,
        has_not: "Locator" = None,
    ) -> "Locator":
        return self._main_frame.locator(
            selector,
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_alt_text(text, exact=exact)

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_label(text, exact=exact)

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_placeholder(text, exact=exact)

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self._main_frame.get_by_role(
            role,
            checked=checked,
            disabled=disabled,
            expanded=expanded,
            includeHidden=includeHidden,
            level=level,
            name=name,
            pressed=pressed,
            selected=selected,
            exact=exact,
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self._main_frame.get_by_test_id(testId)

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_text(text, exact=exact)

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self._main_frame.get_by_title(text, exact=exact)

    def frame_locator(self, selector: str) -> "FrameLocator":
        return self.main_frame.frame_locator(selector)

    async def focus(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> None:
        return await self._main_frame.focus(**locals_to_params(locals()))

    async def text_content(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._main_frame.text_content(**locals_to_params(locals()))

    async def inner_text(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._main_frame.inner_text(**locals_to_params(locals()))

    async def inner_html(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._main_frame.inner_html(**locals_to_params(locals()))

    async def get_attribute(
        self, selector: str, name: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._main_frame.get_attribute(**locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.hover(**locals_to_params(locals()))

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        sourcePosition: Position = None,
        targetPosition: Position = None,
        force: bool = None,
        noWaitAfter: bool = None,
        timeout: float = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.drag_and_drop(**locals_to_params(locals()))

    async def select_option(
        self,
        selector: str,
        value: Union[str, List[str]] = None,
        index: Union[int, List[int]] = None,
        label: Union[str, List[str]] = None,
        element: Union["ElementHandle", List["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        strict: bool = None,
    ) -> List[str]:
        params = locals_to_params(locals())
        return await self._main_frame.select_option(**params)

    async def input_value(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        params = locals_to_params(locals())
        return await self._main_frame.input_value(**params)

    async def set_input_files(
        self,
        selector: str,
        files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]],
        timeout: float = None,
        strict: bool = None,
        noWaitAfter: bool = None,
    ) -> None:
        return await self._main_frame.set_input_files(**locals_to_params(locals()))

    async def type(
        self,
        selector: str,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.type(**locals_to_params(locals()))

    async def press(
        self,
        selector: str,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
    ) -> None:
        return await self._main_frame.press(**locals_to_params(locals()))

    async def check(
        self,
        selector: str,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.check(**locals_to_params(locals()))

    async def uncheck(
        self,
        selector: str,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        return await self._main_frame.uncheck(**locals_to_params(locals()))

    async def wait_for_timeout(self, timeout: float) -> None:
        await self._main_frame.wait_for_timeout(timeout)

    async def wait_for_function(
        self,
        expression: str,
        arg: Serializable = None,
        timeout: float = None,
        polling: Union[float, Literal["raf"]] = None,
    ) -> JSHandle:
        return await self._main_frame.wait_for_function(**locals_to_params(locals()))

    @property
    def workers(self) -> List["Worker"]:
        return self._workers.copy()

    @property
    def request(self) -> "APIRequestContext":
        return self.context.request

    async def pause(self) -> None:
        default_navigation_timeout = (
            self._browser_context._timeout_settings.default_navigation_timeout()
        )
        default_timeout = self._browser_context._timeout_settings.default_timeout()
        self._browser_context.set_default_navigation_timeout(0)
        self._browser_context.set_default_timeout(0)
        try:
            await asyncio.wait(
                [
                    asyncio.create_task(self._browser_context._pause()),
                    self._closed_or_crashed_future,
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            self._browser_context._set_default_navigation_timeout_impl(
                default_navigation_timeout
            )
            self._browser_context._set_default_timeout_impl(default_timeout)

    async def pdf(
        self,
        scale: float = None,
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
            make_dirs_for_file(path)
            await async_writefile(path, decoded_binary)
        return decoded_binary

    @property
    def video(
        self,
    ) -> Optional[Video]:
        if not self._video:
            self._video = Video(self)
        return self._video

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        return self._expect_event(
            event, predicate, timeout, f'waiting for event "{event}"'
        )

    def _expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
        log_line: str = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        wait_helper = WaitHelper(self, f"page.expect_event({event})")
        wait_helper.reject_on_timeout(
            timeout, f'Timeout {timeout}ms exceeded while waiting for event "{event}"'
        )
        if log_line:
            wait_helper.log(log_line)
        if event != Page.Events.Crash:
            wait_helper.reject_on_event(self, Page.Events.Crash, Error("Page crashed"))
        if event != Page.Events.Close:
            wait_helper.reject_on_event(self, Page.Events.Close, Error("Page closed"))
        wait_helper.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(wait_helper.result())

    def expect_console_message(
        self,
        predicate: Callable[[ConsoleMessage], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[ConsoleMessage]:
        return self.expect_event(Page.Events.Console, predicate, timeout)

    def expect_download(
        self,
        predicate: Callable[[Download], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Download]:
        return self.expect_event(Page.Events.Download, predicate, timeout)

    def expect_file_chooser(
        self,
        predicate: Callable[[FileChooser], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[FileChooser]:
        return self.expect_event(Page.Events.FileChooser, predicate, timeout)

    def expect_navigation(
        self,
        url: URLMatch = None,
        wait_until: DocumentLoadState = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Response]:
        return self.main_frame.expect_navigation(url, wait_until, timeout)

    def expect_popup(
        self,
        predicate: Callable[["Page"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl["Page"]:
        return self.expect_event(Page.Events.Popup, predicate, timeout)

    def expect_request(
        self,
        url_or_predicate: URLMatchRequest,
        timeout: float = None,
    ) -> EventContextManagerImpl[Request]:
        matcher = (
            None
            if callable(url_or_predicate)
            else URLMatcher(
                self._browser_context._options.get("baseURL"), url_or_predicate
            )
        )
        predicate = url_or_predicate if callable(url_or_predicate) else None

        def my_predicate(request: Request) -> bool:
            if matcher:
                return matcher.matches(request.url)
            if predicate:
                return predicate(request)
            return True

        trimmed_url = trim_url(url_or_predicate)
        log_line = f"waiting for request {trimmed_url}" if trimmed_url else None
        return self._expect_event(
            Page.Events.Request,
            predicate=my_predicate,
            timeout=timeout,
            log_line=log_line,
        )

    def expect_request_finished(
        self,
        predicate: Callable[["Request"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Request]:
        return self.expect_event(
            Page.Events.RequestFinished, predicate=predicate, timeout=timeout
        )

    def expect_response(
        self,
        url_or_predicate: URLMatchResponse,
        timeout: float = None,
    ) -> EventContextManagerImpl[Response]:
        matcher = (
            None
            if callable(url_or_predicate)
            else URLMatcher(
                self._browser_context._options.get("baseURL"), url_or_predicate
            )
        )
        predicate = url_or_predicate if callable(url_or_predicate) else None

        def my_predicate(response: Response) -> bool:
            if matcher:
                return matcher.matches(response.url)
            if predicate:
                return predicate(response)
            return True

        trimmed_url = trim_url(url_or_predicate)
        log_line = f"waiting for response {trimmed_url}" if trimmed_url else None
        return self._expect_event(
            Page.Events.Response,
            predicate=my_predicate,
            timeout=timeout,
            log_line=log_line,
        )

    def expect_websocket(
        self,
        predicate: Callable[["WebSocket"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl["WebSocket"]:
        return self.expect_event("websocket", predicate, timeout)

    def expect_worker(
        self,
        predicate: Callable[["Worker"], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl["Worker"]:
        return self.expect_event("worker", predicate, timeout)

    async def set_checked(
        self,
        selector: str,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
                strict=strict,
                trial=trial,
            )
        else:
            await self.uncheck(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
                strict=strict,
                trial=trial,
            )


class Worker(ChannelOwner):
    Events = SimpleNamespace(Close="close")

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on("close", lambda _: self._on_close())
        self._page: Optional[Page] = None
        self._context: Optional["BrowserContext"] = None

    def __repr__(self) -> str:
        return f"<Worker url={self.url!r}>"

    def _on_close(self) -> None:
        if self._page:
            self._page._workers.remove(self)
        if self._context:
            self._context._service_workers.remove(self)
        self.emit(Worker.Events.Close, self)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> JSHandle:
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
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
            if inspect.iscoroutine(result):
                result = await result
            await self._channel.send("resolve", dict(result=serialize_argument(result)))
        except Exception as e:
            tb = sys.exc_info()[2]
            asyncio.create_task(
                self._channel.send(
                    "reject", dict(error=dict(error=serialize_error(e, tb)))
                )
            )


def trim_url(param: Union[URLMatchRequest, URLMatchResponse]) -> Optional[str]:
    if isinstance(param, re.Pattern):
        return trim_end(param.pattern)
    if isinstance(param, str):
        return trim_end(param)
    return None


def trim_end(s: str) -> str:
    if len(s) > 50:
        return s[:50] + "\u2026"
    return s
