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

"""Python only: tests of behaviors that no upstream test covers."""

import sys
from typing import TYPE_CHECKING

import pytest

from playwright.async_api import Error, Locator, Page, expect
from tests.server import Server

if TYPE_CHECKING:
    # Real type for static checkers, undefined at runtime (PEP 649 case).
    from playwright.async_api import Locator as TypeCheckingOnlyLocator


async def test_should_work_with_keyword_only_handler(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    called = False

    async def handler(*, timeout: object = None) -> None:
        nonlocal called
        assert timeout is None
        called = True
        await page.locator("#close").click()

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    await page.locator("#aside").hover()
    await page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("mouseover", 1); }'
    )
    await page.locator("#target").click()
    assert called
    assert await page.evaluate("window.clicked") == 1
    await expect(page.locator("#interstitial")).not_to_be_visible()


async def test_should_work_with_varargs_handler(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    called = False
    original_locator = page.get_by_text("This interstitial covers the button")

    async def handler(*locators: Locator) -> None:
        nonlocal called
        assert locators == (original_locator,)
        called = True
        await page.locator("#close").click()

    await page.add_locator_handler(original_locator, handler)

    await page.locator("#aside").hover()
    await page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("mouseover", 1); }'
    )
    await page.locator("#target").click()
    assert called
    assert await page.evaluate("window.clicked") == 1
    await expect(page.locator("#interstitial")).not_to_be_visible()


async def test_should_work_with_times_option(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")
    called = 0

    def _handler() -> None:
        nonlocal called
        called += 1

    await page.add_locator_handler(
        page.locator("body"), _handler, no_wait_after=True, times=2
    )
    await page.locator("#aside").hover()
    await page.evaluate(
        """
    () => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('mouseover', 4);
    }
    """
    )
    with pytest.raises(Error) as exc_info:
        await page.locator("#target").click(timeout=3000)
    assert called == 2
    assert await page.evaluate("window.clicked") == 0
    await expect(page.locator("#interstitial")).to_be_visible()
    assert "Timeout 3000ms exceeded" in exc_info.value.message
    assert (
        '<div>This interstitial covers the button</div> from <div class="visible" id="interstitial">…</div> subtree intercepts pointer events'
        in exc_info.value.message
    )


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="PEP 649 lazy annotations require Python 3.14+",
)
async def test_should_support_annotations_with_runtime_unresolved_types(
    page: Page, server: Server
) -> None:
    # Since PEP 649, annotations are lazily evaluated; the signature
    # inspection done for locator handlers must not resolve them eagerly.
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    original_locator = page.get_by_text("This interstitial covers the button")
    called = 0

    async def handler(locator: TypeCheckingOnlyLocator) -> None:
        nonlocal called
        called += 1
        assert locator == original_locator
        await page.locator("#close").click()

    await page.add_locator_handler(original_locator, handler)
    await page.locator("#aside").hover()
    await page.evaluate('() => window.setupAnnoyingInterstitial("mouseover", 1)')
    await page.locator("#target").click()
    assert called == 1
    assert await page.evaluate("window.clicked") == 1
