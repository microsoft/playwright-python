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

# The implementation of every class in the generated API. The generated API
# imports them from here, so the generator does not need to know which module
# holds each class.

from playwright._impl._assertions import (
    APIResponseAssertions,
    LocatorAssertions,
    PageAssertions,
)
from playwright._impl._browser import Browser
from playwright._impl._browser_context import BrowserContext
from playwright._impl._browser_type import BrowserType
from playwright._impl._cdp_session import CDPSession
from playwright._impl._clock import Clock
from playwright._impl._console_message import ConsoleMessage
from playwright._impl._credentials import Credentials
from playwright._impl._debugger import Debugger
from playwright._impl._dialog import Dialog
from playwright._impl._disposable import Disposable
from playwright._impl._download import Download
from playwright._impl._element_handle import ElementHandle
from playwright._impl._fetch import APIRequest, APIRequestContext, APIResponse
from playwright._impl._file_chooser import FileChooser
from playwright._impl._frame import Frame
from playwright._impl._input import Keyboard, Mouse, Touchscreen
from playwright._impl._js_handle import JSHandle
from playwright._impl._locator import FrameLocator, Locator
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocket,
    WebSocketRoute,
)
from playwright._impl._page import Page, Worker
from playwright._impl._playwright import Playwright
from playwright._impl._screencast import Screencast
from playwright._impl._selectors import Selectors
from playwright._impl._tracing import Tracing
from playwright._impl._video import Video
from playwright._impl._web_error import WebError
from playwright._impl._web_mcp import WebMCP
from playwright._impl._web_storage import WebStorage

__all__ = [
    "APIRequest",
    "APIRequestContext",
    "APIResponse",
    "APIResponseAssertions",
    "Browser",
    "BrowserContext",
    "BrowserType",
    "CDPSession",
    "Clock",
    "ConsoleMessage",
    "Credentials",
    "Debugger",
    "Dialog",
    "Disposable",
    "Download",
    "ElementHandle",
    "FileChooser",
    "Frame",
    "FrameLocator",
    "JSHandle",
    "Keyboard",
    "Locator",
    "LocatorAssertions",
    "Mouse",
    "Page",
    "PageAssertions",
    "Playwright",
    "Request",
    "Response",
    "Route",
    "Screencast",
    "Selectors",
    "Touchscreen",
    "Tracing",
    "Video",
    "WebError",
    "WebMCP",
    "WebSocket",
    "WebSocketRoute",
    "WebStorage",
    "Worker",
]
