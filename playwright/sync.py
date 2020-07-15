# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

import types
import asyncio
from typing import Any, Dict

import playwright


loop = asyncio.get_event_loop()


class AsyncToSync:
    factories: Dict[str, Any] = {}

    def __init__(self, obj: Any) -> None:
        self.obj = obj

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("__") or name in ["obj", "factories", "gather"]:
            return super().__getattribute__(name)
        attribute_value = getattr(self.obj, name)
        if isinstance(attribute_value, types.MethodType):

            def wrap(*args: Any, **kwargs: Any) -> Any:
                value = loop.run_until_complete(attribute_value(*args, **kwargs))
                wrapper_methods = self.factories if hasattr(self, "factories") else {}
                if name in wrapper_methods:
                    return wrapper_methods[name](value)
                return value

            return wrap
        else:
            return attribute_value


class SyncElementHandle(AsyncToSync):
    pass


class SyncFrame(AsyncToSync):
    factories = {
        "querySelector": SyncElementHandle,
        "querySelectorAll": lambda items: list(map(SyncElementHandle, items)),
    }


SyncElementHandle.factories = {**SyncElementHandle.factories, **SyncFrame.factories}


class SyncPage(AsyncToSync):
    factories = SyncFrame.factories


class SyncContext(AsyncToSync):
    factories = {"newPage": SyncPage}


class SyncBrowser(AsyncToSync):
    factories = {"newPage": SyncPage, "newContext": SyncContext}


class SyncBrowserType(AsyncToSync):
    factories = {"launch": SyncBrowser}


chromium = SyncBrowserType(playwright.chromium)
firefox = SyncBrowserType(playwright.firefox)
webkit = SyncBrowserType(playwright.webkit)

browser_types = {"chromium": chromium, "firefox": firefox, "webkit": webkit}
