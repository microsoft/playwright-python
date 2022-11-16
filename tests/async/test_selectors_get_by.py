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

from playwright.async_api import Page


async def test_get_by_role_escaping(
    page: Page,
) -> None:
    await page.set_content(
        """
        <a href="https://playwright.dev">issues 123</a>
        <a href="https://playwright.dev">he llo 56</a>
        <button>Click me</button>
    """
    )
    assert await page.get_by_role("button").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        "<button>Click me</button>",
    ]
    assert await page.get_by_role("link").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">issues 123</a>""",
        """<a href="https://playwright.dev">he llo 56</a>""",
    ]

    assert await page.get_by_role("link", name="issues 123").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">issues 123</a>""",
    ]
    assert await page.get_by_role("link", name="sues").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">issues 123</a>""",
    ]
    assert await page.get_by_role("link", name="  he    \n  llo ").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">he llo 56</a>""",
    ]
    assert (
        await page.get_by_role("button", name="issues").evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )

    assert (
        await page.get_by_role("link", name="sues", exact=True).evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )
    assert await page.get_by_role(
        "link", name="   he \n llo 56 ", exact=True
    ).evaluate_all("els => els.map(e => e.outerHTML)") == [
        """<a href="https://playwright.dev">he llo 56</a>""",
    ]
