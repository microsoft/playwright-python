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

"""Port of tests/page/page-add-locator-handler.spec.ts."""

import asyncio
from typing import List, Union

import pytest

from playwright._impl._greenlets import wait_for_future
from playwright.sync_api import Error, Locator, Page, expect
from tests.server import Server

SETUP_INTERSTITIAL = """args => {
    window.clicked = 0;
    window.setupAnnoyingInterstitial(...args);
}"""


def test_LH_001_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    before_count = 0
    after_count = 0
    original_locator = page.get_by_text("This interstitial covers the button")

    def handler(locator_argument: Locator) -> None:
        nonlocal before_count, after_count
        assert locator_argument is original_locator
        before_count += 1
        page.locator("#close").click()
        after_count += 1

    page.add_locator_handler(original_locator, handler)

    all_args: List[List[Union[str, int]]] = [
        ["mouseover", 1],
        ["mouseover", 1, "capture"],
        ["mouseover", 2],
        ["mouseover", 2, "capture"],
        ["pointerover", 1],
        ["pointerover", 1, "capture"],
        ["none", 1],
        ["remove", 1],
        ["hide", 1],
    ]
    for args in all_args:
        page.locator("#aside").hover()
        before_count = 0
        after_count = 0
        page.evaluate(SETUP_INTERSTITIAL, args)
        assert before_count == 0
        assert after_count == 0
        page.locator("#target").click()
        assert before_count == args[1]
        assert after_count == args[1]
        assert page.evaluate("window.clicked") == 1
        expect(page.locator("#interstitial")).not_to_be_visible()


def test_LH_002_should_work_with_a_custom_check(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    def handler() -> None:
        if page.get_by_text("This interstitial covers the button").is_visible():
            page.locator("#close").click()

    page.add_locator_handler(page.locator("body"), handler, no_wait_after=True)

    all_args: List[List[Union[str, int]]] = [
        ["mouseover", 2],
        ["none", 1],
        ["remove", 1],
        ["hide", 1],
    ]
    for args in all_args:
        page.locator("#aside").hover()
        page.evaluate(SETUP_INTERSTITIAL, args)
        page.locator("#target").click()
        assert page.evaluate("window.clicked") == 1
        expect(page.locator("#interstitial")).not_to_be_visible()


def test_LH_003_should_work_with_locator_hover(
    page: Page, server: Server, headless: bool
) -> None:
    if not headless:
        pytest.skip("Stray hovers in headed mode")

    page.goto(server.PREFIX + "/input/handle-locator.html")

    def handler() -> None:
        page.locator("#close").click()

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.setupAnnoyingInterstitial('pointerover', 1, 'capture');
        }"""
    )
    page.locator("#target").hover()
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert (
        page.eval_on_selector(
            "#target", "e => window.getComputedStyle(e).backgroundColor"
        )
        == "rgb(255, 255, 0)"
    )


def test_LH_004_should_not_work_with_force_true(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    def handler() -> None:
        page.locator("#close").click()

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.setupAnnoyingInterstitial('none', 1);
        }"""
    )
    page.locator("#target").click(force=True, timeout=2000)
    assert page.locator("#interstitial").is_visible() is True
    assert page.evaluate("window.clicked") is None


def test_LH_005_should_throw_when_handler_times_out(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0
    # Python: futures stand for the two ManualPromises.
    release_handler: "asyncio.Future[None]" = page._loop.create_future()
    handler_finished: "asyncio.Future[Union[Error, None]]" = page._loop.create_future()

    def handler() -> None:
        nonlocal called
        called += 1
        # Deliberately timeout.
        wait_for_future(page._loop, page._dispatcher_fiber, release_handler)
        try:
            page.locator("#close").click(timeout=3000)
            handler_finished.set_result(None)
        except Error as error:
            handler_finished.set_result(error)

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('mouseover', 1);
        }"""
    )
    with pytest.raises(Error) as exc_info:
        page.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc_info.value.message

    with pytest.raises(Error) as exc_info2:
        page.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc_info2.value.message

    # Should not enter the same handler while it is still running.
    assert called == 1
    release_handler.set_result(None)
    wait_for_future(page._loop, page._dispatcher_fiber, handler_finished)
    assert handler_finished.result() is None


def test_LH_006_should_work_with_to_be_visible(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler() -> None:
        nonlocal called
        called += 1
        page.locator("#close").click()

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('remove', 1);
        }"""
    )
    expect(page.locator("#target")).to_be_visible()
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 1


