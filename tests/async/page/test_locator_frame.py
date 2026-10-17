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

import asyncio
from urllib.parse import urlparse

import pytest

from playwright.async_api import Error, Page, Route, expect
from tests.server import Server


async def fulfill_html(route: Route, body: str) -> None:
    try:
        await route.fulfill(body=body, content_type="text/html")
    except Error:
        pass


async def route_iframe(page: Page) -> None:
    await page.route(
        "**/empty.html",
        lambda route: fulfill_html(
            route, '<iframe src="iframe.html" name="frame1"></iframe>'
        ),
    )
    await page.route(
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
    await page.route(
        "**/iframe-2.html",
        lambda route: fulfill_html(
            route, "<html><button>Hello nested iframe</button></html>"
        ),
    )


async def route_ambiguous(page: Page) -> None:
    await page.route(
        "**/empty.html",
        lambda route: fulfill_html(
            route,
            """<iframe src="iframe-1.html"></iframe>
             <iframe src="iframe-2.html"></iframe>
             <iframe src="iframe-3.html"></iframe>""",
        ),
    )

    async def handle_iframe(route: Route) -> None:
        path = urlparse(route.request.url).path[1:]
        await fulfill_html(route, f"<html><button>Hello from {path}</button></html>")

    await page.route("**/iframe-*", handle_iframe)


async def test_LO_089_should_work_for_iframe_smoke(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator("button")
    await button.wait_for()
    assert await button.inner_text() == "Hello iframe"
    await expect(button).to_have_text("Hello iframe")
    await button.click()


async def test_LO_090_should_work_for_nested_iframe(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").frame_locator("iframe").locator("button")
    await button.wait_for()
    assert await button.inner_text() == "Hello nested iframe"
    await expect(button).to_have_text("Hello nested iframe")
    await button.click()


async def test_LO_091_should_work_for_and(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    locator = page.frame_locator("iframe").locator("button")
    await expect(locator).to_have_text("Hello iframe")
    spans = page.frame_locator("iframe").locator("span")
    await expect(spans).to_have_count(2)


async def test_LO_092_should_wait_for_frame(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        await page.locator("body").frame_locator("iframe").locator("span").click(
            timeout=1000
        )
    assert (
        """waiting for locator("body").locator("iframe").content_frame"""
        in exc_info.value.message
    )


async def test_LO_093_should_wait_for_frame_2(page: Page, server: Server) -> None:
    await route_iframe(page)

    async def navigate_later() -> None:
        await page.wait_for_timeout(300)
        try:
            await page.goto(server.EMPTY_PAGE)
        except Error:
            pass

    async def click() -> None:
        await page.frame_locator("iframe").locator("button").click()

    await asyncio.gather(navigate_later(), click())


async def test_LO_094_should_wait_for_frame_to_go(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)

    async def remove_later() -> None:
        await page.wait_for_timeout(300)
        try:
            await page.eval_on_selector("iframe", "e => e.remove()")
        except Error:
            pass

    async def check_hidden() -> None:
        await expect(page.frame_locator("iframe").locator("button")).to_be_hidden()

    await asyncio.gather(remove_later(), check_hidden())


async def test_LO_095_should_not_wait_for_frame(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await expect(page.frame_locator("iframe").locator("span")).to_be_hidden()


async def test_LO_096_should_not_wait_for_frame_2(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await expect(page.frame_locator("iframe").locator("span")).not_to_be_visible()


async def test_LO_097_should_not_wait_for_frame_3(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await expect(page.frame_locator("iframe").locator("span")).to_have_count(0)


async def test_LO_098_should_click_in_lazy_iframe(page: Page, server: Server) -> None:
    await page.route(
        "**/iframe.html",
        lambda route: fulfill_html(route, "<html><button>Hello iframe</button></html>"),
    )

    # empty pge
    await page.goto(server.EMPTY_PAGE)

    # add blank iframe
    async def add_iframe_later() -> None:
        await page.wait_for_timeout(500)
        await page.evaluate(
            """() => {
      const iframe = document.createElement('iframe');
      document.body.appendChild(iframe);
    }"""
        )
        # navigate iframe
        await page.wait_for_timeout(500)
        await page.evaluate(
            "() => document.querySelector('iframe').src = 'iframe.html'"
        )

    # Click in iframe
    button = page.frame_locator("iframe").locator("button")

    async def click() -> None:
        await button.click()

    async def inner_text() -> str:
        return await button.inner_text()

    async def check_text() -> None:
        await expect(button).to_have_text("Hello iframe")

    _, _, text, _ = await asyncio.gather(
        add_iframe_later(), click(), inner_text(), check_text()
    )
    assert text == "Hello iframe"


async def test_LO_099_wait_for_should_survive_frame_reattach(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator(
        'button:has-text("Hello nested iframe")'
    )

    async def wait_for() -> None:
        await button.wait_for()

    async def reattach() -> None:
        await page.locator("iframe").evaluate("e => e.remove()")
        await page.evaluate(
            """() => {
    const iframe = document.createElement('iframe');
    iframe.src = 'iframe-2.html';
    document.body.appendChild(iframe);
  }"""
        )

    await asyncio.gather(wait_for(), reattach())


async def test_LO_100_click_should_survive_frame_reattach(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator(
        'button:has-text("Hello nested iframe")'
    )

    async def click() -> None:
        await button.click()

    async def reattach() -> None:
        await page.locator("iframe").evaluate("e => e.remove()")
        await page.evaluate(
            """() => {
    const iframe = document.createElement('iframe');
    iframe.src = 'iframe-2.html';
    document.body.appendChild(iframe);
  }"""
        )

    await asyncio.gather(click(), reattach())


async def test_LO_101_click_should_survive_iframe_navigation(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator(
        'button:has-text("Hello nested iframe")'
    )

    async def click() -> None:
        await button.click()

    async def navigate_iframe() -> None:
        try:
            await page.locator("iframe").evaluate("e => e.src = 'iframe-2.html'")
        except Error:
            pass

    await asyncio.gather(click(), navigate_iframe())


async def test_LO_102_should_non_work_for_non_frame(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.set_content("<div></div>")
    button = page.frame_locator("div").locator("button")
    with pytest.raises(Error) as exc_info:
        await button.wait_for()
    assert "<div></div>" in exc_info.value.message
    assert "<iframe> was expected" in exc_info.value.message


async def test_LO_103_locator_frame_locator_should_work_for_iframe(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    await button.wait_for()
    assert await button.inner_text() == "Hello iframe"
    await expect(button).to_have_text("Hello iframe")
    await button.click()


async def test_LO_104_locator_frame_locator_should_throw_on_ambiguity(
    page: Page, server: Server
) -> None:
    await route_ambiguous(page)
    await page.goto(server.EMPTY_PAGE)
    button = page.locator("body").frame_locator("iframe").locator("button")
    with pytest.raises(Error) as exc_info:
        await button.wait_for()
    assert (
        """Error: strict mode violation: locator("body").locator("iframe") resolved to 3 elements"""
        in exc_info.value.message
    )


async def test_LO_105_locator_frame_locator_should_not_throw_on_first_last_nth(
    page: Page, server: Server
) -> None:
    await route_ambiguous(page)
    await page.goto(server.EMPTY_PAGE)
    button1 = page.locator("body").frame_locator("iframe").first.locator("button")
    await expect(button1).to_have_text("Hello from iframe-1.html")
    button2 = page.locator("body").frame_locator("iframe").nth(1).locator("button")
    await expect(button2).to_have_text("Hello from iframe-2.html")
    button3 = page.locator("body").frame_locator("iframe").last.locator("button")
    await expect(button3).to_have_text("Hello from iframe-3.html")


async def test_LO_106_get_by_coverage(page: Page, server: Server) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    button1 = page.frame_locator("iframe").get_by_role("button")
    button2 = page.frame_locator("iframe").get_by_text("Hello")
    button3 = page.frame_locator("iframe").get_by_test_id("buttonId")
    await expect(button1).to_have_text("Hello iframe")
    await expect(button2).to_have_text("Hello iframe")
    await expect(button3).to_have_text("Hello iframe")
    input1 = page.frame_locator("iframe").get_by_label("Name")
    await expect(input1).to_have_value("")
    input2 = page.frame_locator("iframe").get_by_placeholder("Placeholder")
    await expect(input2).to_have_value("")
    input3 = page.frame_locator("iframe").get_by_alt_text("Alternative")
    await expect(input3).to_have_value("")
    input4 = page.frame_locator("iframe").get_by_title("Title")
    await expect(input4).to_have_value("")


async def test_LO_107_wait_for_hidden_should_succeed_when_frame_is_not_in_dom(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/21879
    await page.goto("about:blank")
    button = page.frame_locator("iframe1").locator("button")
    assert await button.is_hidden()
    await button.wait_for(state="hidden", timeout=1000)
    await button.wait_for(state="detached", timeout=1000)
    with pytest.raises(Error) as exc_info:
        await button.wait_for(state="attached", timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message


async def test_LO_108_should_work_with_coep_coop_corp_isolated_iframe(
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
    await page.route(
        "**/empty.html",
        lambda route: route.fulfill(
            body=f'<iframe src="https://{server.CROSS_PROCESS_PREFIX}/btn.html" allow="cross-origin-isolated; fullscreen" sandbox="allow-same-origin allow-scripts allow-popups" ></iframe>',
            content_type="text/html",
            headers=headers,
        ),
    )
    await page.route(
        "**/btn.html",
        lambda route: route.fulfill(
            body='<button onclick="window.__clicked=true">Click target</button>',
            content_type="text/html",
            headers=headers,
        ),
    )
    await page.goto(server.EMPTY_PAGE)
    await page.frame_locator("iframe").get_by_role("button").click()
    assert await page.frames[1].evaluate("() => window['__clicked']") is True


async def test_LO_109_locator_content_frame_should_work(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    locator = page.locator("iframe")
    frame_locator = locator.content_frame
    button = frame_locator.locator("button")
    assert await button.inner_text() == "Hello iframe"
    await expect(button).to_have_text("Hello iframe")
    await button.click()


async def test_LO_110_frame_locator_owner_should_work(
    page: Page, server: Server
) -> None:
    await route_iframe(page)
    await page.goto(server.EMPTY_PAGE)
    frame_locator = page.frame_locator("iframe")
    locator = frame_locator.owner
    await expect(locator).to_be_visible()
    assert await locator.get_attribute("name") == "frame1"


async def test_LO_111_should_treat_elements_inside_hidden_iframe_as_hidden(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42719
    await page.set_content(
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
        await expect(hidden_button).to_be_attached()
        assert await hidden_button.is_visible() is False
        assert await hidden_button.is_hidden() is True
        await expect(hidden_button).to_be_hidden()
        await expect(hidden_button).not_to_be_visible()
        await hidden_button.wait_for(state="hidden")

    button = page.frame_locator("[name=visible-override]").locator("button")
    assert await button.is_visible() is True
    await expect(button).to_be_visible()
    await button.wait_for(state="visible")


async def test_LO_112_should_wait_for_hidden_iframe_to_become_visible(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42719
    await page.set_content(
        """<iframe name="frame" style="visibility: hidden" srcdoc="<button onclick='window.__clicked = true'>Button</button>"></iframe>"""
    )
    button = page.frame_locator("[name=frame]").locator("button")
    await expect(button).to_be_hidden()

    with pytest.raises(Error) as exc_info:
        await button.click(timeout=1000)
    assert "element is inside a hidden frame, retrying" in exc_info.value.message
    assert await button.evaluate("() => window.__clicked") is None

    async def click() -> None:
        await button.click()

    async def check_visible() -> None:
        await expect(button).to_be_visible()

    async def make_visible() -> None:
        await page.evaluate(
            "() => document.querySelector('iframe').style.visibility = 'visible'"
        )

    await asyncio.gather(click(), check_visible(), make_visible())
    assert await button.evaluate("() => window.__clicked") is True

    await page.evaluate(
        "() => document.querySelector('iframe').style.visibility = 'hidden'"
    )
    await expect(button).to_be_hidden()
    assert await button.is_visible() is False


async def test_LO_113_should_treat_elements_inside_hidden_cross_origin_iframe_as_hidden(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/42719
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<iframe style="visibility: hidden" src="{server.CROSS_PROCESS_PREFIX}/frames/frame.html"></iframe>'
    )
    div = page.frame_locator("iframe").locator("div")
    await expect(div).to_have_text("Hi, I'm frame")
    assert await div.is_visible() is False
    await expect(div).to_be_hidden()

    await page.evaluate(
        "() => document.querySelector('iframe').style.visibility = 'visible'"
    )
    await expect(div).to_be_visible()
    assert await div.is_visible() is True
