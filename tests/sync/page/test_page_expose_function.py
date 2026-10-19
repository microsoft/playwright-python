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

"""Port of tests/page/page-expose-function.spec.ts."""

import time
from typing import Any, Callable, Dict, List

import pytest

from playwright.sync_api import Error, JSHandle, Page
from tests.server import Server, TestServerRequest


def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while actual() != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert actual() == expected


def test_EF_001_expose_binding_should_work_smoke(page: Page) -> None:
    binding_sources: List[Dict] = []

    def add(source: Dict, a: int, b: int) -> int:
        binding_sources.append(source)
        return a + b

    page.expose_binding("add", add)
    result = page.evaluate(
        """async function() {
            return window['add'](5, 6);
        }"""
    )
    assert binding_sources[0]["context"] is page.context
    assert binding_sources[0]["page"] is page
    assert binding_sources[0]["frame"] is page.main_frame
    assert result == 11


def test_EF_002_should_work(page: Page, server: Server) -> None:
    page.expose_function("compute", lambda a, b: a * b)
    result = page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36


def test_EF_003_should_dispose(page: Page, server: Server) -> None:
    binding = page.expose_function("compute", lambda a, b: a * b)
    result = page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36
    binding.close()

    with pytest.raises(Error) as exc_info:
        page.evaluate(
            """async function() {
                return await window['compute'](9, 4);
            }"""
        )
    assert "is not a function" in exc_info.value.message


def test_EF_004_should_work_with_handles_and_complex_objects(
    page: Page, server: Server
) -> None:
    foo_handle = page.evaluate_handle(
        """() => {
            window['fooValue'] = { bar: 2 };
            return window['fooValue'];
        }"""
    )

    def handle() -> List[Dict[str, JSHandle]]:
        return [{"foo": foo_handle}]

    page.expose_function("handle", handle)
    equals = page.evaluate(
        """async function() {
            const value = await window['handle']();
            const [{ foo }] = value;
            return foo === window['fooValue'];
        }"""
    )
    assert equals is True


def test_EF_005_should_throw_exception_in_page_context(
    page: Page, server: Server
) -> None:
    def woof() -> None:
        raise Exception("WOOF WOOF")

    page.expose_function("woof", woof)
    result = page.evaluate(
        """async () => {
            try {
                await window['woof']();
            } catch (e) {
                return { message: e.message, stack: e.stack };
            }
        }"""
    )
    assert result["message"] == "WOOF WOOF"
    assert __file__ in result["stack"]


def test_EF_007_should_be_callable_from_inside_add_init_script(
    page: Page, server: Server
) -> None:
    called = False

    def woof() -> None:
        nonlocal called
        called = True

    page.expose_function("woof", woof)
    page.add_init_script("window['woof']()")
    page.reload()
    poll_until_equal(page, lambda: called, True)


def test_EF_008_should_survive_navigation(page: Page, server: Server) -> None:
    page.expose_function("compute", lambda a, b: a * b)

    page.goto(server.EMPTY_PAGE)
    result = page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36


def test_EF_009_should_await_returned_promise(page: Page, server: Server) -> None:
    def compute(a: int, b: int) -> int:
        return a * b

    page.expose_function("compute", compute)

    result = page.evaluate(
        """async function() {
            return await window['compute'](3, 5);
        }"""
    )
    assert result == 15


def test_EF_010_should_work_on_frames(page: Page, server: Server) -> None:
    def compute(a: int, b: int) -> int:
        return a * b

    page.expose_function("compute", compute)

    page.goto(server.PREFIX + "/frames/nested-frames.html")
    frame = page.frames[1]
    result = frame.evaluate(
        """async function() {
            return await window['compute'](3, 5);
        }"""
    )
    assert result == 15


def test_EF_011_should_work_on_frames_before_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/nested-frames.html")

    def compute(a: int, b: int) -> int:
        return a * b

    page.expose_function("compute", compute)

    frame = page.frames[1]
    result = frame.evaluate(
        """async function() {
            return await window['compute'](3, 5);
        }"""
    )
    assert result == 15


def test_EF_012_should_work_after_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.expose_function("compute", lambda a, b: a * b)

    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    result = page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36


def test_EF_013_should_work_with_complex_objects(page: Page, server: Server) -> None:
    page.expose_function("complexObject", lambda a, b: {"x": a["x"] + b["x"]})
    result = page.evaluate("async () => window['complexObject']({ x: 5 }, { x: 2 })")
    assert result["x"] == 7


def test_EF_014_should_throw_for_duplicate_registrations(page: Page) -> None:
    page.expose_function("foo", lambda: None)
    with pytest.raises(Error) as exc_info:
        page.expose_function("foo", lambda: None)
    assert (
        'Page.expose_function: Function "foo" has been already registered'
        in exc_info.value.message
    )


def test_EF_015_should_work_with_set_content(page: Page, server: Server) -> None:
    def compute(a: int, b: int) -> int:
        return a * b

    page.expose_function("compute", compute)
    page.set_content("<script>window.result = compute(3, 2)</script>")
    assert page.evaluate("window.result") == 6


def test_EF_016_should_alias_window_document_and_node(page: Page) -> None:
    objects: List[Any] = []
    page.expose_binding("log", lambda source, obj: objects.append(obj))
    page.evaluate("window.log([window, document, document.body])")
    assert objects[0] == ["ref: <Window>", "ref: <Document>", "ref: <Node>"]


def test_EF_017_should_serialize_cycles(page: Page) -> None:
    objects: List[Any] = []
    page.expose_binding("log", lambda source, obj: objects.append(obj))
    page.evaluate("const a = {}; a.b = a; window.log(a)")
    # Like `expect(object).toEqual(a)` where a.b = a.
    assert list(objects[0].keys()) == ["b"]
    assert objects[0]["b"] is objects[0]


def test_EF_018_should_work_with_overridden_console_object(page: Page) -> None:
    page.evaluate("() => window.console = null")
    assert page.evaluate("() => window.console === null")
    page.expose_function("add", lambda a, b: a + b)
    assert page.evaluate("add(5, 6)") == 11


def test_EF_019_should_work_with_busted_array_prototype_map_push(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""<script>
      Array.prototype.map = null;
      Array.prototype.push = null;
    </script>"""
        )
        request.finish()

    server.set_route("/test", handler)
    page.goto(server.PREFIX + "/test")
    page.expose_function("add", lambda a, b: a + b)
    assert page.evaluate("add(5, 6)") == 11


def test_EF_020_should_fail_with_busted_array_prototype_to_json(
    page: Page,
) -> None:
    page.evaluate_handle("() => Array.prototype.toJSON = () => '\"[]\"'")

    page.expose_function("add", lambda a, b: a + b)
    with pytest.raises(Error) as exc_info:
        page.evaluate("add(5, 6)")
    assert (
        "serializedArgs is not an array. This can happen when Array.prototype.toJSON is defined incorrectly"
        in exc_info.value.message
    )

    assert page.evaluate("() => [].toJSON()") == '"[]"'


def test_EF_021_expose_binding_should_work_in_parallel(
    page: Page, sync_gather: Callable
) -> None:
    sync_gather(
        lambda: page.expose_binding("foo", lambda source: 42),
        lambda: page.expose_binding("bar", lambda source: 42),
    )
    page.evaluate(
        """() => {
            window.foo();
            window.bar();
        }"""
    )
