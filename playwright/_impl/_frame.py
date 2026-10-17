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
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
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

from pyee import EventEmitter

from playwright._impl._api_structures import DropPayload, FilePayload, Position
from playwright._impl._connection import (
    ChannelOwner,
    api_call,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._element_handle import ElementHandle, convert_select_option_values
from playwright._impl._errors import Error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import (
    DocumentLoadState,
    KeyboardModifier,
    MouseButton,
    URLMatch,
    async_readfile,
    url_matches,
)
from playwright._impl._internal_structures import (
    AriaRole,
    FrameExpectOptions,
    FrameExpectResult,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    add_source_url_to_script,
    parse_result,
    serialize_argument,
)
from playwright._impl._locator import (
    ANY_FRAME_SELECTOR,
    FrameLocator,
    Locator,
    test_id_attribute_name,
)
from playwright._impl._locator_utils import (
    get_by_alt_text_selector,
    get_by_label_selector,
    get_by_placeholder_selector,
    get_by_role_selector,
    get_by_test_id_selector,
    get_by_text_selector,
    get_by_title_selector,
)
from playwright._impl._network import Response
from playwright._impl._serializers import parse_value
from playwright._impl._set_input_files_helpers import convert_input_files
from playwright._impl._timeout_settings import TimeoutSettings
from playwright._impl._waiter import Waiter
from playwright._impl._web_mcp import WebMCP

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._page import Page
    from playwright._impl._protocol_channels import FrameChannel, JSHandleChannel


class Frame(ChannelOwner):
    _channel: "FrameChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._parent_frame = from_nullable_channel(initializer.get("parentFrame"))
        if self._parent_frame:
            self._parent_frame._child_frames.append(self)
        self._name = initializer["name"]
        self._url = initializer["url"]
        self._detached = False
        self._child_frames: List[Frame] = []
        self._page: Optional[Page] = None
        self._load_states: Set[str] = set(initializer["loadStates"])
        self._event_emitter = EventEmitter()
        self._webmcp = WebMCP(self)
        self._channel.onLoadstate(
            lambda event: self._on_load_state(event["add"], event["remove"])
        )
        self._channel.onNavigated(self._on_frame_navigated)

    def __repr__(self) -> str:
        return f"<Frame name={self.name} url={self.url!r}>"

    def _on_load_state(
        self, add: DocumentLoadState = None, remove: DocumentLoadState = None
    ) -> None:
        if add:
            self._load_states.add(add)
            self._event_emitter.emit("loadstate", add)
        elif remove and remove in self._load_states:
            self._load_states.remove(remove)
        if not self._parent_frame and add == "load" and self._page:
            self._page.emit("load", self._page)
            self._page.context.emit("pageload", self._page)
        if not self._parent_frame and add == "domcontentloaded" and self._page:
            self._page.emit("domcontentloaded", self._page)

    def _on_frame_navigated(self, event: "channels.FrameNavigatedEvent") -> None:
        self._url = event["url"]
        self._name = event["name"]
        self._event_emitter.emit("navigated", event)
        if not event["error"] and self._page:
            self._page.emit("framenavigated", self)
            self._page.context.emit("framenavigated", self)

    async def _query_count(self, selector: str) -> int:
        return (await self._channel.queryCount(selector=selector))["value"]

    @property
    def page(self) -> "Page":
        assert self._page
        return self._page

    async def goto(
        self,
        url: str,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
        referer: Optional[str],
    ) -> Optional[Response]:
        result = await self._channel.goto(
            url=url,
            waitUntil=wait_until,
            referer=referer,
            timeout=self._navigation_timeout(timeout),
        )
        return from_nullable_channel(result["response"])

    def _setup_navigation_waiter(self, title: str, timeout: float = None) -> Waiter:
        # Port of Frame._setupNavigationWaiter() in client/frame.ts. Upstream titles
        # the wait with the title of the outer API call, such as 'Wait for
        # navigation' of waitForNavigation().
        assert self._page
        waiter = Waiter(self._page, "", title)
        if self._page.is_closed():
            waiter.reject_immediately(self._page._close_error_with_reason())
        waiter.reject_on_event(
            self._page,
            "close",
            lambda: cast("Page", self._page)._close_error_with_reason(),
        )
        waiter.reject_on_event(
            self._page, "crash", Error("Navigation failed because page crashed!")
        )
        waiter.reject_on_event(
            self._page,
            "framedetached",
            Error("Navigating frame was detached!"),
            lambda frame: frame == self,
        )
        timeout = self._page._timeout_settings.navigation_timeout(timeout)
        waiter.reject_on_timeout(timeout, f"Timeout {timeout}ms exceeded.")
        return waiter

    async def _expect(
        self,
        selector: Optional[str],
        expression: str,
        options: FrameExpectOptions,
        title: str = None,
    ) -> FrameExpectResult:
        try:
            await self._connection.wrap_api_call(
                lambda: self._channel.expect(
                    selector=selector,
                    expression=expression,
                    expressionArg=options.get("expressionArg"),
                    pseudo=options.get("pseudo"),
                    expectedText=options.get("expectedText"),
                    expectedNumber=options.get("expectedNumber"),
                    expectedValue=(
                        serialize_argument(options["expectedValue"])
                        if "expectedValue" in options
                        else None
                    ),
                    useInnerText=options.get("useInnerText"),
                    isNot=bool(options.get("isNot")),
                    timeout=self._timeout(options.get("timeout")),
                ),
                title=title,
            )
            return {"matches": not options.get("isNot")}
        except Error as e:
            if not e._details:
                raise e
            details = cast(Dict[str, Any], e._details)
            received = details.get("received")
            if received:
                received = {
                    "value": (
                        parse_value(received["value"]) if "value" in received else None
                    ),
                    "ariaSnapshot": received.get("ariaSnapshot"),
                }
            return {
                "matches": bool(options.get("isNot")),
                "received": received,
                "timedOut": details.get("timedOut"),
                "errorMessage": (
                    "Error: " + details["customErrorMessage"]
                    if details.get("customErrorMessage")
                    else None
                ),
                "log": e._log,
            }

    @api_call
    def expect_navigation(
        self,
        url: Optional[URLMatch],
        wait_until: Optional[DocumentLoadState],
        timeout: Optional[float],
    ) -> EventContextManagerImpl[Response]:
        # Port of waitForNavigation() in frame.ts: one waiter, so that its
        # timeout and its log cover the whole wait.
        assert self._page
        if not wait_until:
            wait_until = "load"
        waiter = self._setup_navigation_waiter("Wait for navigation", timeout)

        to_url = f' to "{url}"' if isinstance(url, str) else ""
        waiter.log(f'waiting for navigation{to_url} until "{wait_until}"')

        def predicate(event: "channels.FrameNavigatedEvent") -> bool:
            # Any failed navigation results in a rejection.
            if event["error"]:
                return True
            waiter.log(f'  navigated to "{event["url"]}"')
            return url_matches(
                cast("Page", self._page)._browser_context._base_url,
                event["url"],
                url,
            )

        navigated = waiter.wait_for_event(
            self._event_emitter,
            "navigated",
            predicate=predicate,
        )

        async def continuation() -> Optional[Response]:
            event: "channels.FrameNavigatedEvent" = await navigated
            error = event["error"]
            if error:
                failed: asyncio.Future = self._loop.create_future()
                failed.set_exception(Error(error))
                await waiter.wait_for_future(failed)

            if wait_until not in self._load_states:

                def on_load_state(state: str) -> bool:
                    waiter.log(f'  "{state}" event fired')
                    return state == wait_until

                await waiter.wait_for_event(
                    self._event_emitter, "loadstate", on_load_state
                )

            response: Optional[Response] = None
            new_document = event["newDocument"]
            if new_document and new_document.get("request"):
                request = from_channel(new_document["request"])
                # Request._finalRequest() in network.ts.
                while request.redirected_to:
                    request = request.redirected_to
                response_task = self._loop.create_task(request.response())

                def cancel_response() -> None:
                    response_task.cancel()

                response = await waiter.wait_for_future(response_task, cancel_response)
            waiter.dispose()
            return response

        task = self._loop.create_task(continuation())
        # Cancelled before it started: stop the wait for the navigation, too.
        task.add_done_callback(
            lambda _: navigated.cancel() if task.cancelled() else None
        )
        return EventContextManagerImpl(task)

    @api_call
    async def wait_for_url(
        self,
        url: URLMatch,
        wait_until: Optional[DocumentLoadState],
        timeout: Optional[float],
    ) -> None:
        assert self._page
        if url_matches(self._page._browser_context._base_url, self.url, url):
            await self._wait_for_load_state_impl(state=wait_until, timeout=timeout)
            return
        async with self.expect_navigation(
            url=url, wait_until=wait_until, timeout=timeout
        ):
            pass

    @api_call
    async def wait_for_load_state(
        self,
        state: Optional[Literal["domcontentloaded", "load", "networkidle"]],
        timeout: Optional[float],
    ) -> None:
        return await self._wait_for_load_state_impl(state=state, timeout=timeout)

    async def _wait_for_load_state_impl(
        self, state: Optional[DocumentLoadState], timeout: Optional[float]
    ) -> None:
        # Port of waitForLoadState() in frame.ts.
        if not state:
            state = "load"
        if state not in ("load", "domcontentloaded", "networkidle", "commit"):
            raise Error(
                "state: expected one of (load|domcontentloaded|networkidle|commit)"
            )
        waiter = self._setup_navigation_waiter("Wait for load state", timeout)
        try:
            if state in self._load_states:
                waiter.log(f'  not waiting, "{state}" event already fired')
            else:

                def on_load_state(actual_state: str) -> bool:
                    waiter.log(f'  "{actual_state}" event fired')
                    return actual_state == state

                await waiter.wait_for_event(
                    self._event_emitter, "loadstate", on_load_state
                )
        finally:
            waiter.dispose()

    def _timeout(self, timeout: Optional[float]) -> float:
        timeout_settings = (
            self._page._timeout_settings if self._page else TimeoutSettings(None)
        )
        return timeout_settings.timeout(timeout)

    def _navigation_timeout(self, timeout: Optional[float]) -> float:
        timeout_settings = (
            self._page._timeout_settings if self._page else TimeoutSettings(None)
        )
        return timeout_settings.navigation_timeout(timeout)

    async def frame_element(self) -> ElementHandle:
        return from_channel((await self._channel.frameElement())["element"])

    async def evaluate(self, expression: str, arg: Serializable) -> Any:
        result = await self._channel.evaluateExpression(
            expression=expression,
            isFunction=None,
            arg=serialize_argument(arg),
        )
        return parse_result(result["value"])

    async def evaluate_handle(self, expression: str, arg: Serializable) -> JSHandle:
        result = await self._channel.evaluateExpressionHandle(
            expression=expression,
            isFunction=None,
            arg=serialize_argument(arg),
        )
        return from_channel(result["handle"])

    async def query_selector(
        self, selector: str, strict: Optional[bool]
    ) -> Optional[ElementHandle]:
        result = await self._channel.querySelector(selector=selector, strict=strict)
        return from_nullable_channel(result["element"])

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        result = await self._channel.querySelectorAll(selector=selector)
        return list(map(from_channel, result["elements"]))

    async def wait_for_selector(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
        state: Optional[Literal["attached", "detached", "hidden", "visible"]],
        omit_return_value: Optional[bool] = None,  # Not in the docs; Locator passes it.
    ) -> Optional[ElementHandle]:
        result = await self._channel.waitForSelector(
            selector=selector,
            strict=strict,
            state=state,
            omitReturnValue=omit_return_value,
            timeout=self._timeout(timeout),
        )
        return from_nullable_channel(result["element"])

    async def is_checked(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        result = await self._channel.isChecked(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def is_disabled(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        result = await self._channel.isDisabled(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def is_editable(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        result = await self._channel.isEditable(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def is_enabled(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> bool:
        result = await self._channel.isEnabled(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def is_hidden(
        self,
        selector: str,
        strict: Optional[bool],
    ) -> bool:
        result = await self._channel.isHidden(
            selector=selector, strict=strict, timeout=self._timeout(None)
        )
        return result["value"]

    async def is_visible(
        self,
        selector: str,
        strict: Optional[bool],
    ) -> bool:
        result = await self._channel.isVisible(
            selector=selector, strict=strict, timeout=self._timeout(None)
        )
        return result["value"]

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
            strict=strict,
            expression=expression,
            isFunction=None,
            arg=serialize_argument(arg),
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
            isFunction=None,
            arg=serialize_argument(arg),
        )
        return parse_result(result["value"])

    async def content(self, include_shadow: Optional[bool]) -> str:
        return (await self._channel.content(includeShadow=include_shadow))["value"]

    async def set_content(
        self,
        html: str,
        timeout: Optional[float],
        wait_until: Optional[DocumentLoadState],
    ) -> None:
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
        return self._url or ""

    @property
    def webmcp(self) -> WebMCP:
        return self._webmcp

    @property
    def parent_frame(self) -> Optional["Frame"]:
        return self._parent_frame

    @property
    def child_frames(self) -> List["Frame"]:
        return self._child_frames.copy()

    def is_detached(self) -> bool:
        return self._detached

    async def add_script_tag(
        self,
        url: Optional[str],
        path: Optional[Union[str, Path]],
        content: Optional[str],
        type: Optional[str],
    ) -> ElementHandle:
        if path:
            content = add_source_url_to_script(
                (await async_readfile(path)).decode(), path
            )
        result = await self._channel.addScriptTag(url=url, content=content, type=type)
        return from_channel(result["element"])

    async def add_style_tag(
        self,
        url: Optional[str],
        path: Optional[Union[str, Path]],
        content: Optional[str],
    ) -> ElementHandle:
        if path:
            content = (
                (await async_readfile(path)).decode()
                + "\n/*# sourceURL="
                + str(Path(path))
                + "*/"
            )
        result = await self._channel.addStyleTag(url=url, content=content)
        return from_channel(result["element"])

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
        steps: Optional[int] = None,  # Not in the docs; Locator passes it.
    ) -> None:
        await self._channel.click(
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
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
        steps: Optional[int] = None,  # Not in the docs; Locator passes it.
    ) -> None:
        await self._connection.wrap_api_call(
            lambda: self._channel.dblclick(
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
            ),
            title="Double click",
        )

    async def tap(
        self,
        selector: str,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        strict: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.tap(
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
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        strict: Optional[bool],
        force: Optional[bool],
    ) -> None:
        await self._fill(
            selector,
            value,
            title=None,
            timeout=timeout,
            no_wait_after=no_wait_after,
            strict=strict,
            force=force,
        )

    async def _fill(
        self,
        selector: str,
        value: str,
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        strict: Optional[bool],
        force: Optional[bool],
        title: Optional[str],
    ) -> None:
        await self._connection.wrap_api_call(
            lambda: self._channel.fill(
                selector=selector,
                strict=strict,
                value=value,
                force=force,
                timeout=self._timeout(timeout),
            ),
            title=title,
        )

    def locator(
        self,
        selector: str,
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

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            selector=get_by_alt_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            selector=get_by_label_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            selector=get_by_placeholder_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

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

    def get_by_test_id(self, test_id: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(
            selector=get_by_test_id_selector(test_id_attribute_name(), test_id),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            selector=get_by_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            selector=get_by_title_selector(text, exact=exact),
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
        result = await self._channel.textContent(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def inner_text(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> str:
        result = await self._channel.innerText(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def inner_html(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> str:
        result = await self._channel.innerHTML(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def get_attribute(
        self,
        selector: str,
        name: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> Optional[str]:
        result = await self._channel.getAttribute(
            selector=selector,
            strict=strict,
            name=name,
            timeout=self._timeout(timeout),
        )
        return result["value"]

    async def hover(
        self,
        selector: str,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
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

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        source_position: Optional[Position],
        target_position: Optional[Position],
        force: Optional[bool],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        strict: Optional[bool],
        timeout: Optional[float],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._channel.dragAndDrop(
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

    async def select_option(
        self,
        selector: str,
        value: Optional[Union[str, Sequence[str]]],
        index: Optional[Union[int, Sequence[int]]],
        label: Optional[Union[str, Sequence[str]]],
        element: Optional[Union["ElementHandle", Sequence["ElementHandle"]]],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
        strict: Optional[bool],
        force: Optional[bool],
    ) -> List[str]:
        values = convert_select_option_values(value, index, label, element)
        result = await self._channel.selectOption(
            selector=selector,
            strict=strict,
            elements=values.get("elements"),
            options=values.get("options"),
            force=force,
            timeout=self._timeout(timeout),
        )
        return result["values"]

    async def input_value(
        self,
        selector: str,
        strict: Optional[bool],
        timeout: Optional[float],
    ) -> str:
        result = await self._channel.inputValue(
            selector=selector, strict=strict, timeout=self._timeout(timeout)
        )
        return result["value"]

    async def set_input_files(
        self,
        selector: str,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        strict: Optional[bool],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
    ) -> None:
        converted = await convert_input_files(files, self.page.context)
        await self._channel.setInputFiles(
            selector=selector,
            strict=strict,
            payloads=converted.get("payloads"),
            localDirectory=converted.get("localDirectory"),
            directoryStream=converted.get("directoryStream"),
            localPaths=converted.get("localPaths"),
            streams=converted.get("streams"),
            timeout=self._timeout(timeout),
        )

    async def _drop(
        self,
        selector: str,
        payload: "DropPayload",
        strict: Optional[bool],
        position: Optional[Position],
        timeout: Optional[float],
    ) -> None:
        payloads = None
        local_paths = None
        streams = None
        files = payload.get("files") if payload else None
        if files is not None:
            converted = await convert_input_files(files, self.page.context)
            if converted.get("directoryStream") or converted.get("localDirectory"):
                raise Error(
                    "Dropping a directory is not supported, pass individual files instead."
                )
            payloads = converted.get("payloads")
            local_paths = converted.get("localPaths")
            streams = converted.get("streams")
        data = payload.get("data") if payload else None
        await self._channel.drop(
            selector=selector,
            strict=strict,
            position=position,
            payloads=payloads,
            localPaths=local_paths,
            streams=streams,
            data=(
                [{"mimeType": k, "value": v} for k, v in data.items()]
                if data is not None
                else None
            ),
            timeout=self._timeout(timeout),
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: Optional[float],
        strict: Optional[bool],
        timeout: Optional[float],
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
    ) -> None:
        await self._channel.type(
            selector=selector,
            strict=strict,
            text=text,
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
            strict=strict,
            key=key,
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
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
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
        no_wait_after: Optional[bool],  # Deprecated; does nothing.
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

    async def wait_for_timeout(self, timeout: float) -> None:
        await self._channel.waitForTimeout(waitTimeout=timeout)

    async def wait_for_function(
        self,
        expression: str,
        arg: Serializable,
        timeout: Optional[float],
        polling: Optional[Union[float, Literal["raf"]]],
    ) -> JSHandle:
        if isinstance(polling, str) and polling != "raf":
            raise Error(f"Unknown polling option: {polling}")
        result = await self._channel.waitForFunction(
            expression=expression,
            isFunction=None,
            arg=serialize_argument(arg),
            # "raf" is the default polling, sent as no interval.
            pollingInterval=None if isinstance(polling, str) else polling,
            selector=None,
            strict=None,
            timeout=self._timeout(timeout),
        )
        return from_channel(cast("JSHandleChannel", result["handle"]))

    async def title(self) -> str:
        return (await self._channel.title())["value"]

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

    async def _highlight(self, selector: str, style: Optional[str]) -> None:
        await self._channel.highlight(selector=selector, style=style)

    async def _hide_highlight(self, selector: str) -> None:
        await self._channel.hideHighlight(selector=selector)
