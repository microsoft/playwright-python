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
# holds each class. The expect() matchers are not part of the JS client; the
# Python ones are in assertions.py.

from playwright._impl.assertions import (
    APIResponseAssertions,
    LocatorAssertions,
    PageAssertions,
)
from playwright._impl.browser import Browser
from playwright._impl.browser_context import BrowserContext
from playwright._impl.browser_type import BrowserType
from playwright._impl.cdp_session import CDPSession
from playwright._impl.clock import Clock
from playwright._impl.console_message import ConsoleMessage
from playwright._impl.credentials import Credentials
from playwright._impl.debugger import Debugger
from playwright._impl.dialog import Dialog
from playwright._impl.disposable import Disposable
from playwright._impl.download import Download
from playwright._impl.element_handle import ElementHandle
from playwright._impl.fetch import APIRequest, APIRequestContext, APIResponse
from playwright._impl.file_chooser import FileChooser
from playwright._impl.frame import Frame
from playwright._impl.input import Keyboard, Mouse, Touchscreen
from playwright._impl.js_handle import JSHandle
from playwright._impl.locator import FrameLocator, Locator
from playwright._impl.network import (
    Request,
    Response,
    Route,
    WebSocket,
    WebSocketRoute,
)
from playwright._impl.page import Page
from playwright._impl.playwright import Playwright
from playwright._impl.screencast import Screencast
from playwright._impl.selectors import Selectors
from playwright._impl.tracing import Tracing
from playwright._impl.video import Video
from playwright._impl.web_error import WebError
from playwright._impl.web_mcp import WebMCP
from playwright._impl.web_storage import WebStorage
from playwright._impl.worker import Worker

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
