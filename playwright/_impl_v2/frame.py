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

"""Port of packages/playwright-core/src/client/frame.ts.

Python: the JS methods spread their options object into the params of the channel
call, and the validator drops the options that the command does not take (the
deprecated noWaitAfter of most actions). Here each parameter of the command is
passed by name, and the others are not passed.

Python: a page function is a string; isFunction is undefined (None), see the
docstring of js_handle.py. assertMaxArguments(arguments.length, n) is not ported: a
Python method takes no more arguments than its signature has.

Python: name, url, parent_frame, child_frames and page are properties, as the
generated API reads them. The Python API waits for a navigation with
expect_navigation(), a context manager around wait_for_navigation().
"""

import asyncio
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
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

from playwright._impl._api_structures import DropPayload, FilePayload, Position
from playwright._impl_v2 import network
from playwright._impl_v2.channel_owner import (
    ApiCallOptions,
    ChannelOwner,
    api_call,
    from_channel,
)
from playwright._impl_v2.client_helper import add_source_url_to_script
from playwright._impl_v2.element_handle import (
    ElementHandle,
    convert_input_files,
    convert_select_option_values,
)
from playwright._impl_v2.errors import Error
from playwright._impl_v2.event_context_manager import EventContextManagerImpl
from playwright._impl_v2.event_emitter import EventEmitter
from playwright._impl_v2.events import Events
from playwright._impl_v2.internal_structures import (
    AriaRole,
    FrameExpectOptions,
    FrameExpectResult,
)
from playwright._impl_v2.isomorphic.locator_utils import (
    get_by_alt_text_selector,
    get_by_label_selector,
    get_by_placeholder_selector,
    get_by_role_selector,
    get_by_test_id_selector,
    get_by_text_selector,
    get_by_title_selector,
)
from playwright._impl_v2.isomorphic.string_utils import js_string
from playwright._impl_v2.isomorphic.url_match import URLMatch, url_matches
from playwright._impl_v2.js_handle import (
    JSHandle,
    Serializable,
    parse_result,
    serialize_argument,
)
from playwright._impl_v2.locator import (
    ANY_FRAME_SELECTOR,
    FrameLocator,
    Locator,
    test_id_attribute_name,
)
from playwright._impl_v2.timeout_settings import NO_TIMEOUT, TimeoutSettings
from playwright._impl_v2.types import LIFECYCLE_EVENTS
from playwright._impl_v2.utils.tasks import failed
from playwright._impl_v2.waiter import Waiter
from playwright._impl_v2.web_mcp import WebMCP

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.page import Page
    from playwright._impl_v2.protocol_channels import FrameChannel, JSHandleChannel

# Python: LifecycleEvent of types.ts.
LifecycleEvent = Literal["commit", "domcontentloaded", "load", "networkidle"]

# Python: the types of the Python API options (playwright/_impl/_helper.py).
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]

# Not ported: the WaitForNavigationOptions type; wait_for_navigation() takes the
# options as parameters, and has no `signal`.


