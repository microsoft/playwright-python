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

from playwright.async_api import Locator, Page, expect


def _unshift(snapshot: str) -> str:
    lines = snapshot.split("\n")
    whitespace_prefix_length = 100
    for line in lines:
        if not line.strip():
            continue
        match = re.match(r"^(\s*)", line)
        if match and len(match[1]) < whitespace_prefix_length:
            whitespace_prefix_length = len(match[1])
    return "\n".join(
        [line[whitespace_prefix_length:] for line in lines if line.strip()]
    )


async def check_and_match_snapshot(locator: Locator, snapshot: str) -> None:
    assert await locator.aria_snapshot() == _unshift(snapshot)
    await expect(locator).to_match_aria_snapshot(snapshot)


async def test_should_snapshot(page: Page) -> None:
    await page.set_content("<h1>title</h1>")
    await check_and_match_snapshot(
        page.locator("body"),
        """
      - heading "title" [level=1]
    """,
    )


async def test_should_snapshot_list(page: Page) -> None:
    await page.set_content("<h1>title</h1><h1>title 2</h1>")
    await check_and_match_snapshot(
        page.locator("body"),
        """
      - heading "title" [level=1]
      - heading "title 2" [level=1]
    """,
    )


async def test_should_snapshot_list_with_list(page: Page) -> None:
    await page.set_content("<ul><li>one</li><li>two</li></ul>")
    await check_and_match_snapshot(
        page.locator("body"),
        """
      - list:
        - listitem: one
        - listitem: two
    """,
    )


async def test_should_snapshot_list_with_accessible_name(page: Page) -> None:
    await page.set_content('<ul aria-label="my list"><li>one</li><li>two</li></ul>')
    await check_and_match_snapshot(
        page.locator("body"),
        """
      - list "my list":
        - listitem: one
        - listitem: two
    """,
    )


async def test_should_snapshot_complex(page: Page) -> None:
    await page.set_content('<ul><li><a href="about:blank">link</a></li></ul>')
    await check_and_match_snapshot(
        page.locator("body"),
        """
      - list:
        - listitem:
          - link "link"
    """,
    )
