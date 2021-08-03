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

"""
Python package `playwright` is a Python library to automate Chromium,
Firefox and WebKit with a single API. Playwright is built to enable cross-browser
web automation that is ever-green, capable, reliable and fast.
"""

import playwright._impl._api_structures
import playwright._impl._api_types
import playwright.async_api._generated
from playwright.async_api._context_manager import PlaywrightContextManager
from playwright.async_api._generated import (
    Accessibility,
    Browser,
    BrowserContext,
    BrowserType,
    CDPSession,
    ConsoleMessage,
    Dialog,
    Download,
    ElementHandle,
    FileChooser,
    Frame,
    JSHandle,
    Keyboard,
    Locator,
    Mouse,
    Page,
    Playwright,
    Request,
    Response,
    Route,
    Selectors,
    Touchscreen,
    Video,
    WebSocket,
    Worker,
)

ChromiumBrowserContext = BrowserContext

Cookie = playwright._impl._api_structures.Cookie
FilePayload = playwright._impl._api_structures.FilePayload
FloatRect = playwright._impl._api_structures.FloatRect
Geolocation = playwright._impl._api_structures.Geolocation
HttpCredentials = playwright._impl._api_structures.HttpCredentials
PdfMargins = playwright._impl._api_structures.PdfMargins
Position = playwright._impl._api_structures.Position
ProxySettings = playwright._impl._api_structures.ProxySettings
ResourceTiming = playwright._impl._api_structures.ResourceTiming
SourceLocation = playwright._impl._api_structures.SourceLocation
StorageState = playwright._impl._api_structures.StorageState
ViewportSize = playwright._impl._api_structures.ViewportSize

Error = playwright._impl._api_types.Error
TimeoutError = playwright._impl._api_types.TimeoutError


def async_playwright() -> PlaywrightContextManager:
    return PlaywrightContextManager()


__all__ = [
    "async_playwright",
    "Accessibility",
    "BindingCall",
    "Browser",
    "BrowserContext",
    "BrowserType",
    "CDPSession",
    "ChromiumBrowserContext",
    "ConsoleMessage",
    "Cookie",
    "Dialog",
    "Download",
    "ElementHandle",
    "Error",
    "FileChooser",
    "FilePayload",
    "FloatRect",
    "Frame",
    "Geolocation",
    "HttpCredentials",
    "JSHandle",
    "Keyboard",
    "Locator",
    "Mouse",
    "Page",
    "PdfMargins",
    "Position",
    "Playwright",
    "ProxySettings",
    "Request",
    "ResourceTiming",
    "Response",
    "Route",
    "Selectors",
    "SourceLocation",
    "StorageState",
    "sync_playwright",
    "TimeoutError",
    "Touchscreen",
    "Video",
    "ViewportSize",
    "WebSocket",
    "Worker",
]