def test_LH_007_should_work_with_locator_wait_for(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler() -> None:
        nonlocal called
        called += 1
        page.locator("#close").click()

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('remove', 1);
        }"""
    )
    page.locator("#target").wait_for()
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 1


def test_LH_009_should_work_when_owner_frame_detaches(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)

    page.evaluate(
        """() => {
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
        }"""
    )

    def handler() -> None:
        page.locator("#close").click()

    page.add_locator_handler(page.frame_locator("iframe").locator("body"), handler)

    page.locator("#target").click()
    assert page.query_selector("iframe") is None
    assert page.evaluate("window._clicked") is True


def test_LH_010_should_work_with_times_option(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler() -> None:
        nonlocal called
        called += 1

    page.add_locator_handler(page.locator("body"), handler, no_wait_after=True, times=2)

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('mouseover', 4);
        }"""
    )
    with pytest.raises(Error) as exc_info:
        page.locator("#target").click(timeout=3000)
    assert called == 2
    assert page.evaluate("window.clicked") == 0
    expect(page.locator("#interstitial")).to_be_visible()
    assert "Timeout 3000ms exceeded" in exc_info.value.message
    assert (
        '<div>This interstitial covers the button</div> from <div class="visible" id="interstitial">…</div> subtree intercepts pointer events'
        in exc_info.value.message
    )


def test_LH_011_should_wait_for_hidden_by_default(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler(button: Locator) -> None:
        nonlocal called
        called += 1
        button.click()

    page.add_locator_handler(page.get_by_role("button", name="close"), handler)

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('timeout', 1);
        }"""
    )
    page.locator("#target").click()
    assert page.evaluate("window.clicked") == 1
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 1


def test_LH_012_should_wait_for_hidden_by_default_2(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler(button: Locator) -> None:
        nonlocal called
        called += 1

    page.add_locator_handler(page.get_by_role("button", name="close"), handler)

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('hide', 1);
        }"""
    )
    with pytest.raises(Error) as exc_info:
        page.locator("#target").click(timeout=3000)
    assert page.evaluate("window.clicked") == 0
    assert page.locator("#interstitial").is_visible() is True
    assert called == 1
    assert (
        'locator handler has finished, waiting for get_by_role("button", name="close") to be hidden'
        in exc_info.value.message
    )


def test_LH_013_should_work_with_no_wait_after(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler(button: Locator) -> None:
        nonlocal called
        called += 1
        if called == 1:
            button.click()
        else:
            page.locator("#interstitial").wait_for(state="hidden")

    page.add_locator_handler(
        page.get_by_role("button", name="close"), handler, no_wait_after=True
    )

    page.locator("#aside").hover()
    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('timeout', 1);
        }"""
    )
    page.locator("#target").click()
    assert page.evaluate("window.clicked") == 1
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 2


def test_LH_014_should_remove_locator_handler(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler(locator: Locator) -> None:
        nonlocal called
        called += 1
        locator.click()

    page.add_locator_handler(page.get_by_role("button", name="close"), handler)

    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('hide', 1);
        }"""
    )
    page.locator("#target").click()
    assert called == 1
    assert page.evaluate("window.clicked") == 1
    expect(page.locator("#interstitial")).not_to_be_visible()

    page.evaluate(
        """() => {
            window.clicked = 0;
            window.setupAnnoyingInterstitial('hide', 1);
        }"""
    )
    page.remove_locator_handler(page.get_by_role("button", name="close"))

    with pytest.raises(Error) as exc_info:
        page.locator("#target").click(timeout=3000)
    assert called == 1
    assert page.evaluate("window.clicked") == 0
    expect(page.locator("#interstitial")).to_be_visible()
    assert "Timeout 3000ms exceeded" in exc_info.value.message
