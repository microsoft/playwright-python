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
import sys
from pathlib import Path

import playwright
from playwright._repo_version import version


def compute_driver_executable() -> Path:
    package_path = Path(inspect.getfile(playwright)).parent
    platform = sys.platform
    if platform == "win32":
        return package_path / "driver" / "playwright.cmd"
    return package_path / "driver" / "playwright.sh"


if sys.version_info.major == 3 and sys.version_info.minor == 7:
    if sys.platform == "win32":
        # Use ProactorEventLoop in 3.7, which is default in 3.8
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    else:
        # Prevent Python 3.7 from throwing on Linux:
        # RuntimeError: Cannot add child handler, the child watcher does not have a loop attached
        asyncio.get_event_loop()
        try:
            asyncio.get_child_watcher()
        except Exception:
            # uvloop does not support child watcher
            # see https://github.com/microsoft/playwright-python/issues/582
            pass


def get_driver_env() -> dict:
    env = os.environ.copy()
    env["PW_LANG_NAME"] = "python"
    env["PW_LANG_NAME_VERSION"] = f"{sys.version_info.major}.{sys.version_info.minor}"
    env["PW_CLI_DISPLAY_VERSION"] = version
    return env
