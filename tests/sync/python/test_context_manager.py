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

"""Python only: tests of behaviors that no upstream test covers."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from playwright.sync_api import BrowserContext


def test_context_managers_not_hang(context: BrowserContext) -> None:
    with pytest.raises(Exception, match="Oops!"):
        with context.new_page():
            raise Exception("Oops!")


def test_empty_sync_playwright_does_not_warn(tmp_path: Path) -> None:
    # Regression test for https://github.com/microsoft/playwright-python/issues/3165.
    # __enter__ must wait for initialize to finish; otherwise teardown races the
    # in-flight init callback and prints asyncio warnings on an empty with-block.
    script = tmp_path / "empty_sync_playwright.py"
    script.write_text(
        textwrap.dedent(
            """
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                pass
            """
        )
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Future exception was never retrieved" not in result.stderr
    assert "Task was destroyed but it is pending" not in result.stderr
