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

import shutil
from pathlib import Path
from typing import Any, Callable, List

import pytest

from playwright.sync_api import FileChooser, Page, TimeoutError
from tests.helpers.form_files_route import route_form_files
from tests.server import Server

from ..utils import Utils


@pytest.mark.slow
def test_FC_001_should_upload_multiple_large_files(
    page: Page, server: Server, tmp_path: Path
) -> None:
    files_count = 10
    page.goto(server.PREFIX + "/input/fileupload-multi.html")
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
    with page.expect_file_chooser() as file_chooser_info:
        input.click()
    file_chooser = file_chooser_info.value
    file_chooser.set_files(upload_files)
    files_len = page.evaluate('document.getElementsByTagName("input")[0].files.length')
    assert file_chooser.is_multiple() is True
    assert files_len == files_count
    for path in upload_files:
        path.unlink()


def test_FC_002_should_emit_event_once(page: Page, server: Server) -> None:
    page.set_content("<input type=file>")
    choosers: List[FileChooser] = []
    page.once("filechooser", lambda chooser: choosers.append(chooser))
    # Waits for the event; the "once" listener above runs before this one.
    with page.expect_file_chooser():
        page.click("input")
    [chooser] = choosers
    assert chooser


def test_FC_004_should_emit_event_for_iframe(
    page: Page, server: Server, utils: Utils
) -> None:
    frame = utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame.set_content("<input type=file>")
    choosers: List[FileChooser] = []
    page.once("filechooser", lambda chooser: choosers.append(chooser))
    with page.expect_file_chooser():
        frame.click("input")
    [chooser] = choosers
    assert chooser


def test_FC_005_should_emit_event_on_off(page: Page, server: Server) -> None:
    page.set_content("<input type=file>")
    choosers: List[FileChooser] = []

    # Python's name for off() is remove_listener().
    def listener(chooser: FileChooser) -> None:
        page.remove_listener("filechooser", listener)
        choosers.append(chooser)

    page.on("filechooser", listener)
    with page.expect_file_chooser():
        page.click("input")
    [chooser] = choosers
    assert chooser


def test_FC_007_should_work_when_file_input_is_attached_to_dom(
    page: Page, server: Server
) -> None:
    page.set_content("<input type=file>")
    with page.expect_file_chooser() as chooser_info:
        page.click("input")
    chooser = chooser_info.value
    assert chooser


