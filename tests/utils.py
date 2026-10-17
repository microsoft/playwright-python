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

import os
import re
from pathlib import Path
from typing import Optional, Pattern, TypeVar, Union

import pytest

TARGET_CLOSED_ERROR_MESSAGE = "Target page, context or browser has been closed"

# The context options that @playwright/test applies to every context of the upstream
# tests (_combinedContextOptions in packages/playwright/src/index.ts). The others
# there are the defaults of the browser contexts.
DEFAULT_CONTEXT_OPTIONS = {"locale": "en-US"}

MustType = TypeVar("MustType")


def must(value: Optional[MustType]) -> MustType:
    assert value
    return value


def relative_path(path: Union[str, Path]) -> str:
    """path.relative(process.cwd(), path) in Node.js.

    Like Node.js, returns the absolute path when the path is on another drive
    (Windows), where os.path.relpath() raises.
    """
    try:
        return os.path.relpath(path, os.getcwd())
    except ValueError:
        return os.path.abspath(path)


def chromium_version_less_than(a: str, b: str) -> bool:
    left = list(map(int, a.split(".")))
    right = list(map(int, b.split(".")))
    for i in range(4):
        if left[i] > right[i]:
            return False
        if left[i] < right[i]:
            return True
    return False


def expected_ssl_error(
    browser_name: str, platform: str, channel: Optional[str]
) -> Pattern[str]:
    """Port of expectedSSLError() in tests/config/utils.ts."""
    if browser_name == "chromium":
        return re.compile(r"net::(ERR_CERT_AUTHORITY_INVALID|ERR_CERT_INVALID)")
    if browser_name == "webkit":
        if platform == "darwin":
            return re.compile(r"The certificate for this server is invalid")
        if platform == "win32" and channel != "webkit-wsl":
            return re.compile(r"SSL peer certificate or SSH remote key was not OK")
        return re.compile(r"Unacceptable TLS certificate|Operation was cancelled")
    return re.compile(r"SSL_ERROR_UNKNOWN")


def provisional_xfail(request: pytest.FixtureRequest, reason: str) -> None:
    """Marks the test as a non-strict expected failure, for a failure on CI runners
    that does not reproduce here. The test still runs; an XPASS shows when it passes."""
    request.applymarker(
        pytest.mark.xfail(reason=f"provisional: {reason}", strict=False)
    )
