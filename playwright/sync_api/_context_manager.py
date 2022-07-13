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
from typing import Any, Optional

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
        self._loop: asyncio.AbstractEventLoop
        self._own_loop = False
        self._watcher: Optional[asyncio.AbstractChildWatcher] = None

    def __enter__(self) -> SyncPlaywright:
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            self._own_loop = True
        if self._loop.is_running():
            raise Error(
                """It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead."""
            )

        # In Python 3.7, asyncio.Process.wait() hangs because it does not use ThreadedChildWatcher
        # which is used in Python 3.8+. This is unix specific and also takes care about
        # cleaning up zombie processes. See https://bugs.python.org/issue35621
        if (
            sys.version_info[0] == 3
            and sys.version_info[1] == 7
            and sys.platform != "win32"
            and isinstance(asyncio.get_child_watcher(), asyncio.SafeChildWatcher)
        ):
            from ._py37ThreadedChildWatcher import ThreadedChildWatcher  # type: ignore

            self._watcher = ThreadedChildWatcher()
            asyncio.set_child_watcher(self._watcher)  # type: ignore

        # Create a new fiber for the protocol dispatcher. It will be pumping events
        # until the end of times. We will pass control to that fiber every time we
        # block while waiting for a response.
        def greenlet_main() -> None:
            self._loop.run_until_complete(self._connection.run_as_sync())

        dispatcher_fiber = greenlet(greenlet_main)

        self._connection = Connection(
            dispatcher_fiber,
            create_remote_object,
            PipeTransport(self._loop, compute_driver_executable()),
            self._loop,
        )

        g_self = greenlet.getcurrent()

        def callback_wrapper(playwright_impl: Playwright) -> None:
            self._playwright = SyncPlaywright(playwright_impl)
            g_self.switch()

        # Switch control to the dispatcher, it'll fire an event and pass control to
        # the calling greenlet.
        self._connection.call_on_object_with_known_name("Playwright", callback_wrapper)
        dispatcher_fiber.switch()

        playwright = self._playwright
        playwright.stop = self.__exit__  # type: ignore
        return playwright

    def start(self) -> SyncPlaywright:
        return self.__enter__()

    def __exit__(self, *args: Any) -> None:
        self._connection.stop_sync()
        if self._watcher:
            self._watcher.close()
        if self._own_loop:
            tasks = asyncio.all_tasks(self._loop)
            for t in [t for t in tasks if not (t.done() or t.cancelled())]:
                t.cancel()
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
