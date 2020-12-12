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
import inspect
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from greenlet import greenlet

import playwright
from playwright._connection import Connection
from playwright._object_factory import create_remote_object
from playwright._playwright import Playwright
from playwright._types import Error
from playwright.async_api import Playwright as AsyncPlaywright
from playwright.sync_api import Playwright as SyncPlaywright


def compute_driver_executable() -> Path:
    package_path = Path(inspect.getfile(playwright)).parent
    platform = sys.platform
    if platform == "win32":
        return package_path / "driver" / "playwright-cli.exe"
    return package_path / "driver" / "playwright-cli"


class SyncPlaywrightContextManager:
    def __init__(self) -> None:
        self._playwright: SyncPlaywright

    def __enter__(self) -> SyncPlaywright:
        def greenlet_main() -> None:
            loop = None
            own_loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                own_loop = loop

            if loop.is_running():
                raise Error("Can only run one Playwright at a time.")

            loop.run_until_complete(self._connection.run_as_sync())

            if own_loop:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        dispatcher_fiber = greenlet(greenlet_main)
        self._connection = Connection(
            dispatcher_fiber, create_remote_object, compute_driver_executable()
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


class AsyncPlaywrightContextManager:
    def __init__(self) -> None:
        self._connection: Connection

    async def __aenter__(self) -> AsyncPlaywright:
        self._connection = Connection(
            None, create_remote_object, compute_driver_executable()
        )
        loop = asyncio.get_running_loop()
        self._connection._loop = loop
        loop.create_task(self._connection.run())
        playwright = AsyncPlaywright(
            await self._connection.wait_for_object_with_known_name("Playwright")
        )
        playwright.stop = self.__aexit__  # type: ignore
        return playwright

    async def start(self) -> AsyncPlaywright:
        return await self.__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        self._connection.stop_async()


if sys.version_info.major == 3 and sys.version_info.minor == 7:
    if sys.platform == "win32":
        # Use ProactorEventLoop in 3.7, which is default in 3.8
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    else:
        # Prevent Python 3.7 from throwing on Linux:
        # RuntimeError: Cannot add child handler, the child watcher does not have a loop attached
        asyncio.get_event_loop()
        asyncio.get_child_watcher()


def main() -> None:
    driver_executable = compute_driver_executable()
    my_env = os.environ.copy()
    my_env["PW_CLI_TARGET_LANG"] = "python"
    subprocess.run([str(driver_executable), *sys.argv[1:]], env=my_env)
