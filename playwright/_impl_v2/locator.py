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

"""Port of packages/playwright-core/src/client/locator.ts.

Python: Locator and FrameLocator are not ChannelOwners, so each one keeps the event
loop of its frame for the generated API. A page function is always a string. Python
has no locator generator (isomorphic/locatorGenerators.ts): the driver generates the
Python code of a normalized locator, and repr() shows the selector otherwise. The
JavaScript-only API (util.inspect.custom, toString(), ariaSnapshotJSON(), the object
form of the highlight style, signal) is not ported.
"""

import json
import pathlib
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    TypeVar,
    Union,
    cast,
)

from playwright._impl._api_structures import (
    DropPayload,
    FilePayload,
    FloatRect,
    Position,
)
from playwright._impl_v2.channel_owner import ApiCallOptions, ApiZone, api_call
from playwright._impl_v2.disposable import DisposableStub
from playwright._impl_v2.errors import Error
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
from playwright._impl_v2.isomorphic.string_utils import escape_for_text_selector
from playwright._impl_v2.isomorphic.time import monotonic_time
from playwright._impl_v2.js_handle import serialize_argument
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.element_handle import ElementHandle
    from playwright._impl_v2.frame import Frame
    from playwright._impl_v2.js_handle import JSHandle
    from playwright._impl_v2.page import Page

R = TypeVar("R")

# Python: the types of the Python API options (playwright/_impl/_helper.py).
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]

# Python: kAnyFrameSelector of isomorphic/selectorParser.ts, which Python does not
# have.
ANY_FRAME_SELECTOR = "internal:control=any-frame"


