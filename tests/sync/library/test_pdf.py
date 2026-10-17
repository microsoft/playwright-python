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

"""Port of tests/library/pdf.spec.ts."""

from pathlib import Path
from typing import Callable

import pytest

from playwright.sync_api import BrowserContext
from tests.server import Server

ContextFactory = Callable[..., BrowserContext]


def test_PD_001_should_be_able_to_save_file(
    context_factory: ContextFactory, browser_name: str, tmp_path: Path
) -> None:
    if browser_name != "chromium":
        pytest.skip("Printing to pdf is currently only supported in chromium.")
    context = context_factory()
    page = context.new_page()
    output_file = tmp_path / "output.pdf"
    page.pdf(path=output_file)
    assert len(output_file.read_bytes()) > 0


def test_PD_002_should_be_able_to_generate_outline(
    context_factory: ContextFactory, server: Server, browser_name: str, tmp_path: Path
) -> None:
    if browser_name != "chromium":
        pytest.skip("Printing to pdf is currently only supported in chromium.")
    context = context_factory(base_url=server.PREFIX)
    page = context.new_page()
    page.goto("/headings.html")
    output_file_no_outline = tmp_path / "outputNoOutline.pdf"
    output_file_outline = tmp_path / "outputOutline.pdf"
    page.pdf(path=output_file_no_outline)
    page.pdf(path=output_file_outline, tagged=True, outline=True)
    assert len(output_file_outline.read_bytes()) > len(
        output_file_no_outline.read_bytes()
    )
