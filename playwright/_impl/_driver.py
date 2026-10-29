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

import inspect
import os
import sys
from pathlib import Path
from typing import Tuple

import playwright
from playwright._impl._errors import Error
from playwright._repo_version import version


def compute_driver_executable() -> Tuple[str, str]:
    driver_path = Path(inspect.getfile(playwright)).parent / "driver"
    cli_path = str(driver_path / "package" / "cli.js")
    node_path = os.getenv("PLAYWRIGHT_NODEJS_PATH")
    if node_path:
        return (node_path, cli_path)
    bundled_node = driver_path / ("node.exe" if sys.platform == "win32" else "node")
    if not bundled_node.is_file():
        # The source distribution ships the driver without Node.js.
        raise Error(
            "This installation of Playwright does not include Node.js. "
            "Set PLAYWRIGHT_NODEJS_PATH pointing to Node.js executable."
        )
    return (str(bundled_node), cli_path)


def node_launch_error(executable: str, error: OSError) -> Error:
    """The error for a spawn of the driver that failed."""
    return Error(f"Cannot launch Node.js executable at {executable}: {error}")


def get_driver_env() -> dict:
    env = os.environ.copy()
    env["PW_LANG_NAME"] = "python"
    env["PW_LANG_NAME_VERSION"] = f"{sys.version_info.major}.{sys.version_info.minor}"
    env["PW_CLI_DISPLAY_VERSION"] = version
    return env