class Locator:
    def __init__(
        self,
        frame: "Frame",
        selector: str,
        # Python: the LocatorOptions, as separate parameters.
        has_text: Optional[Union[str, Pattern[str]]] = None,
        has_not_text: Optional[Union[str, Pattern[str]]] = None,
        has: Optional["Locator"] = None,
        has_not: Optional["Locator"] = None,
        visible: Optional[bool] = None,
    ) -> None:
        self._frame = frame
        self._selector = selector
        self._api_name = "Locator"
        # Python: the generated API reads the event loop of each object.
        self._loop = frame._loop
        # Python: the Python code of this locator, known only for a normalized
        # locator. See normalize().
        self._locator_code: Optional[str] = None

        if has_text:
            self._selector += (
                f" >> internal:has-text={escape_for_text_selector(has_text, False)}"
            )

        if has_not_text:
            self._selector += f" >> internal:has-not-text={escape_for_text_selector(has_not_text, False)}"

        if has:
            locator = has
            if locator._frame is not frame:
                raise Error('Inner "has" locator must belong to the same frame.')
            self._selector += " >> internal:has=" + json.dumps(
                locator._selector, ensure_ascii=False
            )

        if has_not:
            locator = has_not
            if locator._frame is not frame:
                raise Error('Inner "hasNot" locator must belong to the same frame.')
            self._selector += " >> internal:has-not=" + json.dumps(
                locator._selector, ensure_ascii=False
            )

        if visible is not None:
            self._selector += f" >> visible={'true' if visible else 'false'}"

        # Not ported: util.inspect.custom is Node.js only; __repr__() is the Python
        # counterpart.

    def _wrap_api_call(
        self,
        func: Callable[[ApiZone], Awaitable[R]],
        options: Optional[ApiCallOptions] = None,
    ) -> Awaitable[R]:
        # Python: not an async def, as ChannelOwner._wrap_api_call(): func is
        # called at once.
        return self._frame._wrap_api_call(func, options)

    async def _with_element(
        self,
        task: Callable[["ElementHandle", float], Awaitable[R]],
        timeout: Optional[float],
    ) -> R:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.element_handle import ElementHandle

        timeout = self._frame._timeout(timeout)
        deadline = monotonic_time() + timeout if timeout else 0

        result = await self._frame._channel.waitForSelector(
            selector=self._selector,
            strict=True,
            state="attached",
            omitReturnValue=None,
            timeout=timeout,
        )
        handle = ElementHandle.from_nullable(result["element"])
        if not handle:
            raise Error(f"Could not resolve {self._selector} to DOM Element")
        try:
            return await task(handle, deadline - monotonic_time() if deadline else 0)
        finally:
            await handle.dispose()

    def _equals(self, locator: "Locator") -> bool:
        return self._frame is locator._frame and self._selector == locator._selector

    @property
    def page(self) -> "Page":
        return self._frame.page

    @api_call(title="Bounding box")
    async def bounding_box(self, timeout: Optional[float]) -> Optional[FloatRect]:
        return await self._with_element(lambda h, _: h.bounding_box(), timeout)

    async def check(
        self,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._frame.check(
            self._selector,
            strict=True,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            trial=trial,
            scroll=scroll,
        )

    async def click(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        delay: Optional[float],
        button: Optional[MouseButton],
        click_count: Optional[int],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._frame.click(
            self._selector,
            strict=True,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            click_count=click_count,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            trial=trial,
            steps=steps,
            scroll=scroll,
        )

    async def dblclick(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        delay: Optional[float],
        button: Optional[MouseButton],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        await self._frame.dblclick(
            self._selector,
            strict=True,
            modifiers=modifiers,
            position=position,
            delay=delay,
            button=button,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            trial=trial,
            steps=steps,
            scroll=scroll,
        )

    async def dispatch_event(
        self,
        type: str,
        event_init: Optional[Dict],
        timeout: Optional[float],
    ) -> None:
        return await self._frame.dispatch_event(
            self._selector,
            type=type,
            # Python: None is undefined, so the default {} applies.
            event_init=event_init if event_init is not None else {},
            strict=True,
            timeout=timeout,
        )

    async def drag_to(
        self,
        target: "Locator",
        force: Optional[bool],
        no_wait_after: Optional[bool],
        timeout: Optional[float],
        trial: Optional[bool],
        source_position: Optional[Position],
        target_position: Optional[Position],
        steps: Optional[int],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._frame.drag_and_drop(
            self._selector,
            target._selector,
            strict=True,
            force=force,
            no_wait_after=no_wait_after,
            timeout=timeout,
            trial=trial,
            source_position=source_position,
            target_position=target_position,
            steps=steps,
            scroll=scroll,
        )

    async def drop(
        self,
        payload: DropPayload,
        position: Optional[Position],
        timeout: Optional[float],
    ) -> None:
        await self._frame._drop(
            self._selector,
            payload,
            strict=True,
            position=position,
            timeout=timeout,
        )

    @api_call(title="Evaluate")
    async def evaluate(
        self, expression: str, arg: Any, timeout: Optional[float]
    ) -> Any:
        # Python: there are no EvaluateOptions (exposeFunctions): a Python argument
        # can not hold functions.
        return await self._with_element(
            lambda h, _: h.evaluate(expression=expression, arg=arg), timeout
        )

    async def evaluate_all(self, expression: str, arg: Any) -> Any:
        return await self._frame.eval_on_selector_all(
            self._selector, expression=expression, arg=arg
        )

    @api_call(title="Evaluate")
    async def evaluate_handle(
        self, expression: str, arg: Any, timeout: Optional[float]
    ) -> "JSHandle":
        # Python: there are no EvaluateOptions (exposeFunctions), as in evaluate().
        return await self._with_element(
            lambda h, _: h.evaluate_handle(expression=expression, arg=arg), timeout
        )

    async def fill(
        self,
        value: str,
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
    ) -> None:
        return await self._frame.fill(
            self._selector,
            value,
            strict=True,
            timeout=timeout,
            no_wait_after=no_wait_after,
            force=force,
        )

    @api_call(title="Clear")
    async def clear(
        self,
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
    ) -> None:
        await self.fill("", timeout=timeout, no_wait_after=no_wait_after, force=force)

    async def _highlight(self) -> None:
        # VS Code extension uses this one, keep it for now.
        return await self._frame._highlight(self._selector, style=None)

    async def highlight(self, style: Optional[str]) -> DisposableStub:
        # Not ported: the object form of style, and cssObjectToString(), are
        # JavaScript only. The Python API takes a string.
        await self._frame._highlight(self._selector, style=style)
        return DisposableStub(lambda: self.hide_highlight())

    async def hide_highlight(self) -> None:
        await self._frame._hide_highlight(self._selector)

    def locator(
        self,
        selector_or_locator: Union[str, "Locator"],
        has_text: Optional[Union[str, Pattern[str]]],
        has_not_text: Optional[Union[str, Pattern[str]]],
        has: Optional["Locator"],
        has_not: Optional["Locator"],
    ) -> "Locator":
        if isinstance(selector_or_locator, str):
            return Locator(
                self._frame,
                self._selector + " >> " + selector_or_locator,
                has_text=has_text,
                has_not_text=has_not_text,
                has=has,
                has_not=has_not,
            )
        if selector_or_locator._frame is not self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector
            + " >> internal:chain="
            + json.dumps(selector_or_locator._selector, ensure_ascii=False),
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )

    def within(self, locator: "Locator") -> "Locator":
        return locator.locator(
            self, has_text=None, has_not_text=None, has=None, has_not=None
        )

    def get_by_test_id(self, test_id: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(
            get_by_test_id_selector(test_id_attribute_name(), test_id),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            get_by_alt_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            get_by_label_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            get_by_placeholder_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            get_by_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> "Locator":
        return self.locator(
            get_by_title_selector(text, exact=exact),
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
            get_by_role_selector(
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

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(self._frame, self._selector + " >> " + selector)

    def filter(
        self,
        has_text: Optional[Union[str, Pattern[str]]],
        has_not_text: Optional[Union[str, Pattern[str]]],
        has: Optional["Locator"],
        has_not: Optional["Locator"],
        visible: Optional[bool],
    ) -> "Locator":
        return Locator(
            self._frame,
            self._selector,
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
            visible=visible,
        )

    @property
    def visible(self) -> "Locator":
        return Locator(self._frame, self._selector, visible=True)

    async def element_handle(self, timeout: Optional[float]) -> "ElementHandle":
        # Python: the "!" of upstream is a type assertion, a cast here.
        return cast(
            "ElementHandle",
            await self._frame.wait_for_selector(
                self._selector, strict=True, state="attached", timeout=timeout
            ),
        )

    async def element_handles(self) -> List["ElementHandle"]:
        return await self._frame.query_selector_all(self._selector)

    @property
    def content_frame(self) -> "FrameLocator":
        return FrameLocator(self._frame, self._selector)

    def describe(self, description: str) -> "Locator":
        return Locator(
            self._frame,
            self._selector
            + " >> internal:describe="
            + json.dumps(description, ensure_ascii=False),
        )

    @property
    def description(self) -> Optional[str]:
        return _locator_custom_description(self._selector) or None

    @property
    def first(self) -> "Locator":
        return Locator(self._frame, self._selector + " >> nth=0")

    @property
    def last(self) -> "Locator":
        return Locator(self._frame, self._selector + " >> nth=-1")

    def nth(self, index: int) -> "Locator":
        return Locator(self._frame, self._selector + f" >> nth={index}")

    def and_(self, locator: "Locator") -> "Locator":
        if locator._frame is not self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector
            + " >> internal:and="
            + json.dumps(locator._selector, ensure_ascii=False),
        )

    def or_(self, locator: "Locator") -> "Locator":
        if locator._frame is not self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._selector
            + " >> internal:or="
            + json.dumps(locator._selector, ensure_ascii=False),
        )

    async def focus(self, timeout: Optional[float]) -> None:
        return await self._frame.focus(self._selector, strict=True, timeout=timeout)

    async def blur(self, timeout: Optional[float]) -> None:
        await self._frame._channel.blur(
            selector=self._selector,
            strict=True,
            timeout=self._frame._timeout(timeout),
        )

    async def count(self) -> int:
        return await self._frame._query_count(self._selector)

    async def normalize(self) -> "Locator":
        # Python: there is no locator generator, so the driver also generates the
        # Python code of the locator (sdkLanguage), which str() shows.
        result = await self._frame._channel.resolveSelector(
            selector=self._selector, sdkLanguage="python", timeout=NO_TIMEOUT
        )
        locator = Locator(self._frame, result["resolvedSelector"])
        locator._locator_code = result["locatorCode"]
        return locator

    async def get_attribute(self, name: str, timeout: Optional[float]) -> Optional[str]:
        return await self._frame.get_attribute(
            self._selector, name=name, strict=True, timeout=timeout
        )

    async def hover(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._frame.hover(
            self._selector,
            strict=True,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
            no_wait_after=no_wait_after,
            force=force,
            trial=trial,
            scroll=scroll,
        )

    async def inner_html(self, timeout: Optional[float]) -> str:
        return await self._frame.inner_html(
            self._selector, strict=True, timeout=timeout
        )

    async def inner_text(self, timeout: Optional[float]) -> str:
        return await self._frame.inner_text(
            self._selector, strict=True, timeout=timeout
        )

    async def input_value(self, timeout: Optional[float]) -> str:
        return await self._frame.input_value(
            self._selector, strict=True, timeout=timeout
        )

    async def is_checked(self, timeout: Optional[float]) -> bool:
        return await self._frame.is_checked(
            self._selector, strict=True, timeout=timeout
        )

    async def is_disabled(self, timeout: Optional[float]) -> bool:
        return await self._frame.is_disabled(
            self._selector, strict=True, timeout=timeout
        )

    async def is_editable(self, timeout: Optional[float]) -> bool:
        return await self._frame.is_editable(
            self._selector, strict=True, timeout=timeout
        )

    async def is_enabled(self, timeout: Optional[float]) -> bool:
        return await self._frame.is_enabled(
            self._selector, strict=True, timeout=timeout
        )

    async def is_hidden(self, timeout: Optional[float]) -> bool:
        # Python: Frame.is_hidden() takes no timeout, which is deprecated and
        # ignored.
        return await self._frame.is_hidden(self._selector, strict=True)

    async def is_visible(self, timeout: Optional[float]) -> bool:
        # Python: Frame.is_visible() takes no timeout, which is deprecated and
        # ignored.
        return await self._frame.is_visible(self._selector, strict=True)

    async def press(
        self,
        key: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        return await self._frame.press(
            self._selector,
            key,
            strict=True,
            delay=delay,
            timeout=timeout,
            no_wait_after=no_wait_after,
        )

    @api_call(title="Screenshot")
    async def screenshot(
        self,
        timeout: Optional[float],
        type: Optional[Literal["jpeg", "png", "webp"]],
        path: Optional[Union[str, pathlib.Path]],
        quality: Optional[int],
        omit_background: Optional[bool],
        animations: Optional[Literal["allow", "disabled"]],
        caret: Optional[Literal["hide", "initial"]],
        scale: Optional[Literal["css", "device"]],
        mask: Optional[Sequence["Locator"]],
        mask_color: Optional[str],
        style: Optional[str],
    ) -> bytes:
        return await self._with_element(
            lambda h, timeout: h.screenshot(
                timeout=timeout,
                type=type,
                path=path,
                quality=quality,
                omit_background=omit_background,
                animations=animations,
                caret=caret,
                scale=scale,
                mask=mask,
                mask_color=mask_color,
                style=style,
            ),
            timeout,
        )

    async def aria_snapshot(
        self,
        timeout: Optional[float],
        depth: Optional[int],
        mode: Optional[Literal["ai", "default"]],
        boxes: Optional[bool],
    ) -> str:
        result = await self._frame._channel.ariaSnapshot(
            mode=mode,
            selector=self._selector,
            depth=depth,
            boxes=boxes,
            timeout=self._frame._timeout(timeout),
        )
        return result["snapshot"]

    # Not ported: ariaSnapshotJSON() is JavaScript only (langs: js).

    @api_call(title="Scroll into view")
    async def scroll_into_view_if_needed(self, timeout: Optional[float]) -> None:
        return await self._with_element(
            lambda h, timeout: h.scroll_into_view_if_needed(timeout=timeout),
            timeout,
        )

    async def select_option(
        self,
        # Python: the values are the value, index, label and element options.
        value: Optional[Union[str, Sequence[str]]],
        index: Optional[Union[int, Sequence[int]]],
        label: Optional[Union[str, Sequence[str]]],
        element: Optional[Union["ElementHandle", Sequence["ElementHandle"]]],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
        force: Optional[bool],
    ) -> List[str]:
        return await self._frame.select_option(
            self._selector,
            value=value,
            index=index,
            label=label,
            element=element,
            strict=True,
            timeout=timeout,
            no_wait_after=no_wait_after,
            force=force,
        )

    @api_call(title="Select text")
    async def select_text(
        self, force: Optional[bool], timeout: Optional[float]
    ) -> None:
        return await self._with_element(
            lambda h, timeout: h.select_text(force=force, timeout=timeout),
            timeout,
        )

    async def set_checked(
        self,
        checked: bool,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                no_wait_after=no_wait_after,
                trial=trial,
                scroll=scroll,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                no_wait_after=no_wait_after,
                trial=trial,
                scroll=scroll,
            )

    async def set_input_files(
        self,
        files: Union[
            str,
            pathlib.Path,
            FilePayload,
            Sequence[Union[str, pathlib.Path]],
            Sequence[FilePayload],
        ],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        return await self._frame.set_input_files(
            self._selector,
            files=files,
            strict=True,
            timeout=timeout,
            no_wait_after=no_wait_after,
        )

    async def tap(
        self,
        modifiers: Optional[Sequence[KeyboardModifier]],
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._frame.tap(
            self._selector,
            strict=True,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            trial=trial,
            scroll=scroll,
        )

    async def text_content(self, timeout: Optional[float]) -> Optional[str]:
        return await self._frame.text_content(
            self._selector, strict=True, timeout=timeout
        )

    async def type(
        self,
        text: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        return await self._frame.type(
            self._selector,
            text,
            strict=True,
            delay=delay,
            timeout=timeout,
            no_wait_after=no_wait_after,
        )

    async def press_sequentially(
        self,
        text: str,
        delay: Optional[float],
        timeout: Optional[float],
        no_wait_after: Optional[bool],
    ) -> None:
        return await self.type(
            text, delay=delay, timeout=timeout, no_wait_after=no_wait_after
        )

    async def uncheck(
        self,
        position: Optional[Position],
        timeout: Optional[float],
        force: Optional[bool],
        no_wait_after: Optional[bool],
        trial: Optional[bool],
        scroll: Optional[Literal["auto", "none"]],
    ) -> None:
        return await self._frame.uncheck(
            self._selector,
            strict=True,
            position=position,
            timeout=timeout,
            force=force,
            no_wait_after=no_wait_after,
            trial=trial,
            scroll=scroll,
        )

    async def all(self) -> List["Locator"]:
        return [self.nth(i) for i in range(await self.count())]

    async def all_inner_texts(self) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, expression="ee => ee.map(e => e.innerText)", arg=None
        )

    async def all_text_contents(self) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector,
            expression="ee => ee.map(e => e.textContent || '')",
            arg=None,
        )

    async def wait_for(
        self,
        timeout: Optional[float],
        state: Optional[Literal["attached", "detached", "hidden", "visible"]],
    ) -> None:
        await self._frame._channel.waitForSelector(
            selector=self._selector,
            strict=True,
            omitReturnValue=True,
            state=state,
            timeout=self._frame._timeout(timeout),
        )

    async def wait_for_function(
        self, expression: str, arg: Any, timeout: Optional[float]
    ) -> None:
        await self._frame._channel.waitForFunction(
            selector=self._selector,
            strict=True,
            expression=expression,
            # Python: the page function is a string, which can hold a function.
            # isFunction: false would not call it; undefined lets the driver detect
            # a function.
            isFunction=None,
            arg=serialize_argument(arg),
            pollingInterval=None,
            timeout=self._frame._timeout(timeout),
        )

    async def _expect(
        self,
        expression: str,
        options: FrameExpectOptions,
        # Python: playwright/_impl/_assertions.py passes the title separately.
        title: Optional[str],
    ) -> FrameExpectResult:
        # Python: Frame._expect() takes the selector, the expression, the options
        # and the title, as playwright/_impl/_assertions.py calls it for a page.
        return await self._frame._expect(self._selector, expression, options, title)

    # Not ported: _inspect() and toString() are JavaScript only: toString() uses
    # the JavaScript locator generator. __repr__() and __str__() replace them.

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Locator frame={self._frame!r} selector={self._selector!r}>"

    def __str__(self) -> str:
        if self._locator_code is not None:
            return self._locator_code
        return self.__repr__()


class FrameLocator:
    def __init__(self, frame: "Frame", selector: str) -> None:
        self._frame = frame
        self._frame_selector = selector
        # Python: the generated API reads the event loop of each object.
        self._loop = frame._loop

    def _child_selector(self, selector: str) -> str:
        if self._frame_selector == ANY_FRAME_SELECTOR:
            return self._frame_selector + " >> " + selector
        return self._frame_selector + " >> internal:control=enter-frame >> " + selector

    def locator(
        self,
        selector_or_locator: Union[str, Locator],
        has_text: Optional[Union[str, Pattern[str]]],
        has_not_text: Optional[Union[str, Pattern[str]]],
        has: Optional[Locator],
        has_not: Optional[Locator],
    ) -> Locator:
        if isinstance(selector_or_locator, str):
            return Locator(
                self._frame,
                self._child_selector(selector_or_locator),
                has_text=has_text,
                has_not_text=has_not_text,
                has=has,
                has_not=has_not,
            )
        if selector_or_locator._frame is not self._frame:
            raise Error("Locators must belong to the same frame.")
        return Locator(
            self._frame,
            self._child_selector(selector_or_locator._selector),
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )

    def get_by_test_id(self, test_id: Union[str, Pattern[str]]) -> Locator:
        return self.locator(
            get_by_test_id_selector(test_id_attribute_name(), test_id),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            get_by_alt_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            get_by_label_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            get_by_placeholder_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            get_by_text_selector(text, exact=exact),
            has_text=None,
            has_not_text=None,
            has=None,
            has_not=None,
        )

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: Optional[bool]
    ) -> Locator:
        return self.locator(
            get_by_title_selector(text, exact=exact),
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
    ) -> Locator:
        return self.locator(
            get_by_role_selector(
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

    @property
    def owner(self) -> Locator:
        return Locator(self._frame, self._frame_selector)

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(self._frame, self._child_selector(selector))

    def _nth_selector(self, nth: str) -> str:
        if self._frame_selector == ANY_FRAME_SELECTOR:
            # Python: the message names the Python method, frame_locator(), as the
            # tests expect.
            raise Error("Selecting the nth frame is not allowed on frame_locator().")
        return self._frame_selector + f" >> nth={nth}"

    @property
    def first(self) -> "FrameLocator":
        return FrameLocator(self._frame, self._nth_selector("0"))

    @property
    def last(self) -> "FrameLocator":
        return FrameLocator(self._frame, self._nth_selector("-1"))

    def nth(self, index: int) -> "FrameLocator":
        return FrameLocator(self._frame, self._nth_selector(str(index)))

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<FrameLocator frame={self._frame!r} selector={self._frame_selector!r}>"


_test_id_attribute_name: str = "data-testid"


def test_id_attribute_name() -> str:
    return _test_id_attribute_name


def set_test_id_attribute(attribute_name: str) -> None:
    global _test_id_attribute_name
    _test_id_attribute_name = attribute_name


# Not ported: cssObjectToString(), for the JavaScript-only object form of the
# highlight style.


def _locator_custom_description(selector: str) -> Optional[str]:
    # Python: locatorCustomDescription() of isomorphic/locatorGenerators.ts parses
    # the selector and reads its last part. Python has no selector parser: it
    # matches the last part, an internal:describe with a JSON string.
    match = re.search(r'(?:^| >> )internal:describe=("(?:[^"\\]|\\.)*")$', selector)
    if not match:
        return None
    try:
        description = json.loads(match.group(1))
    except ValueError:
        return None
    if isinstance(description, str):
        return description
    return None
