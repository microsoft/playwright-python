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

import pathlib
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)

from playwright._impl._api_structures import FilePayload, FloatRect, Position
from playwright._impl._element_handle import ElementHandle
from playwright._impl._helper import (
    Error,
    KeyboardModifier,
    MouseButton,
    locals_to_params,
    monotonic_time,
)
from playwright._impl._js_handle import Serializable

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame
    from playwright._impl._js_handle import JSHandle

T = TypeVar("T")


class Locator:
    def __init__(self, frame: "Frame", selector: str) -> None:
        self._frame = frame
        self._selector = selector
        self._loop = frame._loop
        self._dispatcher_fiber = frame._connection._dispatcher_fiber

    def __repr__(self) -> str:
        return f"<Locator frame={self._frame!r} selector={self._selector!r}>"

    async def _with_element(
        self,
        task: Callable[[ElementHandle, float], Awaitable[T]],
        timeout: float = None,
    ) -> T:
        timeout = self._frame.page._timeout_settings.timeout(timeout)
        deadline = (monotonic_time() + timeout) if timeout else 0
        handle = await self.element_handle(timeout=timeout)
        if not handle:
            raise Error(f"Could not resolve {self._selector} to DOM Element")
        try:
            return await task(
                handle,
                (deadline - monotonic_time()) if deadline else 0,
            )
        finally:
            await handle.dispose()

    async def bounding_box(self, timeout: float = None) -> Optional[FloatRect]:
        return await self._with_element(
            lambda h, _: h.bounding_box(),
            timeout,
        )

    async def check(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.check(self._selector, strict=True, **params)

    async def click(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.click(self._selector, strict=True, **params)

    async def dblclick(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.dblclick(self._selector, strict=True, **params)

    async def dispatch_event(
        self,
        type: str,
        eventInit: Dict = None,
        timeout: float = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.dispatch_event(self._selector, strict=True, **params)

    async def evaluate(
        self, expression: str, arg: Serializable = None, timeout: float = None
    ) -> Any:
        return await self._with_element(
            lambda h, _: h.evaluate(expression, arg),
            timeout,
        )

    async def evaluate_all(self, expression: str, arg: Serializable = None) -> Any:
        params = locals_to_params(locals())
        return await self._frame.eval_on_selector_all(self._selector, **params)

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None, timeout: float = None
    ) -> "JSHandle":
        return await self._with_element(
            lambda h, o: h.evaluate_handle(expression, arg), timeout
        )

    async def fill(
        self,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.fill(self._selector, strict=True, **params)

    def locator(
        self,
        selector: str,
    ) -> "Locator":
        return Locator(self._frame, f"{self._selector} >> {selector}")

    async def element_handle(
        self,
        timeout: float = None,
    ) -> ElementHandle:
        params = locals_to_params(locals())
        return cast(
            ElementHandle,
            await self._frame.wait_for_selector(
                self._selector, strict=True, state="attached", **params
            ),
        )

    async def element_handles(self) -> List[ElementHandle]:
        return await self._frame.query_selector_all(self._selector)

    @property
    def first(self) -> "Locator":
        return Locator(self._frame, f"{self._selector} >>  nth=0")

    @property
    def last(self) -> "Locator":
        return Locator(self._frame, f"{self._selector} >>  nth=-1")

    def nth(self, index: int) -> "Locator":
        return Locator(self._frame, f"{self._selector} >>  nth={index}")

    async def focus(self, timeout: float = None) -> None:
        params = locals_to_params(locals())
        return await self._frame.focus(self._selector, strict=True, **params)

    async def count(
        self,
    ) -> int:
        return cast(int, await self.evaluate_all("ee => ee.length"))

    async def get_attribute(self, name: str, timeout: float = None) -> Optional[str]:
        params = locals_to_params(locals())
        return await self._frame.get_attribute(
            self._selector,
            strict=True,
            **params,
        )

    async def hover(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.hover(
            self._selector,
            strict=True,
            **params,
        )

    async def inner_html(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.inner_html(
            self._selector,
            strict=True,
            **params,
        )

    async def inner_text(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.inner_text(
            self._selector,
            strict=True,
            **params,
        )

    async def input_value(self, timeout: float = None) -> str:
        params = locals_to_params(locals())
        return await self._frame.input_value(
            self._selector,
            strict=True,
            **params,
        )

    async def is_checked(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_checked(
            self._selector,
            strict=True,
            **params,
        )

    async def is_disabled(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_disabled(
            self._selector,
            strict=True,
            **params,
        )

    async def is_editable(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_editable(
            self._selector,
            strict=True,
            **params,
        )

    async def is_enabled(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_editable(
            self._selector,
            strict=True,
            **params,
        )

    async def is_hidden(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_hidden(
            self._selector,
            strict=True,
            **params,
        )

    async def is_visible(self, timeout: float = None) -> bool:
        params = locals_to_params(locals())
        return await self._frame.is_visible(
            self._selector,
            strict=True,
            **params,
        )

    async def press(
        self,
        key: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.press(self._selector, strict=True, **params)

    async def screenshot(
        self,
        timeout: float = None,
        type: Literal["jpeg", "png"] = None,
        path: Union[str, pathlib.Path] = None,
        quality: int = None,
        omitBackground: bool = None,
    ) -> bytes:
        params = locals_to_params(locals())
        return await self._with_element(
            lambda h, timeout: h.screenshot(timeout=timeout, **params)
        )

    async def scroll_into_view_if_needed(
        self,
        timeout: float = None,
    ) -> None:
        return await self._with_element(
            lambda h, timeout: h.scroll_into_view_if_needed(timeout=timeout),
            timeout,
        )

    async def select_option(
        self,
        value: Union[str, List[str]] = None,
        index: Union[int, List[int]] = None,
        label: Union[str, List[str]] = None,
        element: Union["ElementHandle", List["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
    ) -> List[str]:
        params = locals_to_params(locals())
        return await self._frame.select_option(
            self._selector,
            strict=True,
            **params,
        )

    async def select_text(self, force: bool = None, timeout: float = None) -> None:
        params = locals_to_params(locals())
        return await self._with_element(
            lambda h, timeout: h.select_text(timeout=timeout, **params), timeout
        )

    async def set_input_files(
        self,
        files: Union[
            str,
            pathlib.Path,
            FilePayload,
            List[Union[str, pathlib.Path]],
            List[FilePayload],
        ],
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.set_input_files(
            self._selector,
            strict=True,
            **params,
        )

    async def tap(
        self,
        modifiers: List[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.tap(
            self._selector,
            strict=True,
            **params,
        )

    async def text_content(self, timeout: float = None) -> Optional[str]:
        params = locals_to_params(locals())
        return await self._frame.text_content(
            self._selector,
            strict=True,
            **params,
        )

    async def type(
        self,
        text: str,
        delay: float = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.type(
            self._selector,
            strict=True,
            **params,
        )

    async def uncheck(
        self,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        return await self._frame.uncheck(
            self._selector,
            strict=True,
            **params,
        )

    async def all_inner_texts(
        self,
    ) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, "ee => ee.map(e => e.innerText)"
        )

    async def all_text_contents(
        self,
    ) -> List[str]:
        return await self._frame.eval_on_selector_all(
            self._selector, "ee => ee.map(e => e.textContent || '')"
        )

    async def set_checked(
        self,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
                trial=trial,
            )
        else:
            await self.uncheck(
                position=position,
                timeout=timeout,
                force=force,
                noWaitAfter=noWaitAfter,
                trial=trial,
            )
