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

import asyncio

import pytest

from playwright.async_api import Error, Locator, Page, expect
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


async def test_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    before_count = 0
    after_count = 0

    original_locator = page.get_by_text("This interstitial covers the button")

    async def handler(locator: Locator) -> None:
        nonlocal original_locator
        assert locator == original_locator
        nonlocal before_count
        nonlocal after_count
        before_count += 1
        await page.locator("#close").click()
        after_count += 1

    await page.add_locator_handler(original_locator, handler)

    for args in [
        ["mouseover", 1],
        ["mouseover", 1, "capture"],
        ["mouseover", 2],
        ["mouseover", 2, "capture"],
        ["pointerover", 1],
        ["pointerover", 1, "capture"],
        ["none", 1],
        ["remove", 1],
        ["hide", 1],
    ]:
        await page.locator("#aside").hover()
        before_count = 0
        after_count = 0
        await page.evaluate(
            "(args) => { window.clicked = 0; window.setupAnnoyingInterstitial(...args); }",
            args,
        )
        assert before_count == 0
        assert after_count == 0
        await page.locator("#target").click()
        assert before_count == args[1]
        assert after_count == args[1]
        assert await page.evaluate("window.clicked") == 1
        await expect(page.locator("#interstitial")).not_to_be_visible()


async def test_should_work_with_a_custom_check(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    async def handler() -> None:
        if await page.get_by_text("This interstitial covers the button").is_visible():
            await page.locator("#close").click()

    await page.add_locator_handler(page.locator("body"), handler, no_wait_after=True)

    for args in [
        ["mouseover", 2],
        ["none", 1],
        ["remove", 1],
        ["hide", 1],
    ]:
        await page.locator("#aside").hover()
        await page.evaluate(
            "(args) => { window.clicked = 0; window.setupAnnoyingInterstitial(...args); }",
            args,
        )
        await page.locator("#target").click()
        assert await page.evaluate("window.clicked") == 1
        await expect(page.locator("#interstitial")).not_to_be_visible()


async def test_should_work_with_locator_hover(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"),
        lambda: page.locator("#close").click(),
    )

    await page.locator("#aside").hover()
    await page.evaluate(
        '() => { window.setupAnnoyingInterstitial("pointerover", 1, "capture"); }'
    )
    await page.locator("#target").hover()
    await expect(page.locator("#interstitial")).not_to_be_visible()
    assert (
        await page.eval_on_selector(
            "#target", "e => window.getComputedStyle(e).backgroundColor"
        )
        == "rgb(255, 255, 0)"
    )


async def test_should_not_work_with_force_true(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"),
        lambda: page.locator("#close").click(),
    )

    await page.locator("#aside").hover()
    await page.evaluate('() => { window.setupAnnoyingInterstitial("none", 1); }')
    await page.locator("#target").click(force=True, timeout=2000)
    assert await page.locator("#interstitial").is_visible()
    assert await page.evaluate("window.clicked") is None


async def test_should_throw_when_page_closes(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), lambda: page.close()
    )

    await page.locator("#aside").hover()
    await page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("mouseover", 1); }'
    )
    with pytest.raises(Error) as exc:
        await page.locator("#target").click()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc.value.message


async def test_should_throw_when_handler_times_out(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0
    stall_future: asyncio.Future[None] = asyncio.Future()

    async def handler() -> None:
        nonlocal called
        called += 1
        # Deliberately timeout.
        await stall_future

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    await page.locator("#aside").hover()
    await page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("mouseover", 1); }'
    )
    with pytest.raises(Error) as exc:
        await page.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc.value.message

    with pytest.raises(Error) as exc:
        await page.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc.value.message

    # Should not enter the same handler while it is still running.
    assert called == 1
    stall_future.cancel()


async def test_should_work_with_to_be_visible(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    async def handler() -> None:
        nonlocal called
        called += 1
        await page.locator("#close").click()

    await page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    await page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("remove", 1); }'
    )
    await expect(page.locator("#target")).to_be_visible()
    await expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 1


