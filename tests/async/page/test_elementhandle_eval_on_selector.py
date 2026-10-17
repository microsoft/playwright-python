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

"""Port of tests/page/elementhandle-eval-on-selector.spec.ts."""

import pytest

from playwright.async_api import Error, Page


async def test_EH_039_should_work(page: Page) -> None:
    await page.set_content(
        '<html><body><div class="tweet"><div class="like">100</div><div class="retweets">10</div></div></body></html>'
    )
    tweet = await page.query_selector(".tweet")
    assert tweet
    content = await tweet.eval_on_selector(".like", "node => node.innerText")
    assert content == "100"


async def test_EH_040_should_retrieve_content_from_subtree(page: Page) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"><div class="a">a-child-div</div></div>'
    await page.set_content(html_content)
    element_handle = await page.query_selector("#myId")
    assert element_handle
    content = await element_handle.eval_on_selector(".a", "node => node.innerText")
    assert content == "a-child-div"


async def test_EH_041_should_throw_in_case_of_missing_selector(page: Page) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"></div>'
    await page.set_content(html_content)
    element_handle = await page.query_selector("#myId")
    assert element_handle
    with pytest.raises(Error) as exc_info:
        await element_handle.eval_on_selector(".a", "node => node.innerText")
    assert (
        'ElementHandle.eval_on_selector: Failed to find element matching selector ".a"'
        in exc_info.value.message
    )


async def test_EH_042_should_work_for_all(page: Page) -> None:
    await page.set_content(
        '<html><body><div class="tweet"><div class="like">100</div><div class="like">10</div></div></body></html>'
    )
    tweet = await page.query_selector(".tweet")
    assert tweet
    content = await tweet.eval_on_selector_all(
        ".like", "nodes => nodes.map(n => n.innerText)"
    )
    assert content == ["100", "10"]


async def test_EH_043_should_retrieve_content_from_subtree_for_all(page: Page) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"><div class="a">a1-child-div</div><div class="a">a2-child-div</div></div>'
    await page.set_content(html_content)
    element_handle = await page.query_selector("#myId")
    assert element_handle
    content = await element_handle.eval_on_selector_all(
        ".a", "nodes => nodes.map(n => n.innerText)"
    )
    assert content == ["a1-child-div", "a2-child-div"]


async def test_EH_044_should_not_throw_in_case_of_missing_selector_for_all(
    page: Page,
) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"></div>'
    await page.set_content(html_content)
    element_handle = await page.query_selector("#myId")
    assert element_handle
    nodes_length = await element_handle.eval_on_selector_all(
        ".a", "nodes => nodes.length"
    )
    assert nodes_length == 0
