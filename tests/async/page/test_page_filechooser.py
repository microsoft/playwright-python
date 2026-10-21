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

"""Port of tests/page/page-filechooser.spec.ts."""

import asyncio
import shutil
from pathlib import Path
from typing import Any, List

import pytest

from playwright.async_api import FileChooser, Page, TimeoutError
from tests.helpers.form_files_route import route_form_files
from tests.server import Server

from ..utils import Utils


@pytest.mark.slow
async def test_FC_001_should_upload_multiple_large_files(
    page: Page, server: Server, tmp_path: Path
) -> None:
    files_count = 10
    await page.goto(server.PREFIX + "/input/fileupload-multi.html")
    upload_file = tmp_path / "50MB_1.zip"
    chunk = b"A" * 1024
    with upload_file.open("wb") as stream:
        # 49 is close to the actual limit
        for _ in range(49 * 1024):
            stream.write(chunk)
    input = page.locator('input[type="file"]')
    upload_files = [upload_file]
    for i in range(2, files_count + 1):
        dst_file = tmp_path / f"50MB_{i}.zip"
        shutil.copyfile(upload_file, dst_file)
        upload_files.append(dst_file)
    async with page.expect_file_chooser() as file_chooser_info:
        await input.click()
    file_chooser = await file_chooser_info.value
    await file_chooser.set_files(upload_files)
    files_len = await page.evaluate(
        'document.getElementsByTagName("input")[0].files.length'
    )
    assert file_chooser.is_multiple() is True
    assert files_len == files_count
    for path in upload_files:
        path.unlink()


async def test_FC_002_should_emit_event_once(page: Page, server: Server) -> None:
    await page.set_content("<input type=file>")
    choosers: List[FileChooser] = []
    page.once("filechooser", lambda chooser: choosers.append(chooser))
    # Waits for the event; the "once" listener above runs before this one.
    async with page.expect_file_chooser():
        await page.click("input")
    [chooser] = choosers
    assert chooser


async def test_FC_004_should_emit_event_for_iframe(
    page: Page, server: Server, utils: Utils
) -> None:
    frame = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await frame.set_content("<input type=file>")
    choosers: List[FileChooser] = []
    page.once("filechooser", lambda chooser: choosers.append(chooser))
    async with page.expect_file_chooser():
        await frame.click("input")
    [chooser] = choosers
    assert chooser


async def test_FC_005_should_emit_event_on_off(page: Page, server: Server) -> None:
    await page.set_content("<input type=file>")
    choosers: List[FileChooser] = []

    # Python's name for off() is remove_listener().
    def listener(chooser: FileChooser) -> None:
        page.remove_listener("filechooser", listener)
        choosers.append(chooser)

    page.on("filechooser", listener)
    async with page.expect_file_chooser():
        await page.click("input")
    [chooser] = choosers
    assert chooser


async def test_FC_007_should_work_when_file_input_is_attached_to_dom(
    page: Page, server: Server
) -> None:
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as chooser_info:
        await page.click("input")
    chooser = await chooser_info.value
    assert chooser


async def test_FC_008_should_work_when_file_input_is_not_attached_to_dom(
    page: Page, assetdir: Path
) -> None:
    async def set_files() -> None:
        chooser = await page.wait_for_event("filechooser")
        await chooser.set_files(assetdir / "file-to-upload.txt")

    async def evaluate() -> Any:
        return await page.evaluate(
            """async () => {
      const el = document.createElement('input');
      el.type = 'file';
      el.click();
      await new Promise(x => el.oninput = x);
      const reader = new FileReader();
      const promise = new Promise(fulfill => reader.onload = fulfill);
      reader.readAsText(el.files[0]);
      return promise.then(() => reader.result);
    }"""
        )

    _, content = await asyncio.gather(set_files(), evaluate())
    assert content == "contents of the file"


