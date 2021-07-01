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

import re
from types import FunctionType
from typing import (  # type: ignore
    Any,
    List,
    Match,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from playwright._impl._accessibility import Accessibility
from playwright._impl._browser import Browser
from playwright._impl._browser_context import BrowserContext
from playwright._impl._browser_type import BrowserType
from playwright._impl._cdp_session import CDPSession
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._dialog import Dialog
from playwright._impl._download import Download
from playwright._impl._element_handle import ElementHandle
from playwright._impl._file_chooser import FileChooser
from playwright._impl._frame import Frame
from playwright._impl._helper import to_snake_case
from playwright._impl._input import Keyboard, Mouse, Touchscreen
from playwright._impl._js_handle import JSHandle, Serializable
from playwright._impl._network import Request, Response, Route, WebSocket
from playwright._impl._page import Page, Worker
from playwright._impl._playwright import Playwright
from playwright._impl._selectors import Selectors
from playwright._impl._tracing import Tracing
from playwright._impl._video import Video


def process_type(value: Any, param: bool = False) -> str:
    value = str(value)
    value = re.sub(r"<class '([^']+)'>", r"\1", value)
    value = re.sub(r"playwright\._impl\._api_structures.([\w]+)", r"\1", value)
    value = re.sub(r"playwright\._impl\.[\w]+\.([\w]+)", r'"\1"', value)
    value = re.sub(r"typing.Literal", "Literal", value)
    if param:
        value = re.sub(r"^typing.Union\[([^,]+), NoneType\]$", r"\1 = None", value)
        value = re.sub(
            r"typing.Union\[(Literal\[[^\]]+\]), NoneType\]", r"\1 = None", value
        )
        value = re.sub(
            r"^typing.Union\[(.+), NoneType\]$", r"typing.Union[\1] = None", value
        )

        value = re.sub(r"^typing.Optional\[([^,]+)\]$", r"\1 = None", value)
        value = re.sub(r"typing.Optional\[(Literal\[[^\]]+\])\]", r"\1 = None", value)
        value = re.sub(
            r"^typing.Optional\[(.+)\]$", r"typing.Optional[\1] = None", value
        )
    return value


positional_exceptions = [
    r"abort\.errorCode",
    r"accept\.promptText",
    r"add_init_script\.script",
    r"cookies\.urls",
    r"dispatch_event\.eventInit",
    r"eval.*\.arg",
    r"expect_.*\.predicate",
    r"evaluate_handle\.arg",
    r"frame.*\.name",
    r"register\.script",
    r"select_option\.value",
    r"send\.params",
    r"set_geolocation\.geolocation",
    r"wait_for_.*\.predicate",
    r"wait_for_load_state\.state",
    r"unroute\.handler",
]


def is_positional_exception(key: str) -> bool:
    for pattern in positional_exceptions:
        if re.match(pattern, key):
            return True
    return False


def signature(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = ["self"]
    split = ",\n" + " " * indent

    saw_optional = False
    for [name, value] in hints.items():
        if name == "return":
            continue
        positional_exception = is_positional_exception(f"{func.__name__}.{name}")
        if saw_optional and positional_exception:
            raise Exception(
                "Positional exception is not first in the list "
                + f"{func.__name__}.{name}"
            )
        if (
            not positional_exception
            and not saw_optional
            and (
                str(value).endswith("NoneType]")
                or str(value).startswith("typing.Optional")
            )
        ):
            saw_optional = True
            tokens.append("*")
        processed = process_type(value, True)
        tokens.append(f"{to_snake_case(name)}: {processed}")
    return split.join(tokens)


def arguments(func: FunctionType, indent: int) -> str:
    hints = get_type_hints(func, globals())
    tokens = []
    split = ",\n" + " " * indent
    for [name, value] in hints.items():
        value_str = str(value)
        if name == "return":
            continue
        if "Callable" in value_str:
            tokens.append(f"{name}=self._wrap_handler({to_snake_case(name)})")
        elif (
            "typing.Any" in value_str
            or "typing.Dict" in value_str
            or "Handle" in value_str
        ):
            tokens.append(f"{name}=mapping.to_impl({to_snake_case(name)})")
        elif (
            re.match(r"<class 'playwright\._impl\.[\w]+\.[\w]+", value_str)
            and "_api_structures" not in value_str
        ):
            tokens.append(f"{name}={to_snake_case(name)}._impl_obj")
        elif (
            re.match(r"typing\.Optional\[playwright\._impl\.[\w]+\.[\w]+\]", value_str)
            and "_api_structures" not in value_str
        ):
            tokens.append(
                f"{name}={to_snake_case(name)}._impl_obj if {to_snake_case(name)} else None"
            )
        else:
            tokens.append(f"{name}={to_snake_case(name)}")
    return split.join(tokens)


def return_type(func: FunctionType) -> str:
    value = get_type_hints(func, globals())["return"]
    return process_type(value)


def short_name(t: Any) -> str:
    match = cast(
        Match[str], re.compile(r"playwright\._impl\.[^.]+\.([^']+)").search(str(t))
    )
    return match.group(1)


def return_value(value: Any) -> List[str]:
    value_str = str(value)
    if "playwright" not in value_str:
        return ["mapping.from_maybe_impl(", ")"]
    if (
        get_origin(value) == Union
        and len(get_args(value)) == 2
        and str(get_args(value)[1]) == "<class 'NoneType'>"
    ):
        return ["mapping.from_impl_nullable(", ")"]
    if str(get_origin(value)) == "<class 'list'>":
        return ["mapping.from_impl_list(", ")"]
    if str(get_origin(value)) == "<class 'dict'>":
        return ["mapping.from_impl_dict(", ")"]
    return ["mapping.from_impl(", ")"]


header = """
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
import pathlib

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal


from playwright._impl._accessibility import Accessibility as AccessibilityImpl
from playwright._impl._api_structures import Cookie, FloatRect, FilePayload, Geolocation, HttpCredentials, PdfMargins, Position, ProxySettings, ResourceTiming, SourceLocation, StorageState, ViewportSize, RemoteAddr, SecurityDetails
from playwright._impl._browser import Browser as BrowserImpl
from playwright._impl._browser_context import BrowserContext as BrowserContextImpl
from playwright._impl._browser_type import BrowserType as BrowserTypeImpl
from playwright._impl._cdp_session import CDPSession as CDPSessionImpl
from playwright._impl._console_message import ConsoleMessage as ConsoleMessageImpl
from playwright._impl._dialog import Dialog as DialogImpl
from playwright._impl._download import Download as DownloadImpl
from playwright._impl._element_handle import ElementHandle as ElementHandleImpl
from playwright._impl._file_chooser import FileChooser as FileChooserImpl
from playwright._impl._frame import Frame as FrameImpl
from playwright._impl._input import Keyboard as KeyboardImpl, Mouse as MouseImpl, Touchscreen as TouchscreenImpl
from playwright._impl._js_handle import JSHandle as JSHandleImpl
from playwright._impl._network import Request as RequestImpl, Response as ResponseImpl, Route as RouteImpl, WebSocket as WebSocketImpl
from playwright._impl._page import Page as PageImpl, Worker as WorkerImpl
from playwright._impl._playwright import Playwright as PlaywrightImpl
from playwright._impl._selectors import Selectors as SelectorsImpl
from playwright._impl._video import Video as VideoImpl
from playwright._impl._tracing import Tracing as TracingImpl

"""


all_types = [
    Request,
    Response,
    Route,
    WebSocket,
    Keyboard,
    Mouse,
    Touchscreen,
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
    Video,
    Page,
    BrowserContext,
    CDPSession,
    Browser,
    BrowserType,
    Playwright,
    Tracing,
]

api_globals = globals()
assert Serializable
