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
from pathlib import Path

import pytest

from playwright.sync_api import Page


@pytest.mark.only_browser("chromium")
def test_should_be_able_to_save_pdf_file(page: Page, tmpdir: Path) -> None:
    output_file = tmpdir / "foo.png"
    page.pdf(path=str(output_file))
    assert os.path.getsize(output_file) > 0


@pytest.mark.only_browser("chromium")
def test_should_be_able_capture_pdf_without_path(page: Page) -> None:
    buffer = page.pdf()
    assert buffer
