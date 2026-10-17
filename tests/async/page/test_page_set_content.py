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

"""Port of tests/page/page-set-content.spec.ts."""


import asyncio
from typing import Any

import pytest

from playwright.async_api import Error, Page, TimeoutError
from tests.server import Server, reactor

EXPECTED_OUTPUT = "<html><head></head><body><div>hello</div></body></html>"


async def test_PA_020_should_work_smoke(page: Page) -> None:
    await page.set_content("<div>hello</div>")
    result = await page.content()
    assert result == EXPECTED_OUTPUT


async def test_PA_021_should_work_with_domcontentloaded(page: Page) -> None:
    await page.set_content("<div>hello</div>", wait_until="domcontentloaded")
    result = await page.content()
    assert result == EXPECTED_OUTPUT


async def test_PA_022_should_work_with_commit(page: Page) -> None:
    await page.set_content("<div>hello</div>", wait_until="commit")
    result = await page.content()
    assert result == EXPECTED_OUTPUT


async def test_PA_023_should_work_with_doctype(page: Page) -> None:
    doctype = "<!DOCTYPE html>"
    await page.set_content(f"{doctype}<div>hello</div>")
    result = await page.content()
    assert result == f"{doctype}{EXPECTED_OUTPUT}"


async def test_PA_024_should_work_with_html_4_doctype(page: Page) -> None:
    doctype = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" '
        '"http://www.w3.org/TR/html4/strict.dtd">'
    )
    await page.set_content(f"{doctype}<div>hello</div>")
    result = await page.content()
    assert result == f"{doctype}{EXPECTED_OUTPUT}"


async def test_PA_025_should_include_shadow_roots(page: Page) -> None:
    html = '<!DOCTYPE html><html lang="en"><head></head><body><div id="host"><template shadowrootmode="open"><div id="nested"><template shadowrootmode="open"><span>nested</span></template><slot></slot></div></template><span>light</span></div><div id="closed"></div></body></html>'
    # Closed shadow roots are not accessible from script and are never serialized.
    await page.set_content(
        html.replace(
            '<div id="closed">',
            '<div id="closed"><template shadowrootmode="closed"><span>closed</span></template>',
        )
    )
    assert (
        await page.content()
        == '<!DOCTYPE html><html lang="en"><head></head><body><div id="host"><span>light</span></div><div id="closed"></div></body></html>'
    )
    assert await page.content(include_shadow=True) == html


async def test_PA_026_should_respect_timeout(page: Page, server: Server) -> None:
    img_path = "/img.png"
    # stall for image
    server.set_route(img_path, lambda request: None)
    with pytest.raises(TimeoutError):
        await page.set_content(
            f'<img src="{server.PREFIX + img_path}"></img>', timeout=1
        )


async def test_PA_027_should_respect_default_navigation_timeout(
    page: Page, server: Server
) -> None:
    page.set_default_navigation_timeout(1)
    img_path = "/img.png"
    # stall for image
    server.set_route(img_path, lambda request: None)
    with pytest.raises(TimeoutError) as exc_info:
        await page.set_content(f'<img src="{server.PREFIX + img_path}"></img>')
    assert "Page.set_content: Timeout 1ms exceeded." in exc_info.value.message


async def test_PA_028_should_await_resources_to_load(
    page: Page, server: Server
) -> None:
    img_path = "/img.png"
    # The request that wait_for_request() returns is the one that the route holds.
    server.set_route(img_path, lambda request: None)
    loaded = False

    async def set_content() -> None:
        nonlocal loaded
        await page.set_content(f'<img src="{server.PREFIX + img_path}"></img>')
        loaded = True

    content_task = asyncio.create_task(set_content())
    img_response = await server.wait_for_request(img_path)
    assert loaded is False
    reactor.callFromThread(img_response.finish)
    await content_task


async def test_PA_029_should_work_fast_enough(page: Page) -> None:
    for _ in range(20):
        await page.set_content("<div>yo</div>")


async def test_PA_030_should_work_with_tricky_content(page: Page) -> None:
    await page.set_content("<div>hello world</div>" + "\x7f")
    assert await page.eval_on_selector("div", "div => div.textContent") == "hello world"


async def test_PA_031_should_work_with_accents(page: Page) -> None:
    await page.set_content("<div>aberración</div>")
    assert await page.eval_on_selector("div", "div => div.textContent") == "aberración"


async def test_PA_032_should_work_with_emojis(page: Page) -> None:
    await page.set_content("<div>🐥</div>")
    assert await page.eval_on_selector("div", "div => div.textContent") == "🐥"


async def test_PA_033_should_work_with_newline(page: Page) -> None:
    await page.set_content("<div>\n</div>")
    assert await page.eval_on_selector("div", "div => div.textContent") == "\n"


async def test_PA_034_content_should_throw_nice_error_during_navigation(
    page: Page, server: Server
) -> None:
    for timeout in range(0, 200, 20):
        await page.set_content("<div>hello</div>")

        async def content_or_error() -> Any:
            await page.wait_for_timeout(timeout)
            try:
                return await page.content()
            except Error as e:
                return e

        _, content = await asyncio.gather(
            page.goto(server.EMPTY_PAGE), content_or_error()
        )
        empty_output = "<html><head></head><body></body></html>"
        if content != EXPECTED_OUTPUT and content != empty_output:
            assert isinstance(content, Error)
            assert (
                "Unable to retrieve content because the page is navigating and changing the content."
                in content.message
            )


async def test_PA_035_should_return_empty_content_there_is_no_iframe_src(
    page: Page, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip("fixme: there is no utility context")
    await page.set_content('<iframe src="javascript:console.log(1)"></iframe>')
    assert len(page.frames) == 2
    assert await page.frames[1].content() == "<html><head></head><body></body></html>"
