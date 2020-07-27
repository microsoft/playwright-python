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

import playwright.helper as helper
from playwright._repo_version import version as __version__  # noqa:F401
from playwright.async_api import Playwright as AsyncPlaywright
from playwright.main import playwright_impl
from playwright.sync_api import Playwright as SyncPlaywright

playwright_sync = SyncPlaywright(playwright_impl)
playwright_async = AsyncPlaywright(playwright_impl)

chromium = playwright_async.chromium
firefox = playwright_async.firefox
webkit = playwright_async.webkit
devices = playwright_async.devices
selectors = playwright_async.selectors
Error = helper.Error
TimeoutError = helper.TimeoutError

__all__ = [
    "playwright_sync",
    "firefox",
    "webkit",
    "devices",
    "selectors",
    "Error",
    "TimeoutError",
]
