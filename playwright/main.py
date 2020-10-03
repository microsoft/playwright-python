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
import os
import stat
import subprocess
import sys
from pathlib import Path
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


def compute_driver_executable() -> Path:
    package_path = get_file_dirname()
    platform = sys.platform
    if platform == "darwin":
        return package_path / "drivers" / "driver-darwin"
    elif platform == "linux":
        return package_path / "drivers" / "driver-linux"
    elif platform == "win32":
        result = package_path / "drivers" / "driver-win32-amd64.exe"
        if result.exists():
            return result
        return package_path / "drivers" / "driver-win32.exe"
    return package_path / "drivers" / "driver-linux"


async def run_driver_async() -> Connection:
    driver_executable = compute_driver_executable()

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
        self._connection = await run_driver_async()
        self._connection.run_async()
        playwright = AsyncPlaywright(
            await self._connection.wait_for_object_with_known_name("Playwright")
        )
        playwright.stop = self.__aexit__  # type: ignore
        return playwright

    async def start(self) -> AsyncPlaywright:
        return await self.__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        self._connection.stop_async()


if sys.platform == "win32":
    # Use ProactorEventLoop in 3.7, which is default in 3.8
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)


def main() -> None:
    if "install" not in sys.argv:
        print('Run "python -m playwright install" to complete installation')
        return
    driver_executable = compute_driver_executable()
    # Fix the executable bit during the installation.
    if not sys.platform == "win32":
        st = os.stat(driver_executable)
        if st.st_mode & stat.S_IEXEC == 0:
            os.chmod(driver_executable, st.st_mode | stat.S_IEXEC)
    print("Installing the browsers...")
    subprocess.check_call([str(driver_executable), "install"])

    print("Playwright is now ready for use")
