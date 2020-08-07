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
import io
import subprocess
import sys
from typing import Any

from greenlet import greenlet

from playwright.async_api import Playwright as AsyncPlaywright
from playwright.connection import Connection
from playwright.helper import Error
from playwright.object_factory import create_remote_object
from playwright.path_utils import get_file_dirname
from playwright.playwright import Playwright
from playwright.sync_api import Playwright as SyncPlaywright
from playwright.sync_base import dispatcher_fiber, set_dispatcher_fiber


def compute_driver_name() -> str:
    platform = sys.platform
    if platform == "darwin":
        result = "driver-macos"
    elif platform == "linux":
        result = "driver-linux"
    elif platform == "win32":
        result = "driver-win.exe"
    return result


async def run_driver_async() -> Connection:
    package_path = get_file_dirname()
    driver_name = compute_driver_name()
    driver_executable = package_path / "drivers" / driver_name

    # Sourced from: https://github.com/pytest-dev/pytest/blob/49827adcb9256c9c9c06a25729421dcc3c385edc/src/_pytest/faulthandler.py#L73-L80
    def _get_stderr_fileno() -> int:
        try:
            return sys.stderr.fileno()
        except io.UnsupportedOperation:
            # pytest-xdist monkeypatches sys.stderr with an object that is not an actual file.
            # https://docs.python.org/3/library/faulthandler.html#issue-with-file-descriptors
            # This is potentially dangerous, but the best we can do.
            return sys.__stderr__.fileno()

    proc = await asyncio.create_subprocess_exec(
        str(driver_executable),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=_get_stderr_fileno(),
        limit=32768,
    )
    assert proc.stdout
    assert proc.stdin
    connection = Connection(
        proc.stdout, proc.stdin, create_remote_object, asyncio.get_event_loop()
    )
    return connection


def run_driver() -> Connection:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        raise Error("Can only run one Playwright at a time.")
    return loop.run_until_complete(run_driver_async())


class SyncPlaywrightContextManager:
    def __init__(self) -> None:
        self._connection = run_driver()
        self._playwright: SyncPlaywright

    def __enter__(self) -> SyncPlaywright:
        g_self = greenlet.getcurrent()

        def callback_wrapper(playwright_impl: Playwright) -> None:
            self._playwright = SyncPlaywright(playwright_impl)
            g_self.switch()

        self._connection.call_on_object_with_known_name("Playwright", callback_wrapper)
        set_dispatcher_fiber(greenlet(lambda: self._connection.run_sync()))
        dispatcher_fiber().switch()
        return self._playwright

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._connection.stop_sync()


class AsyncPlaywrightContextManager:
    def __init__(self) -> None:
        self._connection: Connection

    async def __aenter__(self) -> AsyncPlaywright:
        self._connection = await run_driver_async()
        self._connection.run_async()
        return AsyncPlaywright(
            await self._connection.wait_for_object_with_known_name("Playwright")
        )

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._connection.stop_async()


if sys.platform == "win32":
    # Use ProactorEventLoop in 3.7, which is default in 3.8
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


def main() -> None:
    if "install" not in sys.argv:
        print('Run "python -m playwright install" to complete installation')
        return
    package_path = get_file_dirname()
    driver_name = compute_driver_name()
    driver_executable = package_path / "drivers" / driver_name
    print("Installing the browsers...")
    subprocess.check_call(f"{driver_executable} install", shell=True)

    print("Playwright is now ready for use")
