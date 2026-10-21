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

"""Port of tests/page/page-set-input-files.spec.ts."""

import errno
import os
from pathlib import Path
from typing import Any, List

import pytest

from playwright.sync_api import Error, Page
from tests.helpers.form_files_route import route_form_files
from tests.server import Server
from tests.utils import must, relative_path


def write_large_file(path: Path, chunk: bytes, count: int) -> None:
    with path.open("wb") as file:
        for _ in range(count):
            file.write(chunk)


def test_IF_001_should_upload_the_file(
    page: Page, server: Server, assetdir: Path
) -> None:
    page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = relative_path(assetdir / "file-to-upload.txt")
    input = must(page.query_selector("input"))
    input.set_input_files(file_path)
    assert page.evaluate("e => e.files[0].name", input) == "file-to-upload.txt"
    assert (
        page.evaluate(
            """e => {
    const reader = new FileReader();
    const promise = new Promise(fulfill => reader.onload = fulfill);
    reader.readAsText(e.files[0]);
    return promise.then(() => reader.result);
  }""",
            input,
        )
        == "contents of the file"
    )


def test_IF_002_should_upload_a_folder(
    page: Page, server: Server, tmp_path: Path, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.goto(server.PREFIX + "/input/folderupload.html")
    input = must(page.query_selector("input"))
    dir = tmp_path / "file-upload-test"
    dir.mkdir(parents=True, exist_ok=True)
    (dir / "file1.txt").write_text("file1 content")
    (dir / "file2").write_text("file2 content")
    (dir / "sub-dir").mkdir()
    (dir / "sub-dir" / "really.txt").write_text("sub-dir file content")
    input.set_input_files(dir)
    assert set(
        page.evaluate("e => [...e.files].map(f => f.webkitRelativePath)", input)
    ) == {
        # Note: this did not work before Chrome 127, see https://issues.chromium.org/issues/345393164.
        "file-upload-test/sub-dir/really.txt",
        "file-upload-test/file1.txt",
        "file-upload-test/file2",
    }
    webkit_relative_paths: List[str] = page.evaluate(
        "e => [...e.files].map(f => f.webkitRelativePath)", input
    )
    for i in range(len(webkit_relative_paths)):
        content = input.evaluate(
            """(e, i) => {
      const reader = new FileReader();
      const promise = new Promise(fulfill => reader.onload = fulfill);
      reader.readAsText(e.files[i]);
      return promise.then(() => reader.result);
    }""",
            i,
        )
        assert content == (dir / ".." / webkit_relative_paths[i]).read_text()


def test_IF_003_should_upload_a_folder_via_label(
    page: Page, tmp_path: Path, is_frozen_webkit: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/43367
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.set_content(
        '<label for="folder">Folder</label><input id="folder" type="file" webkitdirectory>'
    )
    dir = tmp_path / "file-upload-test"
    dir.mkdir(parents=True, exist_ok=True)
    (dir / "file1.txt").write_text("file1 content")
    page.get_by_text("Folder").set_input_files(dir)
    assert page.locator("input").evaluate(
        "e => [...e.files].map(f => f.webkitRelativePath)"
    ) == ["file-upload-test/file1.txt"]


def test_IF_004_should_upload_a_folder_and_throw_for_multiple_directories(
    page: Page, server: Server, tmp_path: Path, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.goto(server.PREFIX + "/input/folderupload.html")
    input = must(page.query_selector("input"))
    dir = tmp_path / "file-upload-test"
    (dir / "folder1").mkdir(parents=True, exist_ok=True)
    (dir / "folder1" / "file1.txt").write_text("file1 content")
    (dir / "folder2").mkdir(parents=True, exist_ok=True)
    (dir / "folder2" / "file2.txt").write_text("file2 content")
    with pytest.raises(Error) as exc_info:
        input.set_input_files([dir / "folder1", dir / "folder2"])
    assert "Multiple directories are not supported" in exc_info.value.message


def test_IF_005_should_throw_if_a_directory_and_files_are_passed(
    page: Page, server: Server, tmp_path: Path, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.goto(server.PREFIX + "/input/folderupload.html")
    input = must(page.query_selector("input"))
    dir = tmp_path / "file-upload-test"
    (dir / "folder1").mkdir(parents=True, exist_ok=True)
    (dir / "folder1" / "file1.txt").write_text("file1 content")
    with pytest.raises(Error) as exc_info:
        input.set_input_files([dir / "folder1", dir / "folder1" / "file1.txt"])
    assert (
        "File paths must be all files or a single directory" in exc_info.value.message
    )


def test_IF_006_should_throw_when_uploading_a_folder_in_a_normal_file_upload_input(
    page: Page, server: Server, tmp_path: Path, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.goto(server.PREFIX + "/input/fileupload.html")
    input = must(page.query_selector("input"))
    dir = tmp_path / "file-upload-test"
    dir.mkdir(parents=True, exist_ok=True)
    (dir / "file1.txt").write_text("file1 content")
    with pytest.raises(Error) as exc_info:
        input.set_input_files(dir)
    assert (
        "File input does not support directories, pass individual files instead"
        in exc_info.value.message
    )


def test_IF_007_should_throw_when_uploading_a_file_in_a_directory_upload_input(
    page: Page, server: Server, assetdir: Path, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.goto(server.PREFIX + "/input/folderupload.html")
    input = must(page.query_selector("input"))
    with pytest.raises(Error) as exc_info:
        input.set_input_files(assetdir / "file to upload.txt")
    assert (
        "[webkitdirectory] input requires passing a path to a directory"
        in exc_info.value.message
    )


def test_IF_008_should_upload_a_file_after_popup(
    page: Page, server: Server, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/29923
    page.goto(server.PREFIX + "/input/fileupload.html")
    with page.expect_popup() as popup_info:
        page.evaluate("() => window['__popup'] = window.open('about:blank')")
    popup = popup_info.value
    popup.close()
    file_path = relative_path(assetdir / "file-to-upload.txt")
    input = must(page.query_selector("input"))
    input.set_input_files(file_path)
    assert page.evaluate("e => e.files[0].name", input) == "file-to-upload.txt"


@pytest.mark.slow
def test_IF_009_should_upload_large_file(
    page: Page, server: Server, tmp_path: Path
) -> None:
    page.goto(server.PREFIX + "/input/fileupload.html")
    upload_file = tmp_path / "200MB.zip"
    write_large_file(upload_file, b"A" * 4 * 1024, 50 * 1024)
    input = page.locator('input[type="file"]')
    events = input.evaluate_handle(
        """e => {
    const events = [];
    e.addEventListener('input', () => events.push('input'));
    e.addEventListener('change', () => events.push('change'));
    return events;
  }"""
    )
    input.set_input_files(upload_file)
    assert input.evaluate("e => e.files[0].name") == "200MB.zip"
    assert events.evaluate("e => e") == ["input", "change"]
    files = route_form_files(server, "/upload")
    with page.expect_response(server.PREFIX + "/upload"):
        page.click("input[type=submit]")
    file1 = files["file1"]
    assert file1.filename == "200MB.zip"
    assert len(file1.data) == 200 * 1024 * 1024
    upload_file.unlink()


def test_IF_010_should_throw_an_error_if_the_file_does_not_exist(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/fileupload.html")
    input = must(page.query_selector("input"))
    # The Python client reads the file itself and raises Python's ENOENT error. Its
    # message depends on the OS, unlike Node.js's 'ENOENT: no such file or directory'.
    with pytest.raises(FileNotFoundError) as exc_info:
        input.set_input_files("i actually do not exist.txt")
    assert exc_info.value.errno == errno.ENOENT
    assert "i actually do not exist.txt" in str(exc_info.value)


@pytest.mark.slow
def test_IF_011_should_upload_large_file_with_relative_path(
    page: Page, server: Server, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Upstream writes the file to testInfo.outputPath(), under the current directory.
    # tmp_path can be on another drive (Windows), so make it the current directory.
    monkeypatch.chdir(tmp_path)
    page.goto(server.PREFIX + "/input/fileupload.html")
    upload_file = tmp_path / "200MB.zip"
    write_large_file(upload_file, b"A" * 4 * 1024, 50 * 1024)
    input = page.locator('input[type="file"]')
    events = input.evaluate_handle(
        """e => {
    const events = [];
    e.addEventListener('input', () => events.push('input'));
    e.addEventListener('change', () => events.push('change'));
    return events;
  }"""
    )
    relative_upload_path = relative_path(upload_file)
    assert not os.path.isabs(relative_upload_path)
    input.set_input_files(relative_upload_path)
    assert input.evaluate("e => e.files[0].name") == "200MB.zip"
    assert events.evaluate("e => e") == ["input", "change"]
    files = route_form_files(server, "/upload")
    with page.expect_response(server.PREFIX + "/upload"):
        page.click("input[type=submit]")
    file1 = files["file1"]
    assert file1.filename == "200MB.zip"
    assert len(file1.data) == 200 * 1024 * 1024
    upload_file.unlink()


def test_IF_012_should_upload_the_file_with_spaces_in_name(
    page: Page, server: Server, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/17451
    page.goto(server.PREFIX + "/input/fileupload.html")
    file_path = relative_path(assetdir / "file to upload.txt")
    input = must(page.query_selector("input"))
    input.set_input_files(file_path)
    assert page.evaluate("e => e.files[0].name", input) == "file to upload.txt"
    assert (
        page.evaluate(
            """e => {
    const reader = new FileReader();
    const promise = new Promise(fulfill => reader.onload = fulfill);
    reader.readAsText(e.files[0]);
    return promise.then(() => reader.result);
  }""",
            input,
        )
        == "contents of the file"
    )


def test_IF_013_should_work_smoke(page: Page, assetdir: Path) -> None:
    page.set_content("<input type=file>")
    page.set_input_files("input", assetdir / "file-to-upload.txt")
    assert page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


def test_IF_014_should_set_from_memory(page: Page) -> None:
    page.set_content("<input type=file>")
    page.set_input_files(
        "input",
        {
            "name": "test.txt",
            "mimeType": "text/plain",
            "buffer": b"this is a test",
        },
    )
    assert page.eval_on_selector("input", "input => input.files.length") == 1
    assert page.eval_on_selector("input", "input => input.files[0].name") == "test.txt"


def test_IF_015_should_work_with_csp(
    page: Page, server: Server, assetdir: Path
) -> None:
    server.set_csp("/empty.html", 'default-src "none"')
    page.goto(server.EMPTY_PAGE)
    page.set_content("<input type=file>")
    page.set_input_files("input", assetdir / "file-to-upload.txt")
    assert page.eval_on_selector("input", "input => input.files.length") == 1
    assert (
        page.eval_on_selector("input", "input => input.files[0].name")
        == "file-to-upload.txt"
    )


def test_IF_016_should_detect_mime_type(
    page: Page, server: Server, assetdir: Path
) -> None:
    files = route_form_files(server, "/upload")
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <form action="/upload" method="post" enctype="multipart/form-data" >
      <input type="file" name="file1">
      <input type="file" name="file2">
      <input type="submit" value="Submit">
    </form>"""
    )
    must(page.query_selector("input[name=file1]")).set_input_files(
        assetdir / "file-to-upload.txt"
    )
    must(page.query_selector("input[name=file2]")).set_input_files(
        assetdir / "pptr.png"
    )
    # The route sends the response after it has parsed the form.
    with page.expect_response(server.PREFIX + "/upload"):
        page.click("input[type=submit]")
    file1 = files["file1"]
    file2 = files["file2"]
    assert file1.filename == "file-to-upload.txt"
    assert file1.content_type == "text/plain"
    assert file1.data == (assetdir / "file-to-upload.txt").read_bytes()
    assert file2.filename == "pptr.png"
    assert file2.content_type == "image/png"
    assert file2.data == (assetdir / "pptr.png").read_bytes()


# @see https://github.com/microsoft/playwright/issues/4704
def test_IF_017_should_not_trim_big_uploaded_files(page: Page, server: Server) -> None:
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


def test_IF_018_should_emit_input_and_change_events(page: Page, assetdir: Path) -> None:
    events: List[Any] = []
    page.expose_function("eventHandled", lambda e: events.append(e))
    page.set_content(
        """
  <input id=input type=file></input>
  <script>
    input.addEventListener('input', e => eventHandled({ type: e.type }));
    input.addEventListener('change', e => eventHandled({ type: e.type }));
  </script>"""
    )
    must(page.query_selector("input")).set_input_files(assetdir / "file-to-upload.txt")
    assert len(events) == 2
    assert events[0]["type"] == "input"
    assert events[1]["type"] == "change"


def test_IF_019_input_event_composed_should_be_true_and_cross_shadow_dom_boundary(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28726
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """<body><script>
  const div = document.createElement('div');
  const shadowRoot = div.attachShadow({mode: 'open'});
  shadowRoot.innerHTML = '<input type=file></input>';
  document.body.appendChild(div);
</script></body>"""
    )
    page.locator("body").evaluate(
        """select => {
    window.firedBodyEvents = [];
    for (const event of ['input', 'change']) {
      select.addEventListener(event, e => {
        window.firedBodyEvents.push(e.type + ':' + e.composed);
      }, false);
    }
  }"""
    )

    page.locator("input").evaluate(
        """select => {
    window.firedEvents = [];
    for (const event of ['input', 'change']) {
      select.addEventListener(event, e => {
        window.firedEvents.push(e.type + ':' + e.composed);
      }, false);
    }
  }"""
    )
    page.locator("input").set_input_files(
        {
            "name": "test.txt",
            "mimeType": "text/plain",
            "buffer": b"this is a test",
        }
    )
    assert page.evaluate("() => window['firedEvents']") == [
        "input:true",
        "change:false",
    ]
    assert page.evaluate("() => window['firedBodyEvents']") == ["input:true"]


def test_IF_020_input_should_trigger_events_when_files_changed_second_time(
    page: Page, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/20079
    page.set_content("<input type=file multiple=true/>")

    input = page.locator("input")
    events = input.evaluate_handle(
        """e => {
    const events = [];
    e.addEventListener('input', () => events.push('input'));
    e.addEventListener('change', () => events.push('change'));
    return events;
  }"""
    )

    input.set_input_files(assetdir / "file-to-upload.txt")
    assert input.evaluate("e => e.files[0].name") == "file-to-upload.txt"
    assert events.evaluate("e => e") == ["input", "change"]

    events.evaluate("e => e.length = 0")

    input.set_input_files(assetdir / "pptr.png")
    assert input.evaluate("e => e.files[0].name") == "pptr.png"
    assert events.evaluate("e => e") == ["input", "change"]


def test_IF_021_should_preserve_last_modified_timestamp(
    page: Page, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/27452
    page.set_content("<input type=file multiple=true/>")
    input = page.locator("input")
    files = ["file-to-upload.txt", "file-to-upload-2.txt"]
    input.set_input_files([assetdir / f for f in files])
    assert input.evaluate("e => [...e.files].map(f => f.name)") == files
    timestamps = input.evaluate("e => [...e.files].map(f => f.lastModified)")
    expected_timestamps = [
        round(os.stat(assetdir / file).st_mtime_ns / 1_000_000) for file in files
    ]
    # On Linux browser sometimes reduces the timestamp by 1ms: 1696272058110.0715  -> 1696272058109 or even
    # rounds it to seconds in WebKit: 1696272058110 -> 1696272058000.
    for i in range(len(timestamps)):
        assert (
            abs(timestamps[i] - expected_timestamps[i]) <= 1000
        ), f"expected: {expected_timestamps}; actual: {timestamps}"
