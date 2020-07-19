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

from playwright.browser import Browser
from playwright.browser_context import BrowserContext
from playwright.browser_server import BrowserServer
from playwright.browser_type import BrowserType
from playwright.connection import ChannelOwner, ConnectionScope
from playwright.console_message import ConsoleMessage
from playwright.dialog import Dialog
from playwright.download import Download
from playwright.element_handle import ElementHandle
from playwright.frame import Frame
from playwright.js_handle import JSHandle
from playwright.network import Request, Response, Route
from playwright.page import BindingCall, Page
from playwright.playwright import Playwright
from playwright.worker import Worker
from typing import Any, Dict


class DummyObject(ChannelOwner):
    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)


def create_remote_object(
    scope: ConnectionScope, type: str, guid: str, initializer: Dict
) -> Any:
    if type == "bindingCall":
        return BindingCall(scope, guid, initializer)
    if type == "browser":
        return Browser(scope, guid, initializer)
    if type == "browserServer":
        return BrowserServer(scope, guid, initializer)
    if type == "browserType":
        return BrowserType(scope, guid, initializer)
    if type == "context":
        return BrowserContext(scope, guid, initializer)
    if type == "consoleMessage":
        return ConsoleMessage(scope, guid, initializer)
    if type == "dialog":
        return Dialog(scope, guid, initializer)
    if type == "download":
        return Download(scope, guid, initializer)
    if type == "elementHandle":
        return ElementHandle(scope, guid, initializer)
    if type == "frame":
        return Frame(scope, guid, initializer)
    if type == "jsHandle":
        return JSHandle(scope, guid, initializer)
    if type == "page":
        return Page(scope, guid, initializer)
    if type == "playwright":
        return Playwright(scope, guid, initializer)
    if type == "request":
        return Request(scope, guid, initializer)
    if type == "response":
        return Response(scope, guid, initializer)
    if type == "route":
        return Route(scope, guid, initializer)
    if type == "worker":
        return Worker(scope, guid, initializer)
    return DummyObject(scope, guid, initializer)
