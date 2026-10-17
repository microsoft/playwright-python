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

import asyncio
import time
from typing import Any, Callable, Dict, List

import pytest

from playwright.async_api import Error, JSHandle, Page
from tests.server import Server, TestServerRequest


async def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while actual() != expected and time.monotonic() < deadline:
        await page.wait_for_timeout(100)
    assert actual() == expected


async def test_EF_001_expose_binding_should_work_smoke(page: Page) -> None:
    binding_sources: List[Dict] = []

    def add(source: Dict, a: int, b: int) -> int:
        binding_sources.append(source)
        return a + b

    await page.expose_binding("add", add)
    result = await page.evaluate(
        """async function() {
            return window['add'](5, 6);
        }"""
    )
    assert binding_sources[0]["context"] is page.context
    assert binding_sources[0]["page"] is page
    assert binding_sources[0]["frame"] is page.main_frame
    assert result == 11


async def test_EF_002_should_work(page: Page, server: Server) -> None:
    await page.expose_function("compute", lambda a, b: a * b)
    result = await page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36


async def test_EF_003_should_dispose(page: Page, server: Server) -> None:
    binding = await page.expose_function("compute", lambda a, b: a * b)
    result = await page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36
    await binding.close()

    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """async function() {
                return await window['compute'](9, 4);
            }"""
        )
    assert "is not a function" in exc_info.value.message


@pytest.mark.xfail(
    reason="python: a JSHandle returned from an exposed function is not sent as a handle; the page gets {}",
    strict=True,
)
async def test_EF_004_should_work_with_handles_and_complex_objects(
    page: Page, server: Server
) -> None:
    foo_handle = await page.evaluate_handle(
        """() => {
            window['fooValue'] = { bar: 2 };
            return window['fooValue'];
        }"""
    )

    def handle() -> List[Dict[str, JSHandle]]:
        return [{"foo": foo_handle}]

    await page.expose_function("handle", handle)
    equals = await page.evaluate(
        """async function() {
            const value = await window['handle']();
            const [{ foo }] = value;
            return foo === window['fooValue'];
        }"""
    )
    assert equals is True


async def test_EF_005_should_throw_exception_in_page_context(
    page: Page, server: Server
) -> None:
    def woof() -> None:
        raise Exception("WOOF WOOF")

    await page.expose_function("woof", woof)
    result = await page.evaluate(
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


async def test_EF_007_should_be_callable_from_inside_add_init_script(
    page: Page, server: Server
) -> None:
    called = False

    def woof() -> None:
        nonlocal called
        called = True

    await page.expose_function("woof", woof)
    await page.add_init_script("window['woof']()")
    await page.reload()
    await poll_until_equal(page, lambda: called, True)


async def test_EF_008_should_survive_navigation(page: Page, server: Server) -> None:
    await page.expose_function("compute", lambda a, b: a * b)

    await page.goto(server.EMPTY_PAGE)
    result = await page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36


async def test_EF_009_should_await_returned_promise(page: Page, server: Server) -> None:
    async def compute(a: int, b: int) -> int:
        return a * b

    await page.expose_function("compute", compute)

    result = await page.evaluate(
        """async function() {
            return await window['compute'](3, 5);
        }"""
    )
    assert result == 15


async def test_EF_010_should_work_on_frames(page: Page, server: Server) -> None:
    async def compute(a: int, b: int) -> int:
        return a * b

    await page.expose_function("compute", compute)

    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    frame = page.frames[1]
    result = await frame.evaluate(
        """async function() {
            return await window['compute'](3, 5);
        }"""
    )
    assert result == 15


async def test_EF_011_should_work_on_frames_before_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/nested-frames.html")

    async def compute(a: int, b: int) -> int:
        return a * b

    await page.expose_function("compute", compute)

    frame = page.frames[1]
    result = await frame.evaluate(
        """async function() {
            return await window['compute'](3, 5);
        }"""
    )
    assert result == 15


async def test_EF_012_should_work_after_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.expose_function("compute", lambda a, b: a * b)

    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    result = await page.evaluate(
        """async function() {
            return await window['compute'](9, 4);
        }"""
    )
    assert result == 36


async def test_EF_013_should_work_with_complex_objects(
    page: Page, server: Server
) -> None:
    await page.expose_function("complexObject", lambda a, b: {"x": a["x"] + b["x"]})
    result = await page.evaluate(
        "async () => window['complexObject']({ x: 5 }, { x: 2 })"
    )
    assert result["x"] == 7


@pytest.mark.xfail(
    reason="python: client-side expose_function errors lack the 'Page.expose_function: ' prefix",
    strict=True,
)
async def test_EF_014_should_throw_for_duplicate_registrations(page: Page) -> None:
    await page.expose_function("foo", lambda: None)
    with pytest.raises(Error) as exc_info:
        await page.expose_function("foo", lambda: None)
    assert (
        'Page.expose_function: Function "foo" has been already registered'
        in exc_info.value.message
    )


async def test_EF_015_should_work_with_set_content(page: Page, server: Server) -> None:
    async def compute(a: int, b: int) -> int:
        return a * b

    await page.expose_function("compute", compute)
    await page.set_content("<script>window.result = compute(3, 2)</script>")
    assert await page.evaluate("window.result") == 6


async def test_EF_016_should_alias_window_document_and_node(page: Page) -> None:
    objects: List[Any] = []
    await page.expose_binding("log", lambda source, obj: objects.append(obj))
    await page.evaluate("window.log([window, document, document.body])")
    assert objects[0] == ["ref: <Window>", "ref: <Document>", "ref: <Node>"]


async def test_EF_017_should_serialize_cycles(page: Page) -> None:
    objects: List[Any] = []
    await page.expose_binding("log", lambda source, obj: objects.append(obj))
    await page.evaluate("const a = {}; a.b = a; window.log(a)")
    # Like `expect(object).toEqual(a)` where a.b = a.
    assert list(objects[0].keys()) == ["b"]
    assert objects[0]["b"] is objects[0]


async def test_EF_018_should_work_with_overridden_console_object(page: Page) -> None:
    await page.evaluate("() => window.console = null")
    assert await page.evaluate("() => window.console === null")
    await page.expose_function("add", lambda a, b: a + b)
    assert await page.evaluate("add(5, 6)") == 11


async def test_EF_019_should_work_with_busted_array_prototype_map_push(
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
    await page.goto(server.PREFIX + "/test")
    await page.expose_function("add", lambda a, b: a + b)
    assert await page.evaluate("add(5, 6)") == 11


async def test_EF_020_should_fail_with_busted_array_prototype_to_json(
    page: Page,
) -> None:
    await page.evaluate_handle("() => Array.prototype.toJSON = () => '\"[]\"'")

    await page.expose_function("add", lambda a, b: a + b)
    with pytest.raises(Error) as exc_info:
        await page.evaluate("add(5, 6)")
    assert (
        "serializedArgs is not an array. This can happen when Array.prototype.toJSON is defined incorrectly"
        in exc_info.value.message
    )

    assert await page.evaluate("() => [].toJSON()") == '"[]"'


async def test_EF_021_expose_binding_should_work_in_parallel(page: Page) -> None:
    await asyncio.gather(
        page.expose_binding("foo", lambda source: 42),
        page.expose_binding("bar", lambda source: 42),
    )
    await page.evaluate(
        """() => {
            window.foo();
            window.bar();
        }"""
    )
