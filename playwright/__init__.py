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
For more information you'll find the documentation for the sync API [here](sync_api.html)
and for the async API [here](async_api.html).
"""

import playwright.types as types
from playwright.main import AsyncPlaywrightContextManager, SyncPlaywrightContextManager

Error = types.Error
TimeoutError = types.TimeoutError


def async_playwright() -> AsyncPlaywrightContextManager:
    return AsyncPlaywrightContextManager()


def sync_playwright() -> SyncPlaywrightContextManager:
    return SyncPlaywrightContextManager()


__all__ = [
    "async_playwright",
    "sync_playwright",
    "Error",
    "TimeoutError",
]

__pdoc__ = {
    "accessibility": False,
    "async_base": False,
    "browser": False,
    "browser_context": False,
    "browser_type": False,
    "cdp_session": False,
    "chromium_browser_context": False,
    "connection": False,
    "console_message": False,
    "dialog": False,
    "download": False,
    "element_handle": False,
    "event_context_manager": False,
    "file_chooser": False,
    "frame": False,
    "helper": False,
    "impl_to_api_mapping": False,
    "input": False,
    "js_handle": False,
    "main": False,
    "network": False,
    "object_factory": False,
    "page": False,
    "path_utils": False,
    "playwright": False,
    "selectors": False,
    "sync_base": False,
    "transport": False,
    "wait_helper": False,
    "async_playwright": False,
    "sync_playwright": False,
}
