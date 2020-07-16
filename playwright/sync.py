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

from asyncio.futures import Future
from playwright.download import Download
import types
import asyncio
from typing import Any, Callable, Dict

import playwright


loop = asyncio.get_event_loop()


class GetWrapper:
    def __init__(self, cb: Callable[..., Any]) -> None:
        self.cb = cb

    @property
    def value(self) -> Any:
        return self.cb()


class SyncWaitContextManager:
    def __init__(self, future: Future) -> None:
        self.result: Any = None
        self.async_wrapper = asyncio.ensure_future(future)
        self.async_wrapper.add_done_callback(self._handle_done)

    def _handle_done(self, value: Any) -> None:
        result = value.result()
        if isinstance(result, Download):
            self.result = SyncDownload(result)
        else:
            self.result = result

    def __enter__(self) -> GetWrapper:
        return GetWrapper(lambda: self.result)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if not self.async_wrapper.done():
            loop.run_until_complete(self.async_wrapper)


class AsyncToSync:
    factories: Dict[str, Any] = {}

    def __init__(self, obj: Any) -> None:
        self.obj = obj

    def __str__(self) -> str:
        return self.obj.__str__()

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("__") or name in [
            "obj",
            "factories",
            "withWaitForEvent",
            "withWaitForSelector",
        ]:
            return super().__getattribute__(name)
        attribute_value = getattr(self.obj, name)
        if isinstance(attribute_value, types.MethodType):

            def wrap(*args: Any, **kwargs: Any) -> Any:
                value = attribute_value(*args, **kwargs)
                if asyncio.isfuture(value) or asyncio.iscoroutine(value):
                    value = loop.run_until_complete(value)
                if name in self.factories:
                    return self.factories[name](value)
                return value

            return wrap
        elif isinstance(attribute_value, list):
            if name in self.factories:
                return self.factories[name](attribute_value)
            return attribute_value
        else:
            return attribute_value


class SyncDownload(AsyncToSync):
    pass


class SyncDialog(AsyncToSync):
    pass


class SyncJSHandle(AsyncToSync):
    pass


class SyncConsoleMessage(AsyncToSync):
    factories = {
        "args": lambda items: list(map(SyncJSHandle, items)),
    }

    pass


class SyncWorker(AsyncToSync):
    pass


class SyncElementHandle(AsyncToSync):
    pass


class SyncFrame(AsyncToSync):
    factories = {
        "querySelector": SyncElementHandle,
        "querySelectorAll": lambda items: list(map(SyncElementHandle, items)),
    }


SyncElementHandle.factories = {**SyncElementHandle.factories, **SyncFrame.factories}


class SyncPage(AsyncToSync):
    factories: Dict[str, Any] = {
        **SyncFrame.factories,
        "workers": lambda items: list(map(SyncWorker, items)),
    }

    def withWaitForEvent(self, *args: Any, **kwargs: Any) -> SyncWaitContextManager:
        return SyncWaitContextManager(self.obj.waitForEvent(*args, **kwargs))

    def withWaitForSelector(self, *args: Any, **kwargs: Any) -> SyncWaitContextManager:
        return SyncWaitContextManager(self.obj.waitForSelector(*args, **kwargs))


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
