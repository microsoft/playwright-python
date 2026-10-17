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

"""Port of tests/page/page-add-script-tag.spec.ts."""

import os
from pathlib import Path
from typing import Optional

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_AT_001_should_throw_an_error_if_no_options_are_provided(
    page: Page, server: Server
) -> None:
    error: Optional[Error] = None
    try:
        await page.add_script_tag()
    except Error as e:
        error = e
    assert error
    assert "Provide an object with a `url`, `path` or `content` property" in (
        error.message
    )


async def test_AT_002_should_work_with_a_url(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    script_handle = await page.add_script_tag(url="/injectedfile.js")
    assert script_handle.as_element() is not None
    assert await page.evaluate("() => window['__injected']") == 42


async def test_AT_003_should_work_with_a_url_and_type_module(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.add_script_tag(url="/es6/es6import.js", type="module")
    assert await page.evaluate("() => window['__es6injected']") == 42


async def test_AT_004_should_work_with_a_path_and_type_module(
    page: Page, server: Server, assetdir: Path
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.add_script_tag(path=assetdir / "es6" / "es6pathimport.js", type="module")
    await page.wait_for_function("window.__es6injected")
    assert await page.evaluate("() => window['__es6injected']") == 42


async def test_AT_005_should_work_with_a_content_and_type_module(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.add_script_tag(
        content="import num from '/es6/es6module.js';window.__es6injected = num;",
        type="module",
    )
    await page.wait_for_function("window.__es6injected")
    assert await page.evaluate("() => window['__es6injected']") == 42


async def test_AT_006_should_throw_an_error_if_loading_from_url_fail(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    error: Optional[Error] = None
    try:
        await page.add_script_tag(url="/nonexistfile.js")
    except Error as e:
        error = e
    assert error is not None


async def test_AT_007_should_work_with_a_path(
    page: Page, server: Server, assetdir: Path
) -> None:
    await page.goto(server.EMPTY_PAGE)
    script_handle = await page.add_script_tag(path=assetdir / "injectedfile.js")
    assert script_handle.as_element() is not None
    assert await page.evaluate("() => window['__injected']") == 42


@pytest.mark.skip_browser("webkit")
async def test_AT_008_should_include_source_url_when_path_is_provided(
    page: Page, server: Server, assetdir: Path
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.add_script_tag(path=assetdir / "injectedfile.js")
    result = await page.evaluate("() => window['__injectedError'].stack")
    assert os.path.join("assets", "injectedfile.js") in result


async def test_AT_009_should_work_with_content(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    script_handle = await page.add_script_tag(content='window["__injected"] = 35;')
    assert script_handle.as_element() is not None
    assert await page.evaluate("() => window['__injected']") == 35


async def test_AT_010_should_throw_when_added_with_content_to_the_csp_page(
    page: Page, server: Server
) -> None:
    # Firefox fires onload for blocked script before it issues the CSP console error.
    await page.goto(server.PREFIX + "/csp.html")
    error: Optional[Error] = None
    try:
        await page.add_script_tag(content='window["__injected"] = 35;')
    except Error as e:
        error = e
    assert error


async def test_AT_011_should_throw_when_added_with_url_to_the_csp_page(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/csp.html")
    error: Optional[Error] = None
    try:
        await page.add_script_tag(url=server.CROSS_PROCESS_PREFIX + "/injectedfile.js")
    except Error as e:
        error = e
    assert error


async def test_AT_012_should_throw_a_nice_error_when_the_request_fails(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/this_does_not_exist.js"
    with pytest.raises(Error) as exc_info:
        await page.add_script_tag(url=url)
    assert url in exc_info.value.message
