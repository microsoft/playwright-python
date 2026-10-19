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

"""Port of tests/page/page-drop.spec.ts."""

import re
from pathlib import Path
from typing import Any

import pytest

from playwright.sync_api import Error, FilePayload, Page


def setup_dropzone(page: Page) -> None:
    page.set_content(
        """
        <style>#dropzone { width: 300px; height: 200px; border: 2px dashed #888; }</style>
        <div id="dropzone"></div>
        <script>
          window.__dropInfo = null;
          const zone = document.getElementById('dropzone');
          zone.addEventListener('dragenter', e => e.preventDefault());
          zone.addEventListener('dragover', e => e.preventDefault());
          zone.addEventListener('drop', async e => {
            e.preventDefault();
            const files = [];
            for (const file of e.dataTransfer.files)
              files.push({ name: file.name, type: file.type, size: file.size, text: await file.text() });
            const data = {};
            for (const t of e.dataTransfer.types) {
              if (t !== 'Files')
                data[t] = e.dataTransfer.getData(t);
            }
            window.__dropInfo = { files, data };
          });
        </script>
        """
    )


def get_drop_info(page: Page) -> Any:
    handle = page.wait_for_function("() => window.__dropInfo")
    return handle.json_value()


def test_DD_021_should_drop_a_file_payload(page: Page) -> None:
    setup_dropzone(page)
    page.locator("#dropzone").drop(
        {
            "files": {"name": "note.txt", "mimeType": "text/plain", "buffer": b"hello"},
        }
    )
    assert get_drop_info(page) == {
        "files": [
            {"name": "note.txt", "type": "text/plain", "size": 5, "text": "hello"}
        ],
        "data": {},
    }


def test_DD_022_should_drop_multiple_file_payloads(page: Page) -> None:
    setup_dropzone(page)
    page.locator("#dropzone").drop(
        {
            "files": [
                FilePayload(name="a.txt", mimeType="text/plain", buffer=b"AAA"),
                FilePayload(name="b.txt", mimeType="text/plain", buffer=b"BB"),
            ],
        }
    )
    info = get_drop_info(page)
    assert [[f["name"], f["text"]] for f in info["files"]] == [
        ["a.txt", "AAA"],
        ["b.txt", "BB"],
    ]


def test_DD_023_should_drop_a_file_by_local_path(page: Page, tmp_path: Path) -> None:
    setup_dropzone(page)
    file_path = tmp_path / "hello.txt"
    file_path.write_text("path-content")
    page.locator("#dropzone").drop({"files": file_path})
    info = get_drop_info(page)
    assert len(info["files"]) == 1
    assert info["files"][0]["name"] == "hello.txt"
    assert info["files"][0]["text"] == "path-content"


def test_DD_024_should_drop_clipboard_like_data(page: Page) -> None:
    setup_dropzone(page)
    page.locator("#dropzone").drop(
        {
            "data": {
                "text/plain": "hello world",
                "text/uri-list": "https://example.com",
            },
        }
    )
    info = get_drop_info(page)
    assert info["files"] == []
    assert info["data"]["text/plain"] == "hello world"
    assert info["data"]["text/uri-list"] == "https://example.com"


def test_DD_025_should_drop_files_and_data_together(page: Page) -> None:
    setup_dropzone(page)
    page.locator("#dropzone").drop(
        {
            "files": {"name": "mix.txt", "mimeType": "text/plain", "buffer": b"mix"},
            "data": {"text/plain": "label"},
        }
    )
    info = get_drop_info(page)
    assert info["files"][0]["text"] == "mix"
    assert info["data"]["text/plain"] == "label"


def test_DD_026_should_throw_when_target_does_not_accept_drop(
    page: Page,
) -> None:
    # Dropzone without preventDefault on dragover.
    page.set_content(
        """
        <div id="dropzone" style="width: 200px; height: 100px;"></div>
        """
    )
    with pytest.raises(Error) as exc_info:
        page.locator("#dropzone").drop(
            {
                "data": {"text/plain": "nope"},
            }
        )
    assert re.search(
        r"drop target did not accept the drop", exc_info.value.message, re.IGNORECASE
    )


def test_DD_027_should_throw_when_neither_files_nor_data_provided(
    page: Page,
) -> None:
    setup_dropzone(page)
    with pytest.raises(Error) as exc_info:
        page.locator("#dropzone").drop({})
    assert re.search(r'At least one of "files" or "data"', exc_info.value.message)
