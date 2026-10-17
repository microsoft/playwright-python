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

"""Port of tests/page/locator-frame.spec.ts."""

from typing import Any, Callable, List
from urllib.parse import urlparse

import pytest

from playwright.sync_api import Error, Page, Route, expect
from tests.server import Server


def fulfill_html(route: Route, body: str) -> None:
    try:
        route.fulfill(body=body, content_type="text/html")
    except Error:
        pass


def route_iframe(page: Page) -> None:
    page.route(
        "**/empty.html",
        lambda route: fulfill_html(
            route, '<iframe src="iframe.html" name="frame1"></iframe>'
        ),
    )
    page.route(
        "**/iframe.html",
        lambda route: fulfill_html(
            route,
            """
        <html>
          <div>
            <button data-testid="buttonId">Hello iframe</button>
            <iframe src="iframe-2.html"></iframe>
          </div>
          <span>1</span>
          <span>2</span>
          <label for=target>Name</label><input id=target type=text placeholder=Placeholder title=Title alt=Alternative>
        </html>""",
        ),
    )
    page.route(
        "**/iframe-2.html",
        lambda route: fulfill_html(
            route, "<html><button>Hello nested iframe</button></html>"
        ),
    )


def route_ambiguous(page: Page) -> None:
    page.route(
        "**/empty.html",
        lambda route: fulfill_html(
            route,
            """<iframe src="iframe-1.html"></iframe>
             <iframe src="iframe-2.html"></iframe>
             <iframe src="iframe-3.html"></iframe>""",
        ),
    )

    def handle_iframe(route: Route) -> None:
        path = urlparse(route.request.url).path[1:]
        fulfill_html(route, f"<html><button>Hello from {path}</button></html>")

    page.route("**/iframe-*", handle_iframe)


