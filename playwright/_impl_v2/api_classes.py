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

"""Python only: the v2 class of each class in the generated API.

playwright/_impl/_api_classes.py takes these when PW_IMPL=v2 is set. The expect()
matchers are not part of the JS client; the Python ones are in assertions.py.
"""

from playwright._impl_v2.assertions import (
    APIResponseAssertions,
    LocatorAssertions,
    PageAssertions,
)
from playwright._impl_v2.browser import Browser
from playwright._impl_v2.browser_context import BrowserContext
from playwright._impl_v2.browser_type import BrowserType
from playwright._impl_v2.cdp_session import CDPSession
from playwright._impl_v2.clock import Clock
from playwright._impl_v2.console_message import ConsoleMessage
from playwright._impl_v2.credentials import Credentials
from playwright._impl_v2.debugger import Debugger
from playwright._impl_v2.dialog import Dialog
from playwright._impl_v2.disposable import Disposable
from playwright._impl_v2.download import Download
from playwright._impl_v2.element_handle import ElementHandle
from playwright._impl_v2.fetch import APIRequest, APIRequestContext, APIResponse
from playwright._impl_v2.file_chooser import FileChooser
from playwright._impl_v2.frame import Frame
from playwright._impl_v2.input import Keyboard, Mouse, Touchscreen
from playwright._impl_v2.js_handle import JSHandle
from playwright._impl_v2.locator import FrameLocator, Locator
from playwright._impl_v2.network import (
    Request,
    Response,
    Route,
    WebSocket,
    WebSocketRoute,
)
from playwright._impl_v2.page import Page
from playwright._impl_v2.playwright import Playwright
from playwright._impl_v2.screencast import Screencast
from playwright._impl_v2.selectors import Selectors
from playwright._impl_v2.tracing import Tracing
from playwright._impl_v2.video import Video
from playwright._impl_v2.web_error import WebError
from playwright._impl_v2.web_mcp import WebMCP
from playwright._impl_v2.web_storage import WebStorage
from playwright._impl_v2.worker import Worker

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
