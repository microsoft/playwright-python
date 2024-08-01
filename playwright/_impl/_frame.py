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
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
    cast,
)

from pyee import EventEmitter

from playwright._impl._api_structures import AriaRole, FilePayload, Position
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._element_handle import ElementHandle, convert_select_option_values
from playwright._impl._errors import Error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import (
    DocumentLoadState,
    FrameNavigatedEvent,
    KeyboardModifier,
    Literal,
    MouseButton,
    URLMatch,
    URLMatcher,
    async_readfile,
    locals_to_params,
    monotonic_time,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    add_source_url_to_script,
    parse_result,
    serialize_argument,
)
from playwright._impl._locator import (
    FrameLocator,
    Locator,
    get_by_alt_text_selector,
    get_by_label_selector,
    get_by_placeholder_selector,
    get_by_role_selector,
    get_by_test_id_selector,
    get_by_text_selector,
    get_by_title_selector,
    test_id_attribute_name,
)
from playwright._impl._network import Response
from playwright._impl._set_input_files_helpers import convert_input_files
from playwright._impl._waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page


class Frame(ChannelOwner):
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
        self._channel.on(
            "loadstate",
            lambda params: self._on_load_state(params.get("add"), params.get("remove")),
        )
        self._channel.on(
            "navigated",
            lambda params: self._on_frame_navigated(params),
        )

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
        if not self._parent_frame and add == "domcontentloaded" and self._page:
            self._page.emit("domcontentloaded", self._page)

    def _on_frame_navigated(self, event: FrameNavigatedEvent) -> None:
        self._url = event["url"]
        self._name = event["name"]
        self._event_emitter.emit("navigated", event)
        if "error" not in event and self._page:
            self._page.emit("framenavigated", self)

    async def _query_count(self, selector: str) -> int:
        return await self._channel.send("queryCount", {"selector": selector})

    @property
    def page(self) -> "Page":
        assert self._page
        return self._page

    async def goto(
        self,
        url: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
        referer: str = None,
    ) -> Optional[Response]:
        return cast(
            Optional[Response],
            from_nullable_channel(
                await self._channel.send("goto", locals_to_params(locals()))
            ),
        )

    def _setup_navigation_waiter(self, wait_name: str, timeout: float = None) -> Waiter:
        assert self._page
        waiter = Waiter(self._page, f"frame.{wait_name}")
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
        if timeout is None:
            timeout = self._page._timeout_settings.navigation_timeout()
        waiter.reject_on_timeout(timeout, f"Timeout {timeout}ms exceeded.")
        return waiter

    def expect_navigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Response]:
        assert self._page
        if not waitUntil:
            waitUntil = "load"

        if timeout is None:
            timeout = self._page._timeout_settings.navigation_timeout()
        deadline = monotonic_time() + timeout
        waiter = self._setup_navigation_waiter("expect_navigation", timeout)

        to_url = f' to "{url}"' if url else ""
        waiter.log(f"waiting for navigation{to_url} until '{waitUntil}'")
        matcher = (
            URLMatcher(self._page._browser_context._options.get("baseURL"), url)
            if url
            else None
        )

        def predicate(event: Any) -> bool:
            # Any failed navigation results in a rejection.
            if event.get("error"):
                return True
            waiter.log(f'  navigated to "{event["url"]}"')
            return not matcher or matcher.matches(event["url"])

        waiter.wait_for_event(
            self._event_emitter,
            "navigated",
            predicate=predicate,
        )

        async def continuation() -> Optional[Response]:
            event = await waiter.result()
            if "error" in event:
                raise Error(event["error"])
            if waitUntil not in self._load_states:
                t = deadline - monotonic_time()
                if t > 0:
                    await self._wait_for_load_state_impl(state=waitUntil, timeout=t)
            if "newDocument" in event and "request" in event["newDocument"]:
                request = from_channel(event["newDocument"]["request"])
                return await request.response()
            return None

        return EventContextManagerImpl(asyncio.create_task(continuation()))

    async def wait_for_url(
        self,
        url: URLMatch,
        waitUntil: DocumentLoadState = None,
        timeout: float = None,
    ) -> None:
        assert self._page
        matcher = URLMatcher(self._page._browser_context._options.get("baseURL"), url)
        if matcher.matches(self.url):
            await self._wait_for_load_state_impl(state=waitUntil, timeout=timeout)
            return
        async with self.expect_navigation(
            url=url, waitUntil=waitUntil, timeout=timeout
        ):
            pass

    async def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None,
    ) -> None:
        return await self._wait_for_load_state_impl(state, timeout)

    async def _wait_for_load_state_impl(
        self, state: DocumentLoadState = None, timeout: float = None
    ) -> None:
        if not state:
            state = "load"
        if state not in ("load", "domcontentloaded", "networkidle", "commit"):
            raise Error(
                "state: expected one of (load|domcontentloaded|networkidle|commit)"
            )
        waiter = self._setup_navigation_waiter("wait_for_load_state", timeout)

        if state in self._load_states:
            waiter.log(f'  not waiting, "{state}" event already fired')
            # TODO: align with upstream
            waiter._fulfill(None)
        else:

            def handle_load_state_event(actual_state: str) -> bool:
                waiter.log(f'"{actual_state}" event fired')
                return actual_state == state

            waiter.wait_for_event(
                self._event_emitter,
                "loadstate",
                handle_load_state_event,
            )
        await waiter.result()

    async def frame_element(self) -> ElementHandle:
        return from_channel(await self._channel.send("frameElement"))

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

    async def query_selector(
        self, selector: str, strict: bool = None
    ) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("querySelector", locals_to_params(locals()))
        )

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        return list(
            map(
                from_channel,
                await self._channel.send("querySelectorAll", dict(selector=selector)),
            )
        )

    async def wait_for_selector(
        self,
        selector: str,
        strict: bool = None,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("waitForSelector", locals_to_params(locals()))
        )

    async def is_checked(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isChecked", locals_to_params(locals()))

    async def is_disabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isDisabled", locals_to_params(locals()))

    async def is_editable(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isEditable", locals_to_params(locals()))

    async def is_enabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isEnabled", locals_to_params(locals()))

    async def is_hidden(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isHidden", locals_to_params(locals()))

    async def is_visible(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isVisible", locals_to_params(locals()))

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        eventInit: Dict = None,
        strict: bool = None,
        timeout: float = None,
    ) -> None:
        await self._channel.send(
            "dispatchEvent",
            locals_to_params(
                dict(
                    selector=selector,
                    type=type,
                    eventInit=serialize_argument(eventInit),
                    strict=strict,
                    timeout=timeout,
                ),
            ),
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        strict: bool = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelector",
                locals_to_params(
                    dict(
                        selector=selector,
                        expression=expression,
                        arg=serialize_argument(arg),
                        strict=strict,
                    )
                ),
            )
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelectorAll",
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def content(self) -> str:
        return await self._channel.send("content")

    async def set_content(
        self,
        html: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> None:
        await self._channel.send("setContent", locals_to_params(locals()))

    @property
    def name(self) -> str:
        return self._name or ""

    @property
    def url(self) -> str:
        return self._url or ""

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
        url: str = None,
        path: Union[str, Path] = None,
        content: str = None,
        type: str = None,
    ) -> ElementHandle:
        params = locals_to_params(locals())
        if path:
            params["content"] = add_source_url_to_script(
                (await async_readfile(path)).decode(), path
            )
            del params["path"]
        return from_channel(await self._channel.send("addScriptTag", params))

    async def add_style_tag(
        self, url: str = None, path: Union[str, Path] = None, content: str = None
    ) -> ElementHandle:
        params = locals_to_params(locals())
        if path:
            params["content"] = (
                (await async_readfile(path)).decode()
                + "\n/*# sourceURL="
                + str(Path(path))
                + "*/"
            )
            del params["path"]
        return from_channel(await self._channel.send("addStyleTag", params))

    async def click(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("click", locals_to_params(locals()))

    async def dblclick(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def tap(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("tap", locals_to_params(locals()))

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    def locator(
        self,
        selector: str,
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: Locator = None,
        hasNot: Locator = None,
    ) -> Locator:
        return Locator(
            self,
            selector,
            has_text=hasText,
            has_not_text=hasNotText,
            has=has,
            has_not=hasNot,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_alt_text_selector(text, exact=exact))

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_label_selector(text, exact=exact))

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_placeholder_selector(text, exact=exact))

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
        return self.locator(
            get_by_role_selector(
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
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(get_by_test_id_selector(test_id_attribute_name(), testId))

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_text_selector(text, exact=exact))

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_title_selector(text, exact=exact))

    def frame_locator(self, selector: str) -> FrameLocator:
        return FrameLocator(self, selector)

    async def focus(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> None:
        await self._channel.send("focus", locals_to_params(locals()))

    async def text_content(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._channel.send("textContent", locals_to_params(locals()))

    async def inner_text(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._channel.send("innerText", locals_to_params(locals()))

    async def inner_html(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._channel.send("innerHTML", locals_to_params(locals()))

    async def get_attribute(
        self, selector: str, name: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._channel.send("getAttribute", locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("hover", locals_to_params(locals()))

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        sourcePosition: Position = None,
        targetPosition: Position = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        timeout: float = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("dragAndDrop", locals_to_params(locals()))

    async def select_option(
        self,
        selector: str,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        force: bool = None,
    ) -> List[str]:
        params = locals_to_params(
            dict(
                selector=selector,
                timeout=timeout,
                noWaitAfter=noWaitAfter,
                strict=strict,
                force=force,
                **convert_select_option_values(value, index, label, element),
            )
        )
        return await self._channel.send("selectOption", params)

    async def input_value(
        self,
        selector: str,
        strict: bool = None,
        timeout: float = None,
    ) -> str:
        return await self._channel.send("inputValue", locals_to_params(locals()))

    async def set_input_files(
        self,
        selector: str,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        strict: bool = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        converted = await convert_input_files(files, self.page.context)
        await self._channel.send(
            "setInputFiles",
            {
                "selector": selector,
                "strict": strict,
                "timeout": timeout,
                **converted,
            },
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: float = None,
        strict: bool = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("type", locals_to_params(locals()))

    async def press(
        self,
        selector: str,
        key: str,
        delay: float = None,
        strict: bool = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("press", locals_to_params(locals()))

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
        await self._channel.send("check", locals_to_params(locals()))

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
        await self._channel.send("uncheck", locals_to_params(locals()))

    async def wait_for_timeout(self, timeout: float) -> None:
        await self._channel.send("waitForTimeout", locals_to_params(locals()))

    async def wait_for_function(
        self,
        expression: str,
        arg: Serializable = None,
        timeout: float = None,
        polling: Union[float, Literal["raf"]] = None,
    ) -> JSHandle:
        if isinstance(polling, str) and polling != "raf":
            raise Error(f"Unknown polling option: {polling}")
        params = locals_to_params(locals())
        params["arg"] = serialize_argument(arg)
        if polling is not None and polling != "raf":
            params["pollingInterval"] = polling
        return from_channel(await self._channel.send("waitForFunction", params))

    async def title(self) -> str:
        return await self._channel.send("title")

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
                strict=strict,
                trial=trial,
            )
        else:
            await self.uncheck(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                strict=strict,
                trial=trial,
            )

    async def _highlight(self, selector: str) -> None:
        await self._channel.send("highlight", {"selector": selector})
