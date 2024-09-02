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

import asyncio
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest
from flaky import flaky

from playwright._impl._path_utils import get_file_dirname
from playwright.async_api import Error, FilePayload, Page
from tests.server import Server
from tests.utils import chromium_version_less_than, must

_dirname = get_file_dirname()
FILE_TO_UPLOAD = _dirname / ".." / "assets/file-to-upload.txt"


async def test_should_upload_the_file(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = os.path.relpath(FILE_TO_UPLOAD, os.getcwd())
    input = await page.query_selector("input")
    assert input
    await input.set_input_files(file_path)
    assert await page.evaluate("e => e.files[0].name", input) == "file-to-upload.txt"
    assert (
        await page.evaluate(
            """e => {
        reader = new FileReader()
        promise = new Promise(fulfill => reader.onload = fulfill)
        reader.readAsText(e.files[0])
        return promise.then(() => reader.result)
    }""",
            input,
        )
        == "contents of the file\n"
    )


async def test_should_work(page: Page, assetdir: Path) -> None:
    await page.set_content("<input type=file>")
    await page.set_input_files("input", assetdir / "file-to-upload.txt")
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


async def test_should_set_from_memory(page: Page) -> None:
    await page.set_content("<input type=file>")
    file: FilePayload = {
        "name": "test.txt",
        "mimeType": "text/plain",
        "buffer": b"this is a test",
    }
    await page.set_input_files(
        "input",
        files=[file],
    )
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files[0].name")
        == "test.txt"
    )


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


async def test_should_work_when_file_input_is_attached_to_dom(page: Page) -> None:
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser


async def test_should_work_when_file_input_is_not_attached_to_DOM(page: Page) -> None:
    async with page.expect_file_chooser() as fc_info:
        await page.evaluate(
            """() => {
                el = document.createElement('input')
                el.type = 'file'
                el.click()
            }"""
        )
    file_chooser = await fc_info.value
    assert file_chooser


async def test_should_return_the_same_file_chooser_when_there_are_many_watchdogs_simultaneously(
    page: Page,
) -> None:
    await page.set_content("<input type=file>")
    results = await asyncio.gather(
        page.wait_for_event("filechooser"),
        page.wait_for_event("filechooser"),
        page.eval_on_selector("input", "input => input.click()"),
    )
    assert results[0] == results[1]


async def test_should_accept_single_file(page: Page) -> None:
    await page.set_content('<input type=file oninput="javascript:console.timeStamp()">')
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.page == page
    assert file_chooser.element
    await file_chooser.set_files(FILE_TO_UPLOAD)
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


async def test_should_be_able_to_read_selected_file(page: Page) -> None:
    page.once(
        "filechooser", lambda file_chooser: file_chooser.set_files(FILE_TO_UPLOAD)
    )
    await page.set_content("<input type=file>")
    content = await page.eval_on_selector(
        "input",
        """async picker => {
            picker.click();
            await new Promise(x => picker.oninput = x);
            const reader = new FileReader();
            const promise = new Promise(fulfill => reader.onload = fulfill);
            reader.readAsText(picker.files[0]);
            return promise.then(() => reader.result);
        }""",
    )
    assert content == "contents of the file\n"


async def test_should_be_able_to_reset_selected_files_with_empty_file_list(
    page: Page,
) -> None:
    await page.set_content("<input type=file>")
    page.once(
        "filechooser", lambda file_chooser: file_chooser.set_files(FILE_TO_UPLOAD)
    )
    file_length = 0
    async with page.expect_file_chooser():
        file_length = await page.eval_on_selector(
            "input",
            """async picker => {
                picker.click();
                await new Promise(x => picker.oninput = x);
                return picker.files.length;
            }""",
        )
    assert file_length == 1

    page.once("filechooser", lambda file_chooser: file_chooser.set_files([]))
    async with page.expect_file_chooser():
        file_length = await page.eval_on_selector(
            "input",
            """async picker => {
                picker.click();
                await new Promise(x => picker.oninput = x);
                return picker.files.length;
            }""",
        )
    assert file_length == 0


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


async def test_should_emit_input_and_change_events(page: Page) -> None:
    events = []
    await page.expose_function("eventHandled", lambda e: events.append(e))
    await page.set_content(
        """
            <input id=input type=file></input>
            <script>
            input.addEventListener('input', e => eventHandled({ type: e.type }))
            input.addEventListener('change', e => eventHandled({ type: e.type }))
            </script>
        """
    )
    await must(await page.query_selector("input")).set_input_files(FILE_TO_UPLOAD)
    assert len(events) == 2
    assert events[0]["type"] == "input"
    assert events[1]["type"] == "change"


