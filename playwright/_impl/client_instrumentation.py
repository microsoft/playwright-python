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

"""Port of packages/playwright-core/src/client/clientInstrumentation.ts.

Python: the Proxy that forwards each call to the listeners is a class with the
methods of the ClientInstrumentation interface.
"""

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl.browser_context import BrowserContext
    from playwright._impl.fetch import APIRequestContext
    from playwright._impl.page import Page

# Instrumentation can mutate the data, for example assign the callId.
# Python: the ApiZone of the call, which has the fields of the JS interface.
ApiCallData = Any


class ClientInstrumentationListener:
    pass


class ClientInstrumentation:
    def __init__(self) -> None:
        self._listeners: List[Any] = []

    def add_listener(self, listener: Any) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: Any) -> None:
        # Python: listeners.splice(listeners.indexOf(listener), 1), which removes the
        # last listener when this one is not there.
        if not self._listeners:
            return
        index = self._listeners.index(listener) if listener in self._listeners else -1
        del self._listeners[index]

    def remove_all_listeners(self) -> None:
        self._listeners.clear()

    def _on(self, name: str, *params: Any) -> None:
        for listener in self._listeners:
            method = getattr(listener, name, None)
            if method:
                method(*params)

    async def _run(self, name: str, *params: Any) -> None:
        for listener in self._listeners:
            method = getattr(listener, name, None)
            if method:
                await method(*params)

    def on_api_call_begin(self, api_call: ApiCallData, channel: Dict[str, Any]) -> None:
        self._on("on_api_call_begin", api_call, channel)

    def on_api_call_end(self, api_call: ApiCallData) -> None:
        self._on("on_api_call_end", api_call)

    def on_will_pause(self, options: Dict[str, Any]) -> None:
        self._on("on_will_pause", options)

    def on_page(self, page: "Page") -> None:
        self._on("on_page", page)

    async def run_before_create_browser_context(self, options: Dict[str, Any]) -> None:
        await self._run("run_before_create_browser_context", options)

    async def run_before_create_request_context(self, options: Dict[str, Any]) -> None:
        await self._run("run_before_create_request_context", options)

    async def run_after_create_browser_context(self, context: "BrowserContext") -> None:
        await self._run("run_after_create_browser_context", context)

    async def run_after_create_request_context(
        self, context: "APIRequestContext"
    ) -> None:
        await self._run("run_after_create_request_context", context)

    async def run_before_close_browser_context(self, context: "BrowserContext") -> None:
        await self._run("run_before_close_browser_context", context)

    async def run_before_close_request_context(
        self, context: "APIRequestContext"
    ) -> None:
        await self._run("run_before_close_request_context", context)


def create_instrumentation() -> ClientInstrumentation:
    return ClientInstrumentation()