def test_FC_008_should_work_when_file_input_is_not_attached_to_dom(
    page: Page, assetdir: Path, sync_gather: Callable[..., List[Any]]
) -> None:
    def set_files() -> None:
        chooser = page.wait_for_event("filechooser")
        chooser.set_files(assetdir / "file-to-upload.txt")

    def evaluate() -> Any:
        return page.evaluate(
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

    _, content = sync_gather(set_files, evaluate)
    assert content == "contents of the file"


def test_FC_009_should_not_throw_when_filechooser_belongs_to_iframe(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.main_frame.child_frames[0]
    frame.set_content(
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
    with page.expect_file_chooser():
        frame.click("div")
    page.wait_for_function("() => window.__done")


def test_FC_010_should_not_throw_when_frame_is_detached_immediately(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.main_frame.child_frames[0]
    frame.set_content(
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
    frame.click("div")
    page.wait_for_function("() => window.__done")


def test_FC_011_should_respect_timeout(page: Page) -> None:
    with pytest.raises(TimeoutError):
        page.wait_for_event("filechooser", timeout=1)


def test_FC_012_should_respect_default_timeout_when_there_is_no_custom_timeout(
    page: Page,
) -> None:
    page.set_default_timeout(1)
    with pytest.raises(TimeoutError):
        page.wait_for_event("filechooser")


def test_FC_013_should_prioritize_exact_timeout_over_default_timeout(
    page: Page,
) -> None:
    page.set_default_timeout(0)
    with pytest.raises(TimeoutError):
        page.wait_for_event("filechooser", timeout=1)


def test_FC_014_should_work_with_no_timeout(page: Page, server: Server) -> None:
    with page.expect_file_chooser(timeout=0) as chooser_info:
        page.evaluate(
            """() => window.builtins.setTimeout(() => {
      const el = document.createElement('input');
      el.type = 'file';
      el.click();
    }, 50)"""
        )
    chooser = chooser_info.value
    assert chooser


def test_FC_016_should_return_the_same_file_chooser_when_there_are_many_watchdogs_simultaneously(
    page: Page, server: Server
) -> None:
    page.set_content("<input type=file>")
    with page.expect_file_chooser() as file_chooser_info1:
        with page.expect_file_chooser() as file_chooser_info2:
            page.eval_on_selector("input", "input => input.click()")
    file_chooser1 = file_chooser_info1.value
    file_chooser2 = file_chooser_info2.value
    assert (file_chooser1 is file_chooser2) is True


def test_FC_017_should_accept_single_file(page: Page, assetdir: Path) -> None:
    page.set_content("<input type=file oninput='javascript:console.timeStamp()'>")
    with page.expect_file_chooser() as file_chooser_info:
        page.click("input")
    file_chooser = file_chooser_info.value
    assert file_chooser.page is page
    assert file_chooser.element
    file_chooser.set_files(assetdir / "file-to-upload.txt")
    assert page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


# @see https://github.com/microsoft/playwright/issues/4704
def test_FC_018_should_not_trim_big_uploaded_files(page: Page, server: Server) -> None:
    files = route_form_files(server, "/upload")
    page.goto(server.EMPTY_PAGE)

    DATA_SIZE = 2**20
    # fetch() returns after the route has parsed the form and sent the response.
    page.evaluate(
        """async size => {
    const body = new FormData();
    body.set('file', new Blob([new Uint8Array(size)]));
    await fetch('/upload', { method: 'POST', body });
  }""",
        DATA_SIZE,
    )
    assert len(files["file"].data) == DATA_SIZE


def test_FC_019_should_be_able_to_read_selected_file(
    page: Page, assetdir: Path, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<input type=file>")

    def set_files() -> None:
        file_chooser = page.wait_for_event("filechooser")
        file_chooser.set_files(assetdir / "file-to-upload.txt")

    def read_file() -> Any:
        return page.eval_on_selector(
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

    _, content = sync_gather(set_files, read_file)
    assert content == "contents of the file"


def test_FC_020_should_be_able_to_reset_selected_files_with_empty_file_list(
    page: Page, assetdir: Path, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<input type=file>")

    def set_file() -> None:
        file_chooser = page.wait_for_event("filechooser")
        file_chooser.set_files(assetdir / "file-to-upload.txt")

    def set_no_files() -> None:
        file_chooser = page.wait_for_event("filechooser")
        file_chooser.set_files([])

    def file_length() -> Any:
        return page.eval_on_selector(
            "input",
            """async picker => {
      picker.click();
      await new Promise(x => picker.oninput = x);
      return picker.files.length;
    }""",
        )

    _, file_length1 = sync_gather(set_file, file_length)
    assert file_length1 == 1
    _, file_length2 = sync_gather(set_no_files, file_length)
    assert file_length2 == 0


def test_FC_021_should_work_for_single_file_pick(page: Page, server: Server) -> None:
    page.set_content("<input type=file>")
    with page.expect_file_chooser() as file_chooser_info:
        page.click("input")
    file_chooser = file_chooser_info.value
    assert file_chooser.is_multiple() is False


def test_FC_022_should_work_for_multiple(page: Page, server: Server) -> None:
    page.set_content("<input multiple type=file>")
    with page.expect_file_chooser() as file_chooser_info:
        page.click("input")
    file_chooser = file_chooser_info.value
    assert file_chooser.is_multiple() is True


def test_FC_023_should_work_for_webkitdirectory(page: Page, server: Server) -> None:
    page.set_content("<input multiple webkitdirectory type=file>")
    with page.expect_file_chooser() as file_chooser_info:
        page.click("input")
    file_chooser = file_chooser_info.value
    assert file_chooser.is_multiple() is True


def test_FC_024_should_emit_event_after_navigation(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/11375
    if browser_name == "chromium" and browser_major_version < 99:
        pytest.skip("chromium < 99")

    logs: List[str] = []
    page.on("filechooser", lambda _: logs.append("filechooser"))
    page.goto(server.PREFIX + "/empty.html")
    page.set_content("<input type=file>")
    with page.expect_file_chooser():
        page.click("input")
    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    page.set_content("<input type=file>")
    with page.expect_file_chooser():
        page.click("input")
    assert logs == ["filechooser", "filechooser"]


def test_FC_025_should_trigger_listener_added_before_navigation(
    page: Page, server: Server
) -> None:
    # Add listener before cross process navigation.
    choosers: List[FileChooser] = []
    page.once("filechooser", lambda chooser: choosers.append(chooser))
    page.goto(server.PREFIX + "/empty.html")
    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    page.set_content("<input type=file>")
    # Waits for the event; the "once" listener above runs before this one.
    with page.expect_file_chooser():
        page.click("input")
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


def user_activation_before_each(page: Page, server: Server) -> None:
    page.route(
        server.PREFIX + "/activation.html*",
        lambda route: route.fulfill(
            content_type="text/html", body=USER_ACTIVATION_HTML
        ),
    )


def test_FC_026_user_activation_should_not_open_file_chooser_without_user_activation(
    page: Page, server: Server, browser_name: str
) -> None:
    user_activation_before_each(page, server)
    if browser_name == "webkit":
        pytest.skip(
            "fixme: WebKit opens the file chooser from input.click() without user activation"
        )
    choosers = 0

    def on_file_chooser(_: FileChooser) -> None:
        nonlocal choosers
        choosers += 1

    page.on("filechooser", on_file_chooser)

    page.goto(server.PREFIX + "/activation.html?click")
    page.wait_for_timeout(500)
    assert choosers == 0

    # Do not poll with waitForFunction: each poll evaluates in the page with a user gesture,
    # which grants transient user activation and would let showPicker() succeed.
    with page.expect_console_message(
        lambda msg: msg.text.startswith("showPicker:")
    ) as result:
        page.goto(server.PREFIX + "/activation.html?showPicker")
    assert (result.value).text == "showPicker:NotAllowedError"
    assert choosers == 0


def test_FC_027_user_activation_should_open_file_chooser_with_user_activation(
    page: Page, server: Server
) -> None:
    user_activation_before_each(page, server)
    page.goto(server.PREFIX + "/activation.html")
    with page.expect_file_chooser() as chooser_info:
        page.click("#once")
    chooser = chooser_info.value
    assert chooser

    # page.evaluate grants transient user activation in all browsers.
    page.goto(server.PREFIX + "/activation.html")
    with page.expect_file_chooser() as chooser2_info:
        page.evaluate("() => document.querySelector('input').click()")
    chooser2 = chooser2_info.value
    assert chooser2
    page.goto(server.PREFIX + "/activation.html")
    assert page.evaluate("() => window.showPicker()") == "ok"


def test_FC_028_user_activation_should_consume_user_activation_when_opening_file_chooser(
    page: Page, server: Server, browser_name: str
) -> None:
    user_activation_before_each(page, server)
    if browser_name == "webkit":
        pytest.skip(
            "fixme: WebKit does not consume user activation when opening the file chooser"
        )
    choosers = 0

    def on_file_chooser(_: FileChooser) -> None:
        nonlocal choosers
        choosers += 1

    page.on("filechooser", on_file_chooser)
    page.goto(server.PREFIX + "/activation.html")
    page.click("#twice")
    page.wait_for_timeout(500)
    assert choosers == 1
