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
from playwright.main import AsyncPlaywrightContextManager, SyncPlaywrightContextManager

Error = helper.Error
TimeoutError = helper.TimeoutError


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
