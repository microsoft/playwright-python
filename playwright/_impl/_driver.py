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
from typing import Tuple, Union

import playwright
from playwright._repo_version import version
import pathlib

def get_registry_directory() -> str:
    env_defined = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
    path_home = Path.home()
    if env_defined == '0':
        result = pathlib.Path(__file__).parent.parent.parent.joinpath('.local-browsers')
    elif env_defined:
        result = pathlib.Path(env_defined)
    else:
        cache_directory: Union[str, Path] = ''
        if os.name == 'posix':
            cache_directory = os.environ.get('XDG_CACHE_HOME', path_home / '.cache')
        elif os.name == 'darwin':
            cache_directory = path_home / 'Library' / 'Caches'
        elif os.name == 'nt':
            cache_directory = os.environ.get('LOCALAPPDATA', path_home / 'AppData' / 'Local')
        else:
            raise RuntimeError('Unsupported platform: ' + os.name)
        result = pathlib.Path(cache_directory, 'ms-playwright')

    if not result.is_absolute():
        init_cwd = os.environ.get('INIT_CWD') or os.getcwd()
        result = pathlib.Path(init_cwd).resolve().joinpath(result)

    return str(result)


def compute_driver_executable() -> Tuple[str, str]:
    driver_path = Path(inspect.getfile(playwright)).parent / "driver"
    cli_path = str(driver_path / "package" / "cli.js")
    if sys.platform == "win32":
        return (str(driver_path / "node.exe"), cli_path)
    return (os.getenv("PLAYWRIGHT_NODEJS_PATH", str(driver_path / "node")), cli_path)


def get_driver_env() -> dict:
    env = os.environ.copy()
    env["PW_LANG_NAME"] = "python"
    env["PW_LANG_NAME_VERSION"] = f"{sys.version_info.major}.{sys.version_info.minor}"
    env["PW_CLI_DISPLAY_VERSION"] = version
    return env
