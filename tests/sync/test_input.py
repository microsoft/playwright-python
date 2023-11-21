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
from typing import Any

from playwright.sync_api import Page


def test_expect_file_chooser(page: Page) -> None:
    page.set_content("<input type=file></input>")
    with page.expect_file_chooser() as fc_info:
        page.click('input[type="file"]')
    fc = fc_info.value
    fc.set_files(
        {"name": "test.txt", "mimeType": "text/plain", "buffer": b"Hello World"}
    )


def test_set_input_files_should_preserve_last_modified_timestamp(
    page: Page,
    assetdir: Path,
) -> None:
    page.set_content("<input type=file multiple=true/>")
    input = page.locator("input")
    files: Any = ["file-to-upload.txt", "file-to-upload-2.txt"]
    input.set_input_files([assetdir / file for file in files])
    assert input.evaluate("input => [...input.files].map(f => f.name)") == files
    timestamps = input.evaluate("input => [...input.files].map(f => f.lastModified)")
    expected_timestamps = [os.path.getmtime(assetdir / file) * 1000 for file in files]

    # On Linux browser sometimes reduces the timestamp by 1ms: 1696272058110.0715  -> 1696272058109 or even
    # rounds it to seconds in WebKit: 1696272058110 -> 1696272058000.
    for i in range(len(timestamps)):
        assert abs(timestamps[i] - expected_timestamps[i]) < 1000
