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

from playwright.sync_api import Locator, Page, expect


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


def check_and_match_snapshot(locator: Locator, snapshot: str) -> None:
    assert locator.aria_snapshot() == _unshift(snapshot)
    expect(locator).to_match_aria_snapshot(snapshot)


def test_should_snapshot(page: Page) -> None:
    page.set_content("<h1>title</h1>")
    check_and_match_snapshot(
        page.locator("body"),
        """
      - heading "title" [level=1]
    """,
    )


def test_should_snapshot_list(page: Page) -> None:
    page.set_content("<h1>title</h1><h1>title 2</h1>")
    check_and_match_snapshot(
        page.locator("body"),
        """
      - heading "title" [level=1]
      - heading "title 2" [level=1]
    """,
    )


def test_should_snapshot_list_with_list(page: Page) -> None:
    page.set_content("<ul><li>one</li><li>two</li></ul>")
    check_and_match_snapshot(
        page.locator("body"),
        """
      - list:
        - listitem: one
        - listitem: two
    """,
    )


def test_should_snapshot_list_with_accessible_name(page: Page) -> None:
    page.set_content('<ul aria-label="my list"><li>one</li><li>two</li></ul>')
    check_and_match_snapshot(
        page.locator("body"),
        """
      - list "my list":
        - listitem: one
        - listitem: two
    """,
    )


def test_should_snapshot_complex(page: Page) -> None:
    page.set_content('<ul><li><a href="about:blank">link</a></li></ul>')
    check_and_match_snapshot(
        page.locator("body"),
        """
      - list:
        - listitem:
          - link "link":
            - /url: about:blank
    """,
    )


def test_should_snapshot_with_ref(page: Page) -> None:
    page.set_content('<ul><li><a href="about:blank">link</a></li></ul>')
    expected = """
      - list [ref=s1e3]:
        - listitem [ref=s1e4]:
          - link "link" [ref=s1e5]:
            - /url: about:blank
    """
    assert page.locator("body").aria_snapshot(ref=True) == _unshift(expected)


def test_should_snapshot_with_unexpected_children_equal(page: Page) -> None:
    page.set_content(
        """
      <ul>
        <li>One</li>
        <li>Two</li>
        <li>Three</li>
      </ul>
    """
    )
    expect(page.locator("body")).to_match_aria_snapshot(
        """
      - list:
        - listitem: One
        - listitem: Three
    """,
    )
    with pytest.raises(AssertionError):
        expect(page.locator("body")).to_match_aria_snapshot(
            """
        - list:
          - /children: equal
          - listitem: One
          - listitem: Three
      """,
            timeout=1000,
        )


def test_should_snapshot_with_unexpected_children_deep_equal(page: Page) -> None:
    page.set_content(
        """
      <ul>
        <li>
          <ul>
            <li>1.1</li>
            <li>1.2</li>
          </ul>
        </li>
      </ul>
    """
    )
    expect(page.locator("body")).to_match_aria_snapshot(
        """
      - list:
        - listitem:
          - list:
            - listitem: 1.1
    """,
    )
    expect(page.locator("body")).to_match_aria_snapshot(
        """
        - list:
          - /children: equal
          - listitem:
            - list:
              - listitem: 1.1
      """,
    )
    with pytest.raises(AssertionError):
        expect(page.locator("body")).to_match_aria_snapshot(
            """
          - list:
            - /children: deep-equal
            - listitem:
              - list:
                - listitem: 1.1
        """,
            timeout=1000,
        )


def test_should_snapshot_with_restored_contain_mode_inside_deep_equal(
    page: Page,
) -> None:
    page.set_content(
        """
      <ul>
        <li>
          <ul>
            <li>1.1</li>
            <li>1.2</li>
          </ul>
        </li>
      </ul>
    """
    )
    with pytest.raises(AssertionError):
        expect(page.locator("body")).to_match_aria_snapshot(
            """
        - list:
          - /children: deep-equal
          - listitem:
            - list:
              - listitem: 1.1
      """,
            timeout=1000,
        )
    expect(page.locator("body")).to_match_aria_snapshot(
        """
        - list:
          - /children: deep-equal
          - listitem:
            - list:
              - /children: contain
              - listitem: 1.1
      """,
    )