async def test_FC_009_should_not_throw_when_filechooser_belongs_to_iframe(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.main_frame.child_frames[0]
    await frame.set_content(
        """
    <div>Click me</div>
    <script>
      document.querySelector('div').addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.click();
        window.parent.__done = true;
      });
    </script>
  """
    )
    async with page.expect_file_chooser():
        await frame.click("div")
    await page.wait_for_function("() => window.__done")


async def test_FC_010_should_not_throw_when_frame_is_detached_immediately(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.main_frame.child_frames[0]
    await frame.set_content(
        """
    <div>Click me</div>
    <script>
      document.querySelector('div').addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.click();
        window.parent.__done = true;
        const iframe = window.parent.document.querySelector('iframe');
        iframe.remove();
      });
    </script>
  """
    )
    page.on("filechooser", lambda _: None)  # To ensure we handle file choosers.
    await frame.click("div")
    await page.wait_for_function("() => window.__done")


async def test_FC_011_should_respect_timeout(page: Page) -> None:
    with pytest.raises(TimeoutError):
        await page.wait_for_event("filechooser", timeout=1)


async def test_FC_012_should_respect_default_timeout_when_there_is_no_custom_timeout(
    page: Page,
) -> None:
    page.set_default_timeout(1)
    with pytest.raises(TimeoutError):
        await page.wait_for_event("filechooser")


async def test_FC_013_should_prioritize_exact_timeout_over_default_timeout(
    page: Page,
) -> None:
    page.set_default_timeout(0)
    with pytest.raises(TimeoutError):
        await page.wait_for_event("filechooser", timeout=1)


async def test_FC_014_should_work_with_no_timeout(page: Page, server: Server) -> None:
    async with page.expect_file_chooser(timeout=0) as chooser_info:
        await page.evaluate(
            """() => window.builtins.setTimeout(() => {
      const el = document.createElement('input');
      el.type = 'file';
      el.click();
    }, 50)"""
        )
    chooser = await chooser_info.value
    assert chooser


async def test_FC_016_should_return_the_same_file_chooser_when_there_are_many_watchdogs_simultaneously(
    page: Page, server: Server
) -> None:
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as file_chooser_info1:
        async with page.expect_file_chooser() as file_chooser_info2:
            await page.eval_on_selector("input", "input => input.click()")
    file_chooser1 = await file_chooser_info1.value
    file_chooser2 = await file_chooser_info2.value
    assert (file_chooser1 is file_chooser2) is True


async def test_FC_017_should_accept_single_file(page: Page, assetdir: Path) -> None:
    await page.set_content("<input type=file oninput='javascript:console.timeStamp()'>")
    async with page.expect_file_chooser() as file_chooser_info:
        await page.click("input")
    file_chooser = await file_chooser_info.value
    assert file_chooser.page is page
    assert file_chooser.element
    await file_chooser.set_files(assetdir / "file-to-upload.txt")
    assert await page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        await page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


# @see https://github.com/microsoft/playwright/issues/4704
async def test_FC_018_should_not_trim_big_uploaded_files(
    page: Page, server: Server
) -> None:
    files = route_form_files(server, "/upload")
    await page.goto(server.EMPTY_PAGE)

    DATA_SIZE = 2**20
    # fetch() returns after the route has parsed the form and sent the response.
    await page.evaluate(
        """async size => {
    const body = new FormData();
    body.set('file', new Blob([new Uint8Array(size)]));
    await fetch('/upload', { method: 'POST', body });
  }""",
        DATA_SIZE,
    )
    assert len(files["file"].data) == DATA_SIZE


async def test_FC_019_should_be_able_to_read_selected_file(
    page: Page, assetdir: Path
) -> None:
    await page.set_content("<input type=file>")

    async def set_files() -> None:
        file_chooser = await page.wait_for_event("filechooser")
        await file_chooser.set_files(assetdir / "file-to-upload.txt")

    async def read_file() -> Any:
        return await page.eval_on_selector(
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

    _, content = await asyncio.gather(set_files(), read_file())
    assert content == "contents of the file"


async def test_FC_020_should_be_able_to_reset_selected_files_with_empty_file_list(
    page: Page, assetdir: Path
) -> None:
    await page.set_content("<input type=file>")

    async def set_file() -> None:
        file_chooser = await page.wait_for_event("filechooser")
        await file_chooser.set_files(assetdir / "file-to-upload.txt")

    async def set_no_files() -> None:
        file_chooser = await page.wait_for_event("filechooser")
        await file_chooser.set_files([])

    async def file_length() -> Any:
        return await page.eval_on_selector(
            "input",
            """async picker => {
      picker.click();
      await new Promise(x => picker.oninput = x);
      return picker.files.length;
    }""",
        )

    _, file_length1 = await asyncio.gather(set_file(), file_length())
    assert file_length1 == 1
    _, file_length2 = await asyncio.gather(set_no_files(), file_length())
    assert file_length2 == 0


async def test_FC_021_should_work_for_single_file_pick(
    page: Page, server: Server
) -> None:
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser() as file_chooser_info:
        await page.click("input")
    file_chooser = await file_chooser_info.value
    assert file_chooser.is_multiple() is False


async def test_FC_022_should_work_for_multiple(page: Page, server: Server) -> None:
    await page.set_content("<input multiple type=file>")
    async with page.expect_file_chooser() as file_chooser_info:
        await page.click("input")
    file_chooser = await file_chooser_info.value
    assert file_chooser.is_multiple() is True


async def test_FC_023_should_work_for_webkitdirectory(
    page: Page, server: Server
) -> None:
    await page.set_content("<input multiple webkitdirectory type=file>")
    async with page.expect_file_chooser() as file_chooser_info:
        await page.click("input")
    file_chooser = await file_chooser_info.value
    assert file_chooser.is_multiple() is True


async def test_FC_024_should_emit_event_after_navigation(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/11375
    if browser_name == "chromium" and browser_major_version < 99:
        pytest.skip("chromium < 99")

    logs: List[str] = []
    page.on("filechooser", lambda _: logs.append("filechooser"))
    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser():
        await page.click("input")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    await page.set_content("<input type=file>")
    async with page.expect_file_chooser():
        await page.click("input")
    assert logs == ["filechooser", "filechooser"]


async def test_FC_025_should_trigger_listener_added_before_navigation(
    page: Page, server: Server
) -> None:
    # Add listener before cross process navigation.
    choosers: List[FileChooser] = []
    page.once("filechooser", lambda chooser: choosers.append(chooser))
    await page.goto(server.PREFIX + "/empty.html")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    await page.set_content("<input type=file>")
    # Waits for the event; the "once" listener above runs before this one.
    async with page.expect_file_chooser():
        await page.click("input")
    [chooser] = choosers
    assert chooser


# Each test navigates to a fresh document, because transient activation
# (including the one granted by page.evaluate in all browsers) sticks to
# the document for several seconds.
USER_ACTIVATION_HTML = """
    <button id="once">once</button>
    <button id="twice">twice</button>
    <input type=file>
    <script>
      const input = document.querySelector('input');
      document.querySelector('#once').addEventListener('click', () => input.click());
      document.querySelector('#twice').addEventListener('click', () => { input.click(); input.click(); });
      window.showPicker = () => {
        try {
          input.showPicker();
          return 'ok';
        } catch (e) {
          return e.name;
        }
      };
      if (location.search === '?click')
        setTimeout(() => input.click(), 0);
      if (location.search === '?showPicker')
        setTimeout(() => console.log('showPicker:' + window.showPicker()), 0);
    </script>
  """


async def user_activation_before_each(page: Page, server: Server) -> None:
    await page.route(
        server.PREFIX + "/activation.html*",
        lambda route: route.fulfill(
            content_type="text/html", body=USER_ACTIVATION_HTML
        ),
    )


async def test_FC_026_user_activation_should_not_open_file_chooser_without_user_activation(
    page: Page, server: Server, browser_name: str
) -> None:
    await user_activation_before_each(page, server)
    if browser_name == "webkit":
        pytest.skip(
            "fixme: WebKit opens the file chooser from input.click() without user activation"
        )
    choosers = 0

    def on_file_chooser(_: FileChooser) -> None:
        nonlocal choosers
        choosers += 1

    page.on("filechooser", on_file_chooser)

    await page.goto(server.PREFIX + "/activation.html?click")
    await page.wait_for_timeout(500)
    assert choosers == 0

    # Do not poll with waitForFunction: each poll evaluates in the page with a user gesture,
    # which grants transient user activation and would let showPicker() succeed.
    async with page.expect_console_message(
        lambda msg: msg.text.startswith("showPicker:")
    ) as result:
        await page.goto(server.PREFIX + "/activation.html?showPicker")
    assert (await result.value).text == "showPicker:NotAllowedError"
    assert choosers == 0


async def test_FC_027_user_activation_should_open_file_chooser_with_user_activation(
    page: Page, server: Server
) -> None:
    await user_activation_before_each(page, server)
    await page.goto(server.PREFIX + "/activation.html")
    async with page.expect_file_chooser() as chooser_info:
        await page.click("#once")
    chooser = await chooser_info.value
    assert chooser

    # page.evaluate grants transient user activation in all browsers.
    await page.goto(server.PREFIX + "/activation.html")
    async with page.expect_file_chooser() as chooser2_info:
        await page.evaluate("() => document.querySelector('input').click()")
    chooser2 = await chooser2_info.value
    assert chooser2
    await page.goto(server.PREFIX + "/activation.html")
    assert await page.evaluate("() => window.showPicker()") == "ok"


async def test_FC_028_user_activation_should_consume_user_activation_when_opening_file_chooser(
    page: Page, server: Server, browser_name: str
) -> None:
    await user_activation_before_each(page, server)
    if browser_name == "webkit":
        pytest.skip(
            "fixme: WebKit does not consume user activation when opening the file chooser"
        )
    choosers = 0

    def on_file_chooser(_: FileChooser) -> None:
        nonlocal choosers
        choosers += 1

    page.on("filechooser", on_file_chooser)
    await page.goto(server.PREFIX + "/activation.html")
    await page.click("#twice")
    await page.wait_for_timeout(500)
    assert choosers == 1
