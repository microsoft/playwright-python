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

import pytest

from playwright.async_api import Page
from tests.server import Server

pytestmark = pytest.mark.only_browser("chromium")


async def test_should_be_able_to_save_pdf_file(page: Page, tmp_path: Path) -> None:
    output_file = tmp_path / "foo.png"
    await page.pdf(path=str(output_file))
    assert os.path.getsize(output_file) > 0


async def test_should_be_able_capture_pdf_without_path(page: Page) -> None:
    buffer = await page.pdf()
    assert buffer


async def test_should_be_able_to_generate_outline(
    page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.PREFIX + "/headings.html")
    output_file_no_outline = tmp_path / "outputNoOutline.pdf"
    output_file_outline = tmp_path / "outputOutline.pdf"
    await page.pdf(path=output_file_no_outline)
    await page.pdf(path=output_file_outline, tagged=True, outline=True)
    assert os.path.getsize(output_file_outline) > os.path.getsize(
        output_file_no_outline
    )


async def test_should_accept_numeric_width_height_and_margin(page: Page) -> None:
    await page.set_content("<h1>hello</h1>")
    with_numbers = await page.pdf(
        width=500, height=400, margin={"top": 10, "right": 10, "bottom": 10, "left": 10}
    )
    with_px = await page.pdf(
        width="500px",
        height="400px",
        margin={"top": "10px", "right": "10px", "bottom": "10px", "left": "10px"},
    )
    media_box = re.compile(rb"/MediaBox\s*\[[^\]]*\]")
    assert media_box.findall(with_numbers) == media_box.findall(with_px)