def test_LO_089_should_work_for_iframe_smoke(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello iframe"
    expect(button).to_have_text("Hello iframe")
    button.click()


def test_LO_090_should_work_for_nested_iframe(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello nested iframe"
    expect(button).to_have_text("Hello nested iframe")
    button.click()


def test_LO_091_should_work_for_and(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    locator = page.frame_locator("iframe").locator("button")
    expect(locator).to_have_text("Hello iframe")
    spans = page.frame_locator("iframe").locator("span")
    expect(spans).to_have_count(2)


def test_LO_092_should_wait_for_frame(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        page.locator("body").frame_locator("iframe").locator("span").click(timeout=1000)
    assert (
        """waiting for locator("body").locator("iframe").content_frame"""
        in exc_info.value.message
    )


def test_LO_093_should_wait_for_frame_2(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)

    def navigate_later() -> None:
        page.wait_for_timeout(300)
        try:
            page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    def click() -> None:
        page.frame_locator("iframe").locator("button").click()

    sync_gather(navigate_later, click)


def test_LO_094_should_wait_for_frame_to_go(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)

    def remove_later() -> None:
        page.wait_for_timeout(300)
        try:
            page.eval_on_selector("iframe", "e => e.remove()")
        except Error:
            pass

    def check_hidden() -> None:
        expect(page.frame_locator("iframe").locator("button")).to_be_hidden()

    sync_gather(remove_later, check_hidden)


def test_LO_095_should_not_wait_for_frame(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator("iframe").locator("span")).to_be_hidden()


def test_LO_096_should_not_wait_for_frame_2(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator("iframe").locator("span")).not_to_be_visible()


def test_LO_097_should_not_wait_for_frame_3(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator("iframe").locator("span")).to_have_count(0)


def test_LO_098_should_click_in_lazy_iframe(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.route(
        "**/iframe.html",
        lambda route: fulfill_html(route, "<html><button>Hello iframe</button></html>"),
    )

    # empty pge
    page.goto(server.EMPTY_PAGE)

    # add blank iframe
    def add_iframe_later() -> None:
        page.wait_for_timeout(500)
        page.evaluate(
            """() => {
      const iframe = document.createElement('iframe');
      document.body.appendChild(iframe);
    }"""
        )
        # navigate iframe
        page.wait_for_timeout(500)
        page.evaluate("() => document.querySelector('iframe').src = 'iframe.html'")

    # Click in iframe
    button = page.frame_locator("iframe").locator("button")

    def click() -> None:
        button.click()

    def inner_text() -> str:
        return button.inner_text()

    def check_text() -> None:
        expect(button).to_have_text("Hello iframe")

    _, _, text, _ = sync_gather(add_iframe_later, click, inner_text, check_text)
    assert text == "Hello iframe"


def test_LO_099_wait_for_should_survive_frame_reattach(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator(
        'button:has-text("Hello nested iframe")'
    )

    def wait_for() -> None:
        button.wait_for()

    def reattach() -> None:
        page.locator("iframe").evaluate("e => e.remove()")
        page.evaluate(
            """() => {
    const iframe = document.createElement('iframe');
    iframe.src = 'iframe-2.html';
    document.body.appendChild(iframe);
  }"""
        )

    sync_gather(wait_for, reattach)


def test_LO_100_click_should_survive_frame_reattach(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator(
        'button:has-text("Hello nested iframe")'
    )

    def click() -> None:
        button.click()

    def reattach() -> None:
        page.locator("iframe").evaluate("e => e.remove()")
        page.evaluate(
            """() => {
    const iframe = document.createElement('iframe');
    iframe.src = 'iframe-2.html';
    document.body.appendChild(iframe);
  }"""
        )

    sync_gather(click, reattach)


def test_LO_101_click_should_survive_iframe_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator(
        'button:has-text("Hello nested iframe")'
    )

    def click() -> None:
        button.click()

    def navigate_iframe() -> None:
        try:
            page.locator("iframe").evaluate("e => e.src = 'iframe-2.html'")
        except Error:
            pass

    sync_gather(click, navigate_iframe)


def test_LO_102_should_non_work_for_non_frame(page: Page, server: Server) -> None:
    route_iframe(page)
    page.set_content("<div></div>")
    button = page.frame_locator("div").locator("button")
    with pytest.raises(Error) as exc_info:
        button.wait_for()
    assert "<div></div>" in exc_info.value.message
    assert "<iframe> was expected" in exc_info.value.message


def test_LO_103_locator_frame_locator_should_work_for_iframe(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello iframe"
    expect(button).to_have_text("Hello iframe")
    button.click()


def test_LO_104_locator_frame_locator_should_throw_on_ambiguity(
    page: Page, server: Server
) -> None:
    route_ambiguous(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    with pytest.raises(Error) as exc_info:
        button.wait_for()
    assert (
        """Error: strict mode violation: locator("body").locator("iframe") resolved to 3 elements"""
        in exc_info.value.message
    )


def test_LO_105_locator_frame_locator_should_not_throw_on_first_last_nth(
    page: Page, server: Server
) -> None:
    route_ambiguous(page)
    page.goto(server.EMPTY_PAGE)
    button1 = page.locator("body").frame_locator("iframe").first.locator("button")
    expect(button1).to_have_text("Hello from iframe-1.html")
    button2 = page.locator("body").frame_locator("iframe").nth(1).locator("button")
    expect(button2).to_have_text("Hello from iframe-2.html")
    button3 = page.locator("body").frame_locator("iframe").last.locator("button")
    expect(button3).to_have_text("Hello from iframe-3.html")


def test_LO_106_get_by_coverage(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button1 = page.frame_locator("iframe").get_by_role("button")
    button2 = page.frame_locator("iframe").get_by_text("Hello")
    button3 = page.frame_locator("iframe").get_by_test_id("buttonId")
    expect(button1).to_have_text("Hello iframe")
    expect(button2).to_have_text("Hello iframe")
    expect(button3).to_have_text("Hello iframe")
    input1 = page.frame_locator("iframe").get_by_label("Name")
    expect(input1).to_have_value("")
    input2 = page.frame_locator("iframe").get_by_placeholder("Placeholder")
    expect(input2).to_have_value("")
    input3 = page.frame_locator("iframe").get_by_alt_text("Alternative")
    expect(input3).to_have_value("")
    input4 = page.frame_locator("iframe").get_by_title("Title")
    expect(input4).to_have_value("")


def test_LO_107_wait_for_hidden_should_succeed_when_frame_is_not_in_dom(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/21879
    page.goto("about:blank")
    button = page.frame_locator("iframe1").locator("button")
    assert button.is_hidden()
    button.wait_for(state="hidden", timeout=1000)
    button.wait_for(state="detached", timeout=1000)
    with pytest.raises(Error) as exc_info:
        button.wait_for(state="attached", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message


def test_LO_108_should_work_with_coep_coop_corp_isolated_iframe(
    page: Page, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/28082
    if browser_name == "firefox":
        pytest.skip("fixme")
    headers = {
        "cross-origin-embedder-policy": "require-corp",
        "cross-origin-opener-policy": "same-origin",
        "cross-origin-resource-policy": "cross-origin",
    }
    page.route(
        "**/empty.html",
        lambda route: route.fulfill(
            body=f'<iframe src="https://{server.CROSS_PROCESS_PREFIX}/btn.html" allow="cross-origin-isolated; fullscreen" sandbox="allow-same-origin allow-scripts allow-popups" ></iframe>',
            content_type="text/html",
            headers=headers,
        ),
    )
    page.route(
        "**/btn.html",
        lambda route: route.fulfill(
            body='<button onclick="window.__clicked=true">Click target</button>',
            content_type="text/html",
            headers=headers,
        ),
    )
    page.goto(server.EMPTY_PAGE)
    page.frame_locator("iframe").get_by_role("button").click()
    assert page.frames[1].evaluate("() => window['__clicked']") is True


def test_LO_109_locator_content_frame_should_work(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    locator = page.locator("iframe")
    frame_locator = locator.content_frame
    button = frame_locator.locator("button")
    assert button.inner_text() == "Hello iframe"
    expect(button).to_have_text("Hello iframe")
    button.click()


def test_LO_110_frame_locator_owner_should_work(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    frame_locator = page.frame_locator("iframe")
    locator = frame_locator.owner
    expect(locator).to_be_visible()
    assert locator.get_attribute("name") == "frame1"


def test_LO_111_should_treat_elements_inside_hidden_iframe_as_hidden(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42719
    page.set_content(
        """
    <iframe name="hidden" style="visibility: hidden" srcdoc="<button>Hidden</button>"></iframe>
    <div style="visibility: hidden">
      <iframe name="hidden-parent" srcdoc="<button>Hidden parent</button>"></iframe>
      <iframe name="visible-override" style="visibility: visible" srcdoc="<button>Visible override</button>"></iframe>
    </div>
    <iframe name="outer" style="visibility: hidden" srcdoc="<iframe name='inner' srcdoc='<button>Nested</button>'></iframe>"></iframe>
  """
    )

    for hidden_button in [
        page.frame_locator("[name=hidden]").locator("button"),
        page.frame_locator("[name=hidden-parent]").locator("button"),
        page.frame_locator("[name=outer]")
        .frame_locator("[name=inner]")
        .locator("button"),
    ]:
        expect(hidden_button).to_be_attached()
        assert hidden_button.is_visible() is False
        assert hidden_button.is_hidden() is True
        expect(hidden_button).to_be_hidden()
        expect(hidden_button).not_to_be_visible()
        hidden_button.wait_for(state="hidden")

    button = page.frame_locator("[name=visible-override]").locator("button")
    assert button.is_visible() is True
    expect(button).to_be_visible()
    button.wait_for(state="visible")


def test_LO_112_should_wait_for_hidden_iframe_to_become_visible(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    # https://github.com/microsoft/playwright/issues/42719
    page.set_content(
        """<iframe name="frame" style="visibility: hidden" srcdoc="<button onclick='window.__clicked = true'>Button</button>"></iframe>"""
    )
    button = page.frame_locator("[name=frame]").locator("button")
    expect(button).to_be_hidden()

    with pytest.raises(Error) as exc_info:
        button.click(timeout=1000)
    assert "element is inside a hidden frame, retrying" in exc_info.value.message
    assert button.evaluate("() => window.__clicked") is None

    def click() -> None:
        button.click()

    def check_visible() -> None:
        expect(button).to_be_visible()

    def make_visible() -> None:
        page.evaluate(
            "() => document.querySelector('iframe').style.visibility = 'visible'"
        )

    sync_gather(click, check_visible, make_visible)
    assert button.evaluate("() => window.__clicked") is True

    page.evaluate("() => document.querySelector('iframe').style.visibility = 'hidden'")
    expect(button).to_be_hidden()
    assert button.is_visible() is False


def test_LO_113_should_treat_elements_inside_hidden_cross_origin_iframe_as_hidden(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/42719
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        f'<iframe style="visibility: hidden" src="{server.CROSS_PROCESS_PREFIX}/frames/frame.html"></iframe>'
    )
    div = page.frame_locator("iframe").locator("div")
    expect(div).to_have_text("Hi, I'm frame")
    assert div.is_visible() is False
    expect(div).to_be_hidden()

    page.evaluate("() => document.querySelector('iframe').style.visibility = 'visible'")
    expect(div).to_be_visible()
    assert div.is_visible() is True
