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

import re

import pytest

from playwright.async_api import Error, Page


async def test_wait_for_url_should_work(page: Page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        "url => window.location.href = url", server.PREFIX + "/grid.html"
    )
    await page.wait_for_url("**/grid.html")
    assert "grid.html" in page.url


async def test_wait_for_url_should_respect_timeout(page: Page, server):
    await page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        await page.wait_for_url("**/frame.html", timeout=2500)
    assert "Timeout 2500ms exceeded" in exc_info.value.message


async def test_wait_for_url_should_work_with_both_domcontentloaded_and_load(
    page: Page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.wait_for_url("**/*", wait_until="domcontentloaded")
    await page.wait_for_url("**/*", wait_until="load")


async def test_wait_for_url_should_work_with_clicking_on_anchor_links(
    page: Page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="#foobar">foobar</a>')
    await page.click("a")
    await page.wait_for_url("**/*#foobar")
    assert page.url == server.EMPTY_PAGE + "#foobar"


async def test_wait_for_url_should_work_with_history_push_state(page: Page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <a onclick='javascript:pushState()'>SPA</a>
        <script>
            function pushState() { history.pushState({}, '', 'wow.html') }
        </script>
    """
    )
    await page.click("a")
    await page.wait_for_url("**/wow.html")
    assert page.url == server.PREFIX + "/wow.html"


async def test_wait_for_url_should_work_with_history_replace_state(page: Page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <a onclick='javascript:replaceState()'>SPA</a>
        <script>
            function replaceState() { history.replaceState({}, '', '/replaced.html') }
        </script>
    """
    )
    await page.click("a")
    await page.wait_for_url("**/replaced.html")
    assert page.url == server.PREFIX + "/replaced.html"


async def test_wait_for_url_should_work_with_dom_history_back_forward(
    page: Page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
      <a id=back onclick='javascript:go_back()'>back</a>
      <a id=forward onclick='javascript:go_forward()'>forward</a>
      <script>
        function go_back() { history.back(); }
        function go_forward() { history.forward(); }
        history.pushState({}, '', '/first.html')
        history.pushState({}, '', '/second.html')
      </script>
    """
    )

    assert page.url == server.PREFIX + "/second.html"

    await page.click("a#back"),
    await page.wait_for_url("**/first.html")
    assert page.url == server.PREFIX + "/first.html"

    await page.click("a#forward"),
    await page.wait_for_url("**/second.html")
    assert page.url == server.PREFIX + "/second.html"


async def test_wait_for_url_should_work_with_url_match_for_same_document_navigations(
    page: Page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("history.pushState({}, '', '/first.html')")
    await page.evaluate("history.pushState({}, '', '/second.html')")
    await page.evaluate("history.pushState({}, '', '/third.html')")
    await page.wait_for_url(re.compile(r"third\.html"))
    assert "/third.html" in page.url