async def test_should_work_when_owner_frame_detaches(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """
    () => {
        const iframe = document.createElement('iframe');
        iframe.src = 'data:text/html,<body>hello from iframe</body>';
        document.body.append(iframe);

        const target = document.createElement('button');
        target.textContent = 'Click me';
        target.id = 'target';
        target.addEventListener('click', () => window._clicked = true);
        document.body.appendChild(target);

        const closeButton = document.createElement('button');
        closeButton.textContent = 'close';
        closeButton.id = 'close';
        closeButton.addEventListener('click', () => iframe.remove());
        document.body.appendChild(closeButton);
    }
    """
    )
    await page.add_locator_handler(
        page.frame_locator("iframe").locator("body"),
        lambda: page.locator("#close").click(),
    )
    await page.locator("#target").click()
    assert await page.query_selector("iframe") is None
    assert await page.evaluate("window._clicked") is True


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


async def test_should_wait_for_hidden_by_default(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")
    called = 0

    async def _handler(button: Locator) -> None:
        nonlocal called
        called += 1
        await button.click()

    await page.add_locator_handler(page.get_by_role("button", name="close"), _handler)
    await page.locator("#aside").hover()
    await page.evaluate(
        """
    () => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('timeout', 1);
    }
    """
    )
    await page.locator("#target").click()
    assert await page.evaluate("window.clicked") == 1
    await expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 1


async def test_should_wait_for_hidden_by_default_2(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")
    called = 0

    def _handler() -> None:
        nonlocal called
        called += 1

    await page.add_locator_handler(page.get_by_role("button", name="close"), _handler)
    await page.locator("#aside").hover()
    await page.evaluate(
        """
    () => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('hide', 1);
    }
    """
    )
    with pytest.raises(Error) as exc_info:
        await page.locator("#target").click(timeout=3000)
    assert await page.evaluate("window.clicked") == 0
    await expect(page.locator("#interstitial")).to_be_visible()
    assert called == 1
    assert (
        'locator handler has finished, waiting for get_by_role("button", name="close") to be hidden'
        in exc_info.value.message
    )


async def test_should_work_with_noWaitAfter(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")
    called = 0

    async def _handler(button: Locator) -> None:
        nonlocal called
        called += 1
        if called == 1:
            await button.click()
        else:
            await page.locator("#interstitial").wait_for(state="hidden")

    await page.add_locator_handler(
        page.get_by_role("button", name="close"), _handler, no_wait_after=True
    )
    await page.locator("#aside").hover()
    await page.evaluate(
        """
    () => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('timeout', 1);
    }
    """
    )
    await page.locator("#target").click()
    assert await page.evaluate("window.clicked") == 1
    await expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 2


async def test_should_removeLocatorHandler(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/handle-locator.html")
    called = 0

    async def _handler(locator: Locator) -> None:
        nonlocal called
        called += 1
        await locator.click()

    await page.add_locator_handler(page.get_by_role("button", name="close"), _handler)
    await page.evaluate(
        """
    () => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('hide', 1);
    }
    """
    )
    await page.locator("#target").click()
    assert called == 1
    assert await page.evaluate("window.clicked") == 1
    await expect(page.locator("#interstitial")).not_to_be_visible()
    await page.evaluate(
        """
    () => {
        window.clicked = 0;
        window.setupAnnoyingInterstitial('hide', 1);
    }
    """
    )
    await page.remove_locator_handler(page.get_by_role("button", name="close"))
    with pytest.raises(Error) as error:
        await page.locator("#target").click(timeout=3000)
    assert called == 1
    assert await page.evaluate("window.clicked") == 0
    await expect(page.locator("#interstitial")).to_be_visible()
    assert "Timeout 3000ms exceeded" in error.value.message
