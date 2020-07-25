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

import inspect
import re
from types import FunctionType
from typing import (  # type: ignore
    Any,
    List,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from playwright.accessibility import Accessibility
from playwright.browser import Browser
from playwright.browser_context import BrowserContext
from playwright.browser_server import BrowserServer
from playwright.browser_type import BrowserType
from playwright.console_message import ConsoleMessage
from playwright.dialog import Dialog
from playwright.download import Download
from playwright.element_handle import ElementHandle, ValuesToSelect
from playwright.file_chooser import FileChooser
from playwright.frame import Frame
from playwright.input import Keyboard, Mouse
from playwright.js_handle import JSHandle
from playwright.network import Request, Response, Route
from playwright.page import BindingCall, Page
from playwright.playwright import Playwright
from playwright.selectors import Selectors
from playwright.worker import Worker


def process_type(value: Any, param: bool = False) -> str:
    value = str(value)
    value = re.sub(r"<class '([^']+)'>", r"\1", value)
    if "playwright.helper" in value:
        value = re.sub(r"playwright\.helper\.", "", value)
    value = re.sub(r"playwright\.[\w]+\.([\w]+)", r'"\1"', value)
    value = re.sub(r"typing.Literal", "Literal", value)
    if param:
        value = re.sub(r"typing.Union\[([^,]+), NoneType\]", r"\1", value)
        if "Union[Literal" in value:
            value = re.sub(r"typing.Union\[(.*), NoneType\]", r"\1", value)
        else:
            value = re.sub(
                r"typing.Union\[(.*), NoneType\]", r"typing.Union[\1]", value
            )
    return value


def signature(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = ["self"]
    split = ",\n" + " " * indent

    func_signature = inspect.signature(func)
    for [name, value] in hints.items():
        if name == "return":
            continue
        processed = process_type(value, True)
        default_value = func_signature.parameters[name].default
        if default_value is not func_signature.parameters[name].empty:
            if isinstance(default_value, str):
                default_value = '"' + default_value + '"'
            elif isinstance(default_value, object):
                default_value = str(default_value)
            else:
                raise ValueError(f"value {default_value} not recognized")
            tokens.append(f"{name}: {processed} = {default_value}")
        elif name == "contentScript":
            tokens.append(f"{name}: {processed} = False")
        elif name == "arg":
            tokens.append(f"{name}: typing.Any")
        else:
            tokens.append(f"{name}: {processed}")
    return split.join(tokens)


def arguments(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = []
    split = ",\n" + " " * indent
    for [name, value] in hints.items():
        if name == "return":
            continue
        if "Callable" in str(get_origin(value)):
            # oh ah Python has a bug, list is not iterable
            args_list = get_args(value)[0]
            size = len(str(args_list).split(","))
            tokens.append(f"{name}=self._wrap_handler_{size}({name})")
        else:
            tokens.append(f"{name}={name}")
    return split.join(tokens)


def return_type(func: FunctionType) -> str:
    value = get_type_hints(func, globals())["return"]
    return process_type(value)


def short_name(t: Any) -> str:
    match = re.compile(r"playwright\.[^.]+\.([^']+)").search(str(t))
    if match:
        return match.group(1)
    return str(t)


def return_value(value: Any) -> List[str]:
    if "playwright" not in str(value) or "playwright.helper" in str(value):
        return ["", ""]
    if (
        get_origin(value) == Union
        and len(get_args(value)) == 2
        and str(get_args(value)[1]) == "<class 'NoneType'>"
    ):
        return ["mapping.from_async_nullable(", ")"]
    if str(get_origin(value)) == "<class 'list'>":
        return ["mapping.from_async_list(", ")"]
    if str(get_origin(value)) == "<class 'dict'>":
        return ["mapping.from_async_dict(", ")"]
    return ["mapping.from_async(", ")"]


def generate(t: Any) -> None:
    print("")
    class_name = short_name(t)
    base_class = t.__bases__[0].__name__
    base_sync_class = (
        "SyncBase"
        if base_class == "ChannelOwner" or base_class == "object"
        else base_class
    )
    print(f"class {class_name}({base_sync_class}):")
    print("")
    print(f"    def __init__(self, obj: {class_name}Async):")
    print("        super().__init__(obj)")
    print("")
    print(f"    def as_async(self) -> {class_name}Async:")
    print("        return self._async_obj")
    for [name, type] in get_type_hints(t, globals()).items():
        print("")
        print("    @property")
        print(f"    def {name}(self) -> {process_type(type)}:")
        [prefix, suffix] = return_value(type)
        prefix = "        return " + prefix + f"self._async_obj.{name}"
        print(f"{prefix}{suffix}")
    for [name, value] in t.__dict__.items():
        if name.startswith("_"):
            continue
        if not name.startswith("_") and str(value).startswith("<property"):
            value = value.fget
            print("")
            print("    @property")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
            )
            [prefix, suffix] = return_value(get_type_hints(value, globals())["return"])
            prefix = "        return " + prefix + f"self._async_obj.{name}"
            print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
    for [name, value] in t.__dict__.items():
        if (
            not name.startswith("_")
            and isinstance(value, FunctionType)
            and "expect_" not in name
        ):
            print("")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
            )
            [prefix, suffix] = return_value(get_type_hints(value, globals())["return"])
            prefix = "        return " + prefix + f"self._sync(self._async_obj.{name}("
            suffix = "))" + suffix
            print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
        if "expect_" in name and "expect_event" not in name:
            print("")
            return_type_value = return_type(value)
            return_type_value = re.sub(r"\"Async([^\"]+)\"", r"\1", return_type_value)
            event_name = re.sub(r"expect_(.*)", r"\1", name)
            event_name = re.sub(r"_", "", event_name)
            event_name = re.sub(r"consolemessage", "console", event_name)
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type_value}:"
            )
            print(
                f'        return EventContextManager(self, "{event_name}", predicate, timeout)'
            )

    print("")
    print(f"mapping.register({class_name}Async, {class_name})")