class Frame(ChannelOwner):
    _channel: "FrameChannel"

    @staticmethod
    def from_(frame: "FrameChannel") -> "Frame":
        return from_channel(frame)

    @staticmethod
    def from_nullable(frame: Optional["FrameChannel"]) -> Optional["Frame"]:
        return Frame.from_(frame) if frame else None

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.FrameInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Python: the field initializers of the class.
        self._parent_frame: Optional[Frame] = None
        self._url = ""
        self._name = ""
        self._detached = False
        # Python: a dict is the ordered Set; the values are None.
        self._child_frames: Dict[Frame, None] = {}
        self._page: Optional["Page"] = None

        self._event_emitter = EventEmitter()
        self._event_emitter.set_max_listeners(0)
        self.webmcp = WebMCP(self)
        self._parent_frame = Frame.from_nullable(initializer.get("parentFrame"))
        if self._parent_frame:
            self._parent_frame._child_frames[self] = None
        self._name = initializer["name"]
        self._url = initializer["url"]
        self._load_states: Set[str] = set(initializer["loadStates"])

        def on_loadstate(event: "channels.FrameLoadstateEvent") -> None:
            if event["add"]:
                self._load_states.add(event["add"])
                self._event_emitter.emit("loadstate", event["add"])
            if event["remove"]:
                self._load_states.discard(event["remove"])
            if not self._parent_frame and event["add"] == "load" and self._page:
                self._page.emit(Events.Page.Load, self._page)
                self._page.context.emit(Events.BrowserContext.PageLoad, self._page)
            if (
                not self._parent_frame
                and event["add"] == "domcontentloaded"
                and self._page
            ):
                self._page.emit(Events.Page.DOMContentLoaded, self._page)

        self._channel.onLoadstate(on_loadstate)

        def on_navigated(event: "channels.FrameNavigatedEvent") -> None:
            self._url = event["url"]
            self._name = event["name"]
            # Main frame navigation destroys all execution contexts in the page,
            # erase the bindings backing the functions passed to evaluate().
            if not self._parent_frame and event["newDocument"] and self._page:
                self._page._erase_evaluate_callbacks()
            self._event_emitter.emit("navigated", event)
            if not event["error"] and self._page:
                self._page.emit(Events.Page.FrameNavigated, self)
                self._page.context.emit(Events.BrowserContext.FrameNavigated, self)

        self._channel.onNavigated(on_navigated)

    @property
    def page(self) -> "Page":
        # Python: `this._page!`.
        return cast("Page", self._page)

    def _timeout(self, timeout: Optional[float]) -> float:
        timeout_settings = (
            self._page._timeout_settings if self._page else TimeoutSettings()
        )
        return timeout_settings.timeout(timeout)

    def _navigation_timeout(self, timeout: Optional[float]) -> float:
        timeout_settings = (
            self._page._timeout_settings if self._page else TimeoutSettings()
        )
        return timeout_settings.navigation_timeout(timeout)

    async def goto(
        self,
        url: str,
        timeout: Optional[float],
        wait_until: Optional[LifecycleEvent],
        referer: Optional[str],
    ) -> Optional["network.Response"]:
        # Python: the message names the Python option, wait_until, as the tests
        # assert.
        wait_until = verify_load_state(
            "wait_until", "load" if wait_until is None else wait_until
        )
        return network.Response.from_nullable(
            (
                await self._channel.goto(
                    url=url,
                    waitUntil=wait_until,
                    referer=referer,
                    timeout=self._navigation_timeout(timeout),
                )
            )["response"]
        )

    def _setup_navigation_waiter(self, timeout: Optional[float]) -> Waiter:
        # Python: `this._page!`.
        page = cast("Page", self._page)
        waiter = Waiter(page, "")
        if page.is_closed():
            waiter.reject_immediately(page._close_error_with_reason())
        waiter.reject_on_event(
            page, Events.Page.Close, lambda: page._close_error_with_reason()
        )
        waiter.reject_on_event(
            page, Events.Page.Crash, Error("Navigation failed because page crashed!")
        )
        waiter.reject_on_event(
            page,
            Events.Page.FrameDetached,
            Error("Navigating frame was detached!"),
            lambda frame: frame is self,
        )
        timeout_options = page._timeout_settings.navigation_timeout(timeout)
        # Python: js_string() prints the number as JS does (30000, not 30000.0).
        waiter.reject_on_timeout(
            timeout_options, f"Timeout {js_string(timeout_options)}ms exceeded."
        )
        return waiter

    @api_call(title="Wait for navigation")
    def wait_for_navigation(
        self,
        url: Optional[URLMatch],
        wait_until: Optional[LifecycleEvent],
        timeout: Optional[float],
    ) -> Awaitable[Optional["network.Response"]]:
        # Python: a plain def. The waiter and its listeners are set up at the call, as
        # the JS async function sets them up before its first await; the result is
        # the wait. The message names the Python option, wait_until.
        wait_until = verify_load_state(
            "wait_until", "load" if wait_until is None else wait_until
        )
        waiter = self._setup_navigation_waiter(timeout)

        to_url = f' to "{url}"' if isinstance(url, str) else ""
        waiter.log(f'waiting for navigation{to_url} until "{wait_until}"')

        def navigated_predicate(event: "channels.FrameNavigatedEvent") -> bool:
            # Any failed navigation results in a rejection.
            if event["error"]:
                return True
            waiter.log(f'  navigated to "{event["url"]}"')
            return url_matches(
                self._page.context._options.get("baseURL") if self._page else None,
                event["url"],
                url,
            )

        wait = waiter.wait_for_event(
            self._event_emitter, "navigated", navigated_predicate
        )

        async def rest() -> Optional["network.Response"]:
            navigated_event: "channels.FrameNavigatedEvent" = await wait
            if navigated_event["error"]:
                e = Error(navigated_event["error"])
                e._stack = ""
                await waiter.wait_for_promise(failed(e))

            if wait_until not in self._load_states:

                def loadstate_predicate(s: str) -> bool:
                    waiter.log(f'  "{s}" event fired')
                    return s == wait_until

                await waiter.wait_for_event(
                    self._event_emitter, "loadstate", loadstate_predicate
                )

            new_document = navigated_event["newDocument"]
            request = (
                network.Request.from_nullable(new_document.get("request"))
                if new_document
                else None
            )
            response = (
                await waiter.wait_for_promise(
                    request._final_request()._internal_response()
                )
                if request
                else None
            )
            waiter.dispose()
            return response

        return rest()

    @api_call(title="Wait for load state")
    async def wait_for_load_state(
        self,
        state: Optional[LifecycleEvent],
        timeout: Optional[float],
    ) -> None:
        # Python: None is the default 'load'.
        state = verify_load_state("state", "load" if state is None else state)
        waiter = self._setup_navigation_waiter(timeout)
        try:
            if state in self._load_states:
                waiter.log(f'  not waiting, "{state}" event already fired')
                waiter.throw_if_immediately_rejected()
            else:

                def predicate(s: str) -> bool:
                    waiter.log(f'  "{s}" event fired')
                    return s == state

                await waiter.wait_for_event(self._event_emitter, "loadstate", predicate)
        finally:
            waiter.dispose()

    async def wait_for_url(
        self,
        url: URLMatch,
        wait_until: Optional[LifecycleEvent],
        timeout: Optional[float],
    ) -> None:
        # Python: waitOptions are wait_until and timeout.
        if url_matches(
            self._page.context._options.get("baseURL") if self._page else None,
            self.url,
            url,
        ):
            return await self.wait_for_load_state(state=wait_until, timeout=timeout)

        await self.wait_for_navigation(url=url, wait_until=wait_until, timeout=timeout)

    async def frame_element(self) -> ElementHandle:
        return ElementHandle.from_(
            (await self._channel.frameElement(timeout=NO_TIMEOUT))["element"]
        )

    async def evaluate_handle(self, expression: str, arg: Serializable) -> JSHandle:
        # Not ported: assertEvaluateOptions(options), and the exposeFunctions option
        # (JS only), with which the argument is serialize_argument_with_callbacks().
        serialized_arg = serialize_argument(arg)
        result = await self._channel.evaluateExpressionHandle(
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialized_arg,
            timeout=NO_TIMEOUT,
        )
        return JSHandle.from_(result["handle"])

    async def evaluate(self, expression: str, arg: Serializable) -> Any:
        # Not ported: assertEvaluateOptions(options), and the exposeFunctions option
        # (JS only), with which the argument is serialize_argument_with_callbacks().
        serialized_arg = serialize_argument(arg)
        result = await self._channel.evaluateExpression(
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialized_arg,
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def _evaluate_expose_utility_script(
        self, expression: str, arg: Serializable
    ) -> Any:
        result = await self._channel.evaluateExpression(
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def query_selector(
        self, selector: str, strict: Optional[bool]
    ) -> Optional[ElementHandle]:
        result = await self._channel.querySelector(
            selector=selector, strict=strict, timeout=NO_TIMEOUT
        )
        return ElementHandle.from_nullable(result["element"])

    async def wait_for_selector(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
        state: Optional[Literal["attached", "detached", "hidden", "visible"]],
    ) -> Optional[ElementHandle]:
        # Not ported: the errors for options.visibility and options.waitFor, the
        # options of old JS versions. The Python API has no such options.
        result = await self._channel.waitForSelector(
            selector=selector,
            strict=strict,
            state=state,
            omitReturnValue=None,
            timeout=self._timeout(timeout),
        )
        return ElementHandle.from_nullable(result["element"])

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        event_init: Optional[Dict],
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> None:
        await self._channel.dispatchEvent(
            selector=selector,
            strict=strict,
            type=type,
            eventInit=serialize_argument(event_init),
            timeout=self._timeout(timeout),
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable,
        strict: Optional[bool],
    ) -> Any:
        result = await self._channel.evalOnSelector(
            selector=selector,
            # Python: the docs give $eval() a strict option. The JS client drops it
            # (and assertMaxArguments() rejects it); the Python API sends it.
            strict=strict,
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable,
    ) -> Any:
        result = await self._channel.evalOnSelectorAll(
            selector=selector,
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialize_argument(arg),
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        result = await self._channel.querySelectorAll(
            selector=selector, timeout=NO_TIMEOUT
        )
        return [ElementHandle.from_(e) for e in result["elements"]]

    async def _query_count(self, selector: str) -> int:
        return (await self._channel.queryCount(selector=selector, timeout=NO_TIMEOUT))[
            "value"
        ]

    async def content(self, include_shadow: Optional[bool]) -> str:
        return (
            await self._channel.content(
                includeShadow=include_shadow, timeout=NO_TIMEOUT
            )
        )["value"]

    async def set_content(
        self,
        html: str,
        timeout: Optional[float],
        wait_until: Optional[LifecycleEvent],
    ) -> None:
        # Python: the message names the Python option, wait_until.
        wait_until = verify_load_state(
            "wait_until", "load" if wait_until is None else wait_until
        )
        await self._channel.setContent(
            html=html,
            waitUntil=wait_until,
            timeout=self._navigation_timeout(timeout),
        )

    @property
    def name(self) -> str:
        return self._name or ""

    @property
    def url(self) -> str:
        return self._url

    @property
    def parent_frame(self) -> Optional["Frame"]:
        return self._parent_frame

    @property
    def child_frames(self) -> List["Frame"]:
        return list(self._child_frames)

    def is_detached(self) -> bool:
        return self._detached

    async def add_script_tag(
        self,
        url: Optional[str],
        path: Optional[Union[str, Path]],
        content: Optional[str],
        type: Optional[str],
    ) -> ElementHandle:
        # Python: the options are parameters, so `copy` is the content.
        if path:
            content = (await _read_file(path)).decode("utf-8", "replace")
            content = add_source_url_to_script(content, path)
        return ElementHandle.from_(
            (
                await self._channel.addScriptTag(
                    url=url, content=content, type=type, timeout=NO_TIMEOUT
                )
            )["element"]
        )

    async def add_style_tag(
        self,
        url: Optional[str],
        path: Optional[Union[str, Path]],
        content: Optional[str],
    ) -> ElementHandle:
        # Python: the options are parameters, so `copy` is the content.
        if path:
            content = (await _read_file(path)).decode("utf-8", "replace")
            content += "/*# sourceURL=" + str(path).replace("\n", "") + "*/"
        return ElementHandle.from_(
            (
                await self._channel.addStyleTag(
                    url=url, content=content, timeout=NO_TIMEOUT
                )
            )["element"]
        )

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
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
        # Python: Frame.click() of the Python API has no steps option, and
        # Locator.click() passes it.
        steps: Optional[int] = None,
    ) -> None:
        return await self._channel.click(
            selector=selector,
            strict=strict,
            force=force,
            scroll=scroll,
            noWaitAfter=no_wait_after,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            clickCount=click_count,
            trial=trial,
            steps=steps,
            timeout=self._timeout(timeout),
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
        scroll: Optional[Literal["auto", "none"]],
        # Python: Frame.dblclick() of the Python API has no steps option, and
        # Locator.dblclick() passes it.
        steps: Optional[int] = None,
    ) -> None:
        return await self._channel.dblclick(
            selector=selector,
            strict=strict,
            force=force,
            scroll=scroll,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            trial=trial,
            steps=steps,
            timeout=self._timeout(timeout),
        )

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        source_position: Optional[Position],
        target_position: Optional[Position],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        strict: Optional[bool],
        timeout: Optional[float],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._channel.dragAndDrop(
            source=source,
            target=target,
            force=force,
            scroll=scroll,
            trial=trial,
            sourcePosition=source_position,
            targetPosition=target_position,
            strict=strict,
            steps=steps,
            timeout=self._timeout(timeout),
        )

    async def _drop(
        self,
        selector: str,
        payload: DropPayload,
        strict: Optional[bool],
        position: Optional[Position],
        timeout: Optional[float],
    ) -> None:
        # Python: fileParams are the three params below.
        payloads = None
        local_paths = None
        streams = None
        files = payload.get("files")
        if files is not None:
            converted = await convert_input_files(files, self.page.context)
            if converted.get("localDirectory") or converted.get("directoryStream"):
                raise Error(
                    "Dropping a directory is not supported — pass individual files."
                )
            payloads = converted.get("payloads")
            local_paths = converted.get("localPaths")
            streams = converted.get("streams")
        # Python: an empty dict is data, as an empty object is truthy.
        data = payload.get("data")
        data_array: Optional[List["channels.FrameDropParamsData"]] = (
            [
                {"mimeType": mime_type, "value": value}
                for mime_type, value in data.items()
            ]
            if data is not None
            else None
        )
        await self._channel.drop(
            selector=selector,
            payloads=payloads,
            localPaths=local_paths,
            streams=streams,
            data=data_array,
            strict=strict,
            position=position,
            timeout=self._timeout(timeout),
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
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._channel.tap(
            selector=selector,
            strict=strict,
            force=force,
            scroll=scroll,
            modifiers=modifiers,
            position=position,
            trial=trial,
            timeout=self._timeout(timeout),
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
        return await self._channel.fill(
            selector=selector,
            strict=strict,
            value=value,
            force=force,
            timeout=self._timeout(timeout),
        )

    async def _highlight(self, selector: str, style: Optional[str] = None) -> None:
        return await self._channel.highlight(
            selector=selector, style=style, timeout=NO_TIMEOUT
        )

    async def _hide_highlight(self, selector: str) -> None:
        return await self._channel.hideHighlight(selector=selector, timeout=NO_TIMEOUT)

    def locator(
        self,
        selector: str,
        # Python: the LocatorOptions, as separate parameters.
        has_text: Optional[Union[str, Pattern[str]]],
        has_not_text: Optional[Union[str, Pattern[str]]],
        has: Optional[Locator],
        has_not: Optional[Locator],
    ) -> Locator:
        return Locator(
            self,
            selector,
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )

    def get_by_test_id(self, test_id: Union[str, Pattern[str]]) -> Locator:
        return self.locator(
            selector=get_by_test_id_selector(test_id_attribute_name(), test_id),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            selector=get_by_alt_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            selector=get_by_label_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            selector=get_by_placeholder_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            selector=get_by_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            selector=get_by_title_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_role(
        self,
        role: AriaRole,
        # Python: the ByRoleOptions, as separate parameters.
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
    ) -> Locator:
        return self.locator(
            selector=get_by_role_selector(
                role,
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
            ),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def frame_locator(self, selector: Optional[str]) -> FrameLocator:
        return FrameLocator(self, ANY_FRAME_SELECTOR if selector is None else selector)

    async def focus(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> None:
        await self._channel.focus(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )

    async def text_content(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> Optional[str]:
        value = (
            await self._channel.textContent(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]
        # Python: an undefined value is None, as null is.
        return value

    async def inner_text(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> str:
        return (
            await self._channel.innerText(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def inner_html(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> str:
        return (
            await self._channel.innerHTML(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def get_attribute(
        self,
        selector: str,
        name: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> Optional[str]:
        value = (
            await self._channel.getAttribute(
                selector=selector,
                strict=strict,
                name=name,
                timeout=self._timeout(timeout),
            )
        )["value"]
        # Python: an undefined value is None, as null is.
        return value

    async def input_value(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> str:
        return (
            await self._channel.inputValue(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def is_checked(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        return (
            await self._channel.isChecked(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def is_disabled(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        return (
            await self._channel.isDisabled(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def is_editable(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        return (
            await self._channel.isEditable(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def is_enabled(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        return (
            await self._channel.isEnabled(
                selector=selector, strict=strict, timeout=self._timeout(timeout)
            )
        )["value"]

    async def is_hidden(self, selector: str, strict: Optional[bool]) -> bool:
        # Python: the Python API has no timeout here (it is deprecated and ignored).
        return (
            await self._channel.isHidden(
                selector=selector, strict=strict, timeout=NO_TIMEOUT
            )
        )["value"]

    async def is_visible(self, selector: str, strict: Optional[bool]) -> bool:
        # Python: the Python API has no timeout here (it is deprecated and ignored).
        return (
            await self._channel.isVisible(
                selector=selector, strict=strict, timeout=NO_TIMEOUT
            )
        )["value"]

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
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.hover(
            selector=selector,
            strict=strict,
            force=force,
            scroll=scroll,
            modifiers=modifiers,
            position=position,
            trial=trial,
            timeout=self._timeout(timeout),
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
        strict: Optional[bool],
        force: Optional[bool],
    ) -> List[str]:
        converted = convert_select_option_values(value, index, label, element)
        return (
            await self._channel.selectOption(
                selector=selector,
                elements=converted.get("elements"),
                options=converted.get("options"),
                strict=strict,
                force=force,
                timeout=self._timeout(timeout),
            )
        )["values"]

    async def set_input_files(
        self,
        selector: str,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        strict: Optional[bool],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        converted = await convert_input_files(files, self.page.context)
        await self._channel.setInputFiles(
            selector=selector,
            payloads=converted.get("payloads"),
            localDirectory=converted.get("localDirectory"),
            directoryStream=converted.get("directoryStream"),
            localPaths=converted.get("localPaths"),
            streams=converted.get("streams"),
            strict=strict,
            timeout=self._timeout(timeout),
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: Optional[float],
        strict: Optional[bool],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        await self._channel.type(
            selector=selector,
            text=text,
            strict=strict,
            delay=delay,
            timeout=self._timeout(timeout),
        )

    async def press(
        self,
        selector: str,
        key: str,
        delay: Optional[float],
        strict: Optional[bool],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        await self._channel.press(
            selector=selector,
            key=key,
            strict=strict,
            delay=delay,
            noWaitAfter=no_wait_after,
            timeout=self._timeout(timeout),
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
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.check(
            selector=selector,
            strict=strict,
            force=force,
            scroll=scroll,
            position=position,
            trial=trial,
            timeout=self._timeout(timeout),
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
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.uncheck(
            selector=selector,
            strict=strict,
            force=force,
            scroll=scroll,
            position=position,
            trial=trial,
            timeout=self._timeout(timeout),
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
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        if checked:
            await self.check(
                selector,
                position=position,
                timeout=timeout,
                force=force,
                no_wait_after=no_wait_after,
                strict=strict,
                trial=trial,
                scroll=scroll,
            )
        else:
            await self.uncheck(
                selector,
                position=position,
                timeout=timeout,
                force=force,
                no_wait_after=no_wait_after,
                strict=strict,
                trial=trial,
                scroll=scroll,
            )

    async def wait_for_timeout(self, timeout: float) -> None:
        await self._channel.waitForTimeout(waitTimeout=timeout, timeout=NO_TIMEOUT)

    async def wait_for_function(
        self,
        expression: str,
        arg: Serializable,
        timeout: Optional[float],
        polling: Optional[Union[float, Literal["raf"]]],
    ) -> JSHandle:
        if isinstance(polling, str):
            # Python: assert() of isomorphic/assert.ts throws an Error.
            if polling != "raf":
                raise Error("Unknown polling option: " + polling)
        result = await self._channel.waitForFunction(
            pollingInterval=None if polling == "raf" else polling,
            expression=expression,
            # Python: undefined; see the docstring of js_handle.py.
            isFunction=None,
            arg=serialize_argument(arg),
            selector=None,
            strict=None,
            timeout=self._timeout(timeout),
        )
        # Python: `result.handle!`.
        return JSHandle.from_(cast("JSHandleChannel", result["handle"]))

    async def title(self) -> str:
        return (await self._channel.title(timeout=NO_TIMEOUT))["value"]

    async def _expect(
        self,
        # Python: playwright/_impl/_assertions.py passes the selector, the options
        # and the title as separate arguments; upstream has them all in options.
        selector: Optional[str],
        expression: str,
        options: FrameExpectOptions,
        title: Optional[str],
    ) -> FrameExpectResult:
        # Not ported: the `signal` option.
        timeout = cast(float, options.get("timeout"))
        is_not = bool(options.get("isNot"))

        async def inner() -> FrameExpectResult:
            # Python: params are the arguments of the expect() call. Python has no
            # undefined: an absent expected value is not sent, where upstream sends
            # serializeArgument(undefined); the driver reads both as undefined.
            expected_value = (
                serialize_argument(options["expectedValue"])
                if "expectedValue" in options
                else None
            )
            try:
                await self._channel.expect(
                    selector=selector,
                    expression=expression,
                    expressionArg=options.get("expressionArg"),
                    pseudo=options.get("pseudo"),
                    expectedText=options.get("expectedText"),
                    expectedNumber=options.get("expectedNumber"),
                    expectedValue=expected_value,
                    useInnerText=options.get("useInnerText"),
                    isNot=is_not,
                    timeout=timeout,
                )
                return {"matches": not is_not}
            except Exception as e:
                # Not ported: the AbortError of the `signal` option.
                if not isinstance(e, Error):
                    raise e
                details = cast(Optional[Dict[str, Any]], e._details)
                # Python: an error that did not come from the driver (a closed
                # connection) has no details. Upstream reads `details.received`
                # and throws a TypeError; this raises the error itself.
                if details is None:
                    raise e
                received = (
                    {
                        "value": (
                            parse_result(details["received"]["value"])
                            if details["received"].get("value") is not None
                            else None
                        ),
                        "ariaSnapshot": details["received"].get("ariaSnapshot"),
                    }
                    if details.get("received")
                    else None
                )
                return {
                    "matches": is_not,
                    "received": received,
                    "log": e._log,
                    "timedOut": details.get("timedOut"),
                    "errorMessage": (
                        "Error: " + details["customErrorMessage"]
                        if details.get("customErrorMessage")
                        else None
                    ),
                }

        return await self._wrap_api_call(lambda _: inner(), ApiCallOptions(title=title))

    # Python only: the members of the Python API that upstream does not have.

    def expect_navigation(
        self,
        url: Optional[URLMatch],
        wait_until: Optional[LifecycleEvent],
        timeout: Optional[float],
    ) -> "EventContextManagerImpl[network.Response]":
        # Python only: waitForNavigation() as a context manager. wait_for_navigation()
        # is a plain def, so the waiter and its listeners are set up here, before the
        # with block runs; the wait runs in a task.
        return EventContextManagerImpl(
            asyncio.ensure_future(
                self.wait_for_navigation(
                    url=url, wait_until=wait_until, timeout=timeout
                )
            )
        )

    def __repr__(self) -> str:
        return f"<Frame name={self.name} url={self.url!r}>"


# Not ported: the ExpectReceived and ExpectResult types. The result is the
# FrameExpectResult of playwright/_impl/_internal_structures.py, which
# playwright/_impl/_assertions.py reads.


def verify_load_state(name: str, wait_until: str) -> LifecycleEvent:
    if wait_until == "networkidle0":
        wait_until = "networkidle"
    if wait_until not in LIFECYCLE_EVENTS:
        raise Error(
            f"{name}: expected one of (load|domcontentloaded|networkidle|commit)"
        )
    return cast(LifecycleEvent, wait_until)


# Python only: fs.promises.readFile(path), in a thread.
async def _read_file(path: Union[str, Path]) -> bytes:
    def read() -> bytes:
        with open(path, "rb") as file:
            return file.read()

    return await asyncio.get_running_loop().run_in_executor(None, read)
