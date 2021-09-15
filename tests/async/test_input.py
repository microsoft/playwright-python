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

import pytest

from playwright._impl._path_utils import get_file_dirname
from playwright.async_api import Page

_dirname = get_file_dirname()
FILE_TO_UPLOAD = _dirname / ".." / "assets/file-to-upload.txt"


async def test_should_upload_the_file(page, server):
    await page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = os.path.relpath(FILE_TO_UPLOAD, os.getcwd())
    input = await page.query_selector("input")
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


async def test_should_work(page, assetdir):
    await page.set_content("<input type=file>")
    await page.set_input_files("input", assetdir / "file-to-upload.txt")
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


async def test_should_set_from_memory(page):
    await page.set_content("<input type=file>")
    await page.set_input_files(
        "input",
        files=[
            {"name": "test.txt", "mimeType": "text/plain", "buffer": b"this is a test"}
        ],
    )
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files[0].name")
        == "test.txt"
    )


async def test_should_emit_event(page: Page):
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


async def test_should_work_when_file_input_is_attached_to_dom(page: Page):
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser


async def test_should_work_when_file_input_is_not_attached_to_DOM(page):
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
):
    await page.set_content("<input type=file>")
    results = await asyncio.gather(
        page.wait_for_event("filechooser"),
        page.wait_for_event("filechooser"),
        page.eval_on_selector("input", "input => input.click()"),
    )
    assert results[0] == results[1]


async def test_should_accept_single_file(page: Page):
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


async def test_should_be_able_to_read_selected_file(page: Page):
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
    page: Page, server
):
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
    page, server, assetdir
):
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


async def test_should_emit_input_and_change_events(page):
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
    await (await page.query_selector("input")).set_input_files(FILE_TO_UPLOAD)
    assert len(events) == 2
    assert events[0]["type"] == "input"
    assert events[1]["type"] == "change"


async def test_should_work_for_single_file_pick(page):
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.is_multiple() is False


async def test_should_work_for_multiple(page):
    await page.set_content("<input multiple type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.is_multiple()


async def test_should_work_for_webkitdirectory(page):
    await page.set_content("<input multiple webkitdirectory type=file>")
    async with page.expect_file_chooser() as fc_info:
        await page.click("input")
    file_chooser = await fc_info.value
    assert file_chooser.is_multiple()


async def test_wheel_should_work(page: Page, server):
    await page.set_content(
        """
        <div style="width: 5000px; height: 5000px;"></div>
    """
    )
    await page.mouse.move(50, 60)
    await _listen_for_wheel_events(page, "div")
    await page.mouse.wheel(0, 100)
    assert await page.evaluate("window.lastEvent") == {
        "deltaX": 0,
        "deltaY": 100,
        "clientX": 50,
        "clientY": 60,
        "deltaMode": 0,
        "ctrlKey": False,
        "shiftKey": False,
        "altKey": False,
        "metaKey": False,
    }
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
