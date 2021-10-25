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
import sys
from typing import Any

from greenlet import greenlet

from playwright._impl._api_types import Error
from playwright._impl._connection import Connection
from playwright._impl._driver import compute_driver_executable
from playwright._impl._object_factory import create_remote_object
from playwright._impl._playwright import Playwright
from playwright._impl._transport import PipeTransport
from playwright.sync_api._generated import Playwright as SyncPlaywright

# Used for sync API tests
dispatcher_fiber: Any = None


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._playwright: SyncPlaywright
        self._loop: asyncio.AbstractEventLoop
        self._own_loop = False

    def __enter__(self) -> SyncPlaywright:
        try:
            self._loop = loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = loop = asyncio.new_event_loop()
            self._own_loop = True
        if loop.is_running():
            raise Error(
                """It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead."""
            )

        def greenlet_main() -> None:
            loop.run_until_complete(self._connection.run_as_sync())

        global dispatcher_fiber
        dispatcher_fiber = greenlet(greenlet_main)
        self._connection = Connection(
            dispatcher_fiber,
            create_remote_object,
            PipeTransport(loop, compute_driver_executable()),
            loop,
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
        # In Python 3.7, self._connection._transport.wait_until_stopped() hangs because
        # it does not uses ThreadedChildWatcher which is used in Python 3.8+.
        # Hence waiting for child process is skipped in Python 3.7.
        # See https://bugs.python.org/issue35621
        # See https://stackoverflow.com/questions/28915607/does-asyncio-support-running-a-subprocess-from-a-non-main-thread/28917653#28917653
        if sys.version_info >= (3, 8):
            self._loop.run_until_complete(
                self._connection._transport.wait_until_stopped()
            )
        if self._own_loop:
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