def main() -> None:
    assert ValuesToSelect
    print(
        """
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

import typing
import sys
from playwright.sync_base import EventContextManager, SyncBase, mapping

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

from playwright.accessibility import Accessibility as AccessibilityAsync
from playwright.browser import Browser as BrowserAsync
from playwright.browser_context import BrowserContext as BrowserContextAsync
from playwright.browser_server import BrowserServer as BrowserServerAsync
from playwright.browser_type import BrowserType as BrowserTypeAsync
from playwright.console_message import ConsoleMessage as ConsoleMessageAsync
from playwright.dialog import Dialog as DialogAsync
from playwright.download import Download as DownloadAsync
from playwright.element_handle import ElementHandle as ElementHandleAsync
from playwright.file_chooser import FileChooser as FileChooserAsync
from playwright.frame import Frame as FrameAsync
from playwright.helper import ConsoleMessageLocation, Error, FilePayload, SelectOption, Viewport, DeviceDescriptor
from playwright.input import Keyboard as KeyboardAsync, Mouse as MouseAsync
from playwright.js_handle import JSHandle as JSHandleAsync
from playwright.network import Request as RequestAsync, Response as ResponseAsync, Route as RouteAsync
from playwright.page import BindingCall as BindingCallAsync, Page as PageAsync
from playwright.playwright import Playwright as PlaywrightAsync
from playwright.selectors import Selectors as SelectorsAsync
from playwright.worker import Worker as WorkerAsync

NoneType = type(None)
"""
    )
    all_types = [
        Request,
        Response,
        Route,
        Keyboard,
        Mouse,
        JSHandle,
        ElementHandle,
        Accessibility,
        FileChooser,
        Frame,
        Worker,
        Selectors,
        ConsoleMessage,
        Dialog,
        Download,
        BindingCall,
        Page,
        BrowserContext,
        Browser,
        BrowserServer,
        BrowserType,
        Playwright,
    ]
    for t in all_types:
        generate(t)


if __name__ == "__main__":
    main()
