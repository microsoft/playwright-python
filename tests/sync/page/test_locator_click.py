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

"""Port of tests/page/locator-click.spec.ts."""

from playwright.sync_api import Page
from tests.server import Server


def test_LO_052_should_work_smoke(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    button = page.locator("button")
    button.click()
    assert page.evaluate("() => window['result']") == "Clicked"


def test_LO_053_should_work_with_node_removed(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.evaluate("() => delete window['Node']")
    button = page.locator("button")
    button.click()
    assert page.evaluate("() => window['result']") == "Clicked"


def test_LO_054_should_double_click_the_button(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/button.html")
    page.evaluate(
        """() => {
        window['double'] = false;
        const button = document.querySelector('button');
        button.addEventListener('dblclick', event => {
          window['double'] = true;
        });
      }"""
    )
    button = page.locator("button")
    button.dblclick()
    assert page.evaluate("double") is True
    assert page.evaluate("result") == "Clicked"


def test_LO_055_should_click_if_the_target_element_is_removed_in_pointerup_event(
    page: Page,
) -> None:
    page.set_content("<button id=clickme>Clickable</button>")
    page.eval_on_selector(
        "#clickme",
        "element => element.addEventListener('pointerup', () => element.remove(), false)",
    )
    page.locator("#clickme").click()


def test_LO_056_should_click_if_the_target_element_is_removed_in_pointerdown_event(
    page: Page,
) -> None:
    page.set_content("<button id=clickme>Clickable</button>")
    page.eval_on_selector(
        "#clickme",
        "element => element.addEventListener('pointerdown', () => element.remove(), false)",
    )
    page.locator("#clickme").click()