async def test_should_work_for_single_file_pick(page: Page) -> None:
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.is_multiple() is False


async def test_should_work_for_multiple(page: Page) -> None:
    await page.set_content("<input multiple type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.is_multiple()


async def test_should_work_for_webkitdirectory(page: Page) -> None:
    await page.set_content("<input multiple webkitdirectory type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.is_multiple()


def _assert_wheel_event(expected: Any, received: Any, browser_name: str) -> None:
    # Chromium reports deltaX/deltaY scaled by host device scale factor.
    # https://bugs.chromium.org/p/chromium/issues/detail?id=1324819
    # https://github.com/microsoft/playwright/issues/7362
    # Different bots have different scale factors (usually 1 or 2), so we just ignore the values
    # instead of guessing the host scale factor.
    if sys.platform == "darwin" and browser_name == "chromium":
        del expected["deltaX"]
        del expected["deltaY"]
        del received["deltaX"]
        del received["deltaY"]
    assert received == expected


async def test_wheel_should_work(page: Page, browser_name: str) -> None:
    await page.set_content(
        """
        <div style="width: 5000px; height: 5000px;"></div>
    """
    )
    await page.mouse.move(50, 60)
    await _listen_for_wheel_events(page, "div")
    await page.mouse.wheel(0, 100)
    _assert_wheel_event(
        await page.evaluate("window.lastEvent"),
        {
            "deltaX": 0,
            "deltaY": 100,
            "clientX": 50,
            "clientY": 60,
            "deltaMode": 0,
            "ctrlKey": False,
            "shiftKey": False,
            "altKey": False,
            "metaKey": False,
        },
        browser_name,
    )
    await page.wait_for_function("window.scrollY === 100")


async def _listen_for_wheel_events(page: Page, selector: str) -> None:
    await page.evaluate(
        """
        selector => {
            document.querySelector(selector).addEventListener('wheel', (e) => {
            window['lastEvent'] = {
                deltaX: e.deltaX,
                deltaY: e.deltaY,
                clientX: e.clientX,
                clientY: e.clientY,
                deltaMode: e.deltaMode,
                ctrlKey: e.ctrlKey,
                shiftKey: e.shiftKey,
                altKey: e.altKey,
                metaKey: e.metaKey,
            };
            }, { passive: false });
        }
    """,
        selector,
    )


@flaky
async def test_should_upload_large_file(
    page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.PREFIX + "/input/fileupload.html")
    large_file_path = tmp_path / "200MB.zip"
    data = b"A" * 1024
    with large_file_path.open("wb") as f:
        for i in range(0, 200 * 1024 * 1024, len(data)):
            f.write(data)
    input = page.locator('input[type="file"]')
    events = await input.evaluate_handle(
        """
        e => {
            const events = [];
            e.addEventListener('input', () => events.push('input'));
            e.addEventListener('change', () => events.push('change'));
            return events;
        }
    """
    )

    await input.set_input_files(large_file_path)
    assert await input.evaluate("e => e.files[0].name") == "200MB.zip"
    assert await events.evaluate("e => e") == ["input", "change"]

    [request, _] = await asyncio.gather(
        server.wait_for_request("/upload"),
        page.click("input[type=submit]"),
    )

    contents = request.args[b"file1"][0]
    assert len(contents) == 200 * 1024 * 1024
    assert contents[:1024] == data
    # flake8: noqa: E203
    assert contents[len(contents) - 1024 :] == data
    assert request.post_body
    match = re.search(
        rb'^.*Content-Disposition: form-data; name="(?P<name>.*)"; filename="(?P<filename>.*)".*$',
        request.post_body,
        re.MULTILINE,
    )
    assert match
    assert match.group("name") == b"file1"
    assert match.group("filename") == b"200MB.zip"


async def test_set_input_files_should_preserve_last_modified_timestamp(
    page: Page,
    assetdir: Path,
) -> None:
    await page.set_content("<input type=file multiple=true/>")
    input = page.locator("input")
    files = ["file-to-upload.txt", "file-to-upload-2.txt"]
    await input.set_input_files([assetdir / file for file in files])
    assert await input.evaluate("input => [...input.files].map(f => f.name)") == files
    timestamps = await input.evaluate(
        "input => [...input.files].map(f => f.lastModified)"
    )
    expected_timestamps = [os.path.getmtime(assetdir / file) * 1000 for file in files]

    # On Linux browser sometimes reduces the timestamp by 1ms: 1696272058110.0715  -> 1696272058109 or even
    # rounds it to seconds in WebKit: 1696272058110 -> 1696272058000.
    for i in range(len(timestamps)):
        assert abs(timestamps[i] - expected_timestamps[i]) < 1000


@flaky
async def test_should_upload_multiple_large_file(
    page: Page, server: Server, tmp_path: Path
) -> None:
    files_count = 10
    await page.goto(server.PREFIX + "/input/fileupload-multi.html")
    upload_file = tmp_path / "50MB_1.zip"
    data = b"A" * 1024
    with upload_file.open("wb") as f:
        # 49 is close to the actual limit
        for i in range(0, 49 * 1024):
            f.write(data)
    input = page.locator('input[type="file"]')
    upload_files = [upload_file]
    for i in range(2, files_count + 1):
        dst_file = tmp_path / f"50MB_{i}.zip"
        shutil.copy(upload_file, dst_file)
        upload_files.append(dst_file)
    async with page.expect_file_chooser() as fc_info:
        await input.click()
    file_chooser = await fc_info.value
    await file_chooser.set_files(upload_files)
    files_len = await page.evaluate(
        'document.getElementsByTagName("input")[0].files.length'
    )
    assert file_chooser.is_multiple()
    assert files_len == files_count
    for path in upload_files:
        path.unlink()


async def test_should_upload_a_folder(
    page: Page,
    server: Server,
    tmp_path: Path,
    browser_name: str,
    browser_version: str,
    headless: bool,
) -> None:
    await page.goto(server.PREFIX + "/input/folderupload.html")
    input = await page.query_selector("input")
    assert input
    dir = tmp_path / "file-upload-test"
    dir.mkdir()
    (dir / "file1.txt").write_text("file1 content")
    (dir / "file2").write_text("file2 content")
    (dir / "sub-dir").mkdir()
    (dir / "sub-dir" / "really.txt").write_text("sub-dir file content")
    await input.set_input_files(dir)
    assert set(
        await input.evaluate("e => [...e.files].map(f => f.webkitRelativePath)")
    ) == set(
        [
            "file-upload-test/file1.txt",
            "file-upload-test/file2",
            # https://issues.chromium.org/issues/345393164
            *(
                []
                if browser_name == "chromium"
                and headless
                and chromium_version_less_than(browser_version, "127.0.6533.0")
                else ["file-upload-test/sub-dir/really.txt"]
            ),
        ]
    )
    webkit_relative_paths = await input.evaluate(
        "e => [...e.files].map(f => f.webkitRelativePath)"
    )
    for i, webkit_relative_path in enumerate(webkit_relative_paths):
        content = await input.evaluate(
            """(e, i) => {
            const reader = new FileReader();
            const promise = new Promise(fulfill => reader.onload = fulfill);
            reader.readAsText(e.files[i]);
            return promise.then(() => reader.result);
        }""",
            i,
        )
        assert content == (dir / ".." / webkit_relative_path).read_text()


async def test_should_upload_a_folder_and_throw_for_multiple_directories(
    page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.PREFIX + "/input/folderupload.html")
    input = page.locator("input")
    dir = tmp_path / "file-upload-test"
    dir.mkdir()
    (dir / "folder1").mkdir()
    (dir / "folder1" / "file1.txt").write_text("file1 content")
    (dir / "folder2").mkdir()
    (dir / "folder2" / "file2.txt").write_text("file2 content")
    with pytest.raises(Error) as exc_info:
        await input.set_input_files([dir / "folder1", dir / "folder2"])
    assert "Multiple directories are not supported" in exc_info.value.message


async def test_should_throw_if_a_directory_and_files_are_passed(
    page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.PREFIX + "/input/folderupload.html")
    input = page.locator("input")
    dir = tmp_path / "file-upload-test"
    dir.mkdir()
    (dir / "file1.txt").write_text("file1 content")
    with pytest.raises(Error) as exc_info:
        await input.set_input_files([dir, dir / "file1.txt"])
    assert (
        "File paths must be all files or a single directory" in exc_info.value.message
    )


async def test_should_throw_when_upload_a_folder_in_a_normal_file_upload_input(
    page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.PREFIX + "/input/fileupload.html")
    input = await page.query_selector("input")
    assert input
    dir = tmp_path / "file-upload-test"
    dir.mkdir()
    (dir / "file1.txt").write_text("file1 content")
    with pytest.raises(Error) as exc_info:
        await input.set_input_files(dir)
    assert (
        "File input does not support directories, pass individual files instead"
        in exc_info.value.message
    )
