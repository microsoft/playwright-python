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

"""Port of tests/page/elementhandle-wait-for-element-state.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server

from ..utils import Utils


def give_it_a_chance_to_resolve(page: Page, utils: Utils) -> None:
    utils.rafraf(page, 5)


def test_EH_112_should_wait_for_visible(
    page: Page, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div style='display:none'>content</div>")
    div = page.query_selector("div")
    assert div
    done = False

    def wait() -> None:
        nonlocal done
        div.wait_for_element_state("visible")
        done = True

    def make_visible() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        div.evaluate("div => div.style.display = 'block'")

    sync_gather(wait, make_visible)


def test_EH_113_should_wait_for_already_visible(page: Page) -> None:
    page.set_content("<div>content</div>")
    div = page.query_selector("div")
    assert div
    div.wait_for_element_state("visible")


def test_EH_114_should_timeout_waiting_for_visible(page: Page) -> None:
    page.set_content("<div style='display:none'>content</div>")
    div = page.query_selector("div")
    assert div
    with pytest.raises(Error) as exc_info:
        div.wait_for_element_state("visible", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message


def test_EH_115_should_throw_waiting_for_visible_when_detached(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div style='display:none'>content</div>")
    div = page.query_selector("div")
    assert div

    def wait() -> None:
        div.wait_for_element_state("visible")

    def remove() -> None:
        div.evaluate("div => div.remove()")

    with pytest.raises(Error) as exc_info:
        sync_gather(wait, remove)
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_EH_116_should_wait_for_hidden(
    page: Page, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div>content</div>")
    div = page.query_selector("div")
    assert div
    done = False

    def wait() -> None:
        nonlocal done
        div.wait_for_element_state("hidden")
        done = True

    def hide() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        div.evaluate("div => div.style.display = 'none'")

    sync_gather(wait, hide)


def test_EH_117_should_wait_for_already_hidden(page: Page) -> None:
    page.set_content("<div></div>")
    div = page.query_selector("div")
    assert div
    div.wait_for_element_state("hidden")


def test_EH_118_should_wait_for_hidden_when_detached(
    page: Page, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<div>content</div>")
    div = page.query_selector("div")
    assert div
    done = False

    def wait() -> None:
        nonlocal done
        div.wait_for_element_state("hidden")
        done = True

    def remove() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        div.evaluate("div => div.remove()")

    sync_gather(wait, remove)


def test_EH_119_should_throw_waiting_for_enabled_when_detached(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button disabled>Target</button>")
    button = page.query_selector("button")
    assert button

    def wait() -> None:
        button.wait_for_element_state("enabled")

    def remove() -> None:
        button.evaluate("button => button.remove()")

    with pytest.raises(Error) as exc_info:
        sync_gather(wait, remove)
    assert "Element is not attached to the DOM" in exc_info.value.message


def test_EH_120_should_wait_for_aria_enabled_button(
    page: Page, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<button aria-disabled=true><span>Target</span></button>")
    span = page.query_selector("text=Target")
    assert span
    done = False

    def wait() -> None:
        nonlocal done
        span.wait_for_element_state("enabled")
        done = True

    def enable() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        span.evaluate(
            "span => span.parentElement.setAttribute('aria-disabled', 'false')"
        )

    sync_gather(wait, enable)


def test_EH_121_should_wait_for_button_with_an_aria_disabled_parent(
    page: Page, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content(
        '<div role="group" aria-disabled=true><button><span>Target</span></button></div>'
    )
    span = page.query_selector("text=Target")
    assert span
    done = False

    def wait() -> None:
        nonlocal done
        span.wait_for_element_state("enabled")
        done = True

    def enable() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        span.evaluate(
            "span => span.parentElement.parentElement.setAttribute('aria-disabled', 'false')"
        )

    sync_gather(wait, enable)


def test_EH_122_should_wait_for_stable_position(
    page: Page, server: Server, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.query_selector("button")
    assert button
    page.eval_on_selector(
        "button",
        """button => {
    button.style.transition = 'margin 10000ms linear 0s';
    button.style.marginLeft = '20000px';
  }""",
    )
    # rafraf for Firefox to kick in the animation.
    utils.rafraf(page)
    done = False

    def wait() -> None:
        nonlocal done
        button.wait_for_element_state("stable")
        done = True

    def stop() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        button.evaluate("button => button.style.transition = ''")

    sync_gather(wait, stop)


def test_EH_123_should_wait_for_editable_input(
    page: Page, utils: Utils, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<input readonly>")
    input = page.query_selector("input")
    assert input
    done = False

    def wait() -> None:
        nonlocal done
        input.wait_for_element_state("editable")
        done = True

    def make_editable() -> None:
        give_it_a_chance_to_resolve(page, utils)
        assert done is False
        input.evaluate("input => input.readOnly = false")

    sync_gather(wait, make_editable)
