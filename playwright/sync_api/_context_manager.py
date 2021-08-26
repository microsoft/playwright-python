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

import asyncio
from typing import Any

from greenlet import greenlet

from playwright._impl._api_types import Error
from playwright._impl._connection import Connection
from playwright._impl._driver import compute_driver_executable
from playwright._impl._object_factory import create_remote_object
from playwright._impl._playwright import Playwright
from playwright._impl._transport import PipeTransport
from playwright.sync_api._generated import Playwright as SyncPlaywright


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._playwright: SyncPlaywright

    def __enter__(self) -> SyncPlaywright:
        loop: asyncio.AbstractEventLoop
        own_loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            own_loop = loop
        if loop.is_running():
            raise Error(
                """It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead."""
            )

        def greenlet_main() -> None:
            loop.run_until_complete(self._connection.run_as_sync())

            if own_loop:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        dispatcher_fiber = greenlet(greenlet_main)
        self._connection = Connection(
            dispatcher_fiber,
            create_remote_object,
            PipeTransport(loop, compute_driver_executable()),
        )

        g_self = greenlet.getcurrent()

        def callback_wrapper(playwright_impl: Playwright) -> None:
            self._playwright = SyncPlaywright(playwright_impl)
            g_self.switch()

        self._connection.call_on_object_with_known_name("Playwright", callback_wrapper)

        dispatcher_fiber.switch()
        playwright = self._playwright
        playwright.stop = self.__exit__  # type: ignore
        return playwright

    def start(self) -> SyncPlaywright:
        return self.__enter__()

    def __exit__(self, *args: Any) -> None:
        self._connection.stop_sync()
