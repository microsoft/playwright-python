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

from typing import Union, overload

import playwright._impl._api_structures
import playwright._impl._api_types
import playwright.sync_api._generated
from playwright._impl._assertions import (
    APIResponseAssertions as APIResponseAssertionsImpl,
)
from playwright._impl._assertions import LocatorAssertions as LocatorAssertionsImpl
from playwright._impl._assertions import PageAssertions as PageAssertionsImpl
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright.sync_api._generated import (
    Accessibility,
    APIRequest,
    APIRequestContext,
    APIResponse,
    APIResponseAssertions,
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
    FrameLocator,
    JSHandle,
    Keyboard,
    Locator,
    LocatorAssertions,
    Mouse,
    Page,
    PageAssertions,
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


def sync_playwright() -> PlaywrightContextManager:
    return PlaywrightContextManager()


@overload
def expect(actual: Page) -> PageAssertions:
    ...


@overload
def expect(actual: Locator) -> LocatorAssertions:
    ...


@overload
def expect(actual: APIResponse) -> APIResponseAssertions:
    ...


def expect(
    actual: Union[Page, Locator, APIResponse]
) -> Union[PageAssertions, LocatorAssertions, APIResponseAssertions]:
    if isinstance(actual, Page):
        return PageAssertions(PageAssertionsImpl(actual._impl_obj))
    elif isinstance(actual, Locator):
        return LocatorAssertions(LocatorAssertionsImpl(actual._impl_obj))
    elif isinstance(actual, APIResponse):
        return APIResponseAssertions(APIResponseAssertionsImpl(actual._impl_obj))
    raise ValueError(f"Unsupported type: {type(actual)}")


__all__ = [
    "expect",
    "Accessibility",
    "APIRequest",
    "APIRequestContext",
    "APIResponse",
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
    "FrameLocator",
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
