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

import pytest

from playwright.sync_api import Error, Page, expect
from tests.server import Server
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


def test_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    before_count = 0
    after_count = 0

    def handler() -> None:
        nonlocal before_count
        nonlocal after_count
        before_count += 1
        page.locator("#close").click()
        after_count += 1

    page.add_locator_handler(
        page.locator("text=This interstitial covers the button"), handler
    )

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
        page.locator("#aside").hover()
        before_count = 0
        after_count = 0
        page.evaluate(
            "(args) => { window.clicked = 0; window.setupAnnoyingInterstitial(...args); }",
            args,
        )
        assert before_count == 0
        assert after_count == 0
        page.locator("#target").click()
        assert before_count == args[1]
        assert after_count == args[1]
        assert page.evaluate("window.clicked") == 1
        expect(page.locator("#interstitial")).not_to_be_visible()


def test_should_work_with_a_custom_check(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    def handler() -> None:
        if page.get_by_text("This interstitial covers the button").is_visible():
            page.locator("#close").click()

    page.add_locator_handler(page.locator("body"), handler)

    for args in [
        ["mouseover", 2],
        ["none", 1],
        ["remove", 1],
        ["hide", 1],
    ]:
        page.locator("#aside").hover()
        page.evaluate(
            "(args) => { window.clicked = 0; window.setupAnnoyingInterstitial(...args); }",
            args,
        )
        page.locator("#target").click()
        assert page.evaluate("window.clicked") == 1
        expect(page.locator("#interstitial")).not_to_be_visible()


def test_should_work_with_locator_hover(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"),
        lambda: page.locator("#close").click(),
    )

    page.locator("#aside").hover()
    page.evaluate(
        '() => { window.setupAnnoyingInterstitial("pointerover", 1, "capture"); }'
    )
    page.locator("#target").hover()
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert (
        page.eval_on_selector(
            "#target", "e => window.getComputedStyle(e).backgroundColor"
        )
        == "rgb(255, 255, 0)"
    )


def test_should_not_work_with_force_true(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"),
        lambda: page.locator("#close").click(),
    )

    page.locator("#aside").hover()
    page.evaluate('() => { window.setupAnnoyingInterstitial("none", 1); }')
    page.locator("#target").click(force=True, timeout=2000)
    assert page.locator("#interstitial").is_visible()
    assert page.evaluate("window.clicked") is None


def test_should_throw_when_page_closes(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), lambda: page.close()
    )

    page.locator("#aside").hover()
    page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("mouseover", 1); }'
    )
    with pytest.raises(Error) as exc:
        page.locator("#target").click()
    assert TARGET_CLOSED_ERROR_MESSAGE in exc.value.message


def test_should_throw_when_handler_times_out(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/handle-locator.html")

    called = 0

    def handler() -> None:
        nonlocal called
        called += 1
        # Deliberately timeout.
        try:
            page.wait_for_timeout(9999999)
        except Error:
            pass

    page.add_locator_handler(
        page.get_by_text("This interstitial covers the button"), handler
    )

    page.locator("#aside").hover()
    page.evaluate(
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("mouseover", 1); }'
    )
    with pytest.raises(Error) as exc:
        page.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc.value.message

    with pytest.raises(Error) as exc:
        page.locator("#target").click(timeout=3000)
    assert "Timeout 3000ms exceeded" in exc.value.message

    # Should not enter the same handler while it is still running.
    assert called == 1


def test_should_work_with_to_be_visible(page: Page, server: Server) -> None:
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
        '() => { window.clicked = 0; window.setupAnnoyingInterstitial("remove", 1); }'
    )
    expect(page.locator("#target")).to_be_visible()
    expect(page.locator("#interstitial")).not_to_be_visible()
    assert called == 1
