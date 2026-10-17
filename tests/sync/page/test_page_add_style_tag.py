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

"""Port of tests/page/page-add-style-tag.spec.ts."""

import os
from pathlib import Path
from typing import Optional

from playwright.sync_api import Error, Page
from tests.server import Server

BODY_BACKGROUND_COLOR = (
    "window.getComputedStyle(document.querySelector('body'))"
    ".getPropertyValue('background-color')"
)


def test_AT_013_should_throw_an_error_if_no_options_are_provided(
    page: Page, server: Server
) -> None:
    error: Optional[Error] = None
    try:
        page.add_style_tag()
    except Error as e:
        error = e
    assert error
    assert "Provide an object with a `url`, `path` or `content` property" in (
        error.message
    )


def test_AT_014_should_work_with_a_url_smoke(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    style_handle = page.add_style_tag(url="/injectedstyle.css")
    assert style_handle.as_element() is not None
    assert page.evaluate(BODY_BACKGROUND_COLOR) == "rgb(255, 0, 0)"


def test_AT_015_should_throw_an_error_if_loading_from_url_fail(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    error: Optional[Error] = None
    try:
        page.add_style_tag(url="/nonexistfile.js")
    except Error as e:
        error = e
    assert error is not None


def test_AT_016_should_work_with_a_path(
    page: Page, server: Server, assetdir: Path
) -> None:
    page.goto(server.EMPTY_PAGE)
    style_handle = page.add_style_tag(path=assetdir / "injectedstyle.css")
    assert style_handle.as_element() is not None
    assert page.evaluate(BODY_BACKGROUND_COLOR) == "rgb(255, 0, 0)"


def test_AT_017_should_include_source_url_when_path_is_provided(
    page: Page, server: Server, assetdir: Path
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.add_style_tag(path=assetdir / "injectedstyle.css")
    style_handle = page.query_selector("style")
    style_content = page.evaluate("style => style.innerHTML", style_handle)
    assert os.path.join("assets", "injectedstyle.css") in style_content


def test_AT_018_should_work_with_content(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    style_handle = page.add_style_tag(content="body { background-color: green; }")
    assert style_handle.as_element() is not None
    assert page.evaluate(BODY_BACKGROUND_COLOR) == "rgb(0, 128, 0)"


def test_AT_019_should_throw_when_added_with_content_to_the_csp_page(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/csp.html")
    error: Optional[Error] = None
    try:
        page.add_style_tag(content="body { background-color: green; }")
    except Error as e:
        error = e
    assert error


def test_AT_020_should_throw_when_added_with_url_to_the_csp_page(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/csp.html")
    error: Optional[Error] = None
    try:
        page.add_style_tag(url=server.CROSS_PROCESS_PREFIX + "/injectedstyle.css")
    except Error as e:
        error = e
    assert error
