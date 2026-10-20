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

import asyncio
import os
from pathlib import Path

import pytest

from playwright.async_api import Page


async def test_should_emit_event(page: Page) -> None:
    await page.set_content("<input type=file>")
    fc_done: asyncio.Future = asyncio.Future()
    page.once("filechooser", lambda file_chooser: fc_done.set_result(file_chooser))
    await page.click("input")
    file_chooser = await fc_done
    assert file_chooser
    assert (
        repr(file_chooser)
        == f"<FileChooser page={file_chooser.page} element={file_chooser.element}>"
    )


async def test_should_not_accept_multiple_files_for_single_file_input(
    page: Page, assetdir: Path
) -> None:
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    with pytest.raises(Exception) as exc_info:
        await file_chooser.set_files(
            [
                os.path.realpath(assetdir / "file-to-upload.txt"),
                os.path.realpath(assetdir / "pptr.png"),
            ]
        )
    assert exc_info.value
