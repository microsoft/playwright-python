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

"""Port of tests/page/locator-evaluate.spec.ts."""

from playwright.sync_api import Page
from tests.server import Server


def test_LO_084_should_work_smoke(page: Page, server: Server) -> None:
    page.set_content(
        '<html><body><div class="tweet"><div class="like">100</div><div class="retweets">10</div></div></body></html>'
    )
    tweet = page.locator(".tweet .like")
    content = tweet.evaluate("node => node.innerText")
    assert content == "100"


def test_LO_085_should_retrieve_content_from_subtree(
    page: Page, server: Server
) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"><div class="a">a-child-div</div></div>'
    page.set_content(html_content)
    element_handle = page.locator("#myId .a")
    content = element_handle.evaluate("node => node.innerText")
    assert content == "a-child-div"


def test_LO_086_should_work_for_all(page: Page, server: Server) -> None:
    page.set_content(
        '<html><body><div class="tweet"><div class="like">100</div><div class="like">10</div></div></body></html>'
    )
    tweet = page.locator(".tweet .like")
    content = tweet.evaluate_all("nodes => nodes.map(n => n.innerText)")
    assert content == ["100", "10"]


def test_LO_087_should_retrieve_content_from_subtree_for_all(
    page: Page, server: Server
) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"><div class="a">a1-child-div</div><div class="a">a2-child-div</div></div>'
    page.set_content(html_content)
    element = page.locator("#myId .a")
    content = element.evaluate_all("nodes => nodes.map(n => n.innerText)")
    assert content == ["a1-child-div", "a2-child-div"]


def test_LO_088_should_not_throw_in_case_of_missing_selector_for_all(
    page: Page, server: Server
) -> None:
    html_content = '<div class="a">not-a-child-div</div><div id="myId"></div>'
    page.set_content(html_content)
    element = page.locator("#myId .a")
    nodes_length = element.evaluate_all("nodes => nodes.length")
    assert nodes_length == 0
