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

"""Port of tests/page/selectors-frame.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page, Route, expect
from tests.server import Server


def route_html(page: Page, url: str, body: str) -> None:
    def handler(route: Route) -> None:
        try:
            route.fulfill(body=body, content_type="text/html")
        except Error:
            pass

    page.route(url, handler)


def route_iframe(page: Page) -> None:
    route_html(page, "**/empty.html", '<iframe src="iframe.html"></iframe>')
    route_html(
        page,
        "**/iframe.html",
        """
        <html>
          <div>
            <button>Hello iframe</button>
            <iframe src="iframe-2.html"></iframe>
          </div>
          <span>1</span>
          <span>2</span>
        </html>""",
    )
    route_html(
        page,
        "**/iframe-2.html",
        '<html><button tag="iframe2">Hello nested iframe</button></html>',
    )


def test_SE_098_should_work_for_iframe_smoke(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("iframe >> internal:control=enter-frame >> button")
    button.wait_for()
    assert button.inner_text() == "Hello iframe"
    expect(button).to_have_text("Hello iframe")
    button.click()


def test_SE_099_should_work_for_iframe_handle(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    button = body.wait_for_selector("iframe >> internal:control=enter-frame >> button")
    assert button
    assert button.inner_text() == "Hello iframe"
    assert button.text_content() == "Hello iframe"
    button.click()


def test_SE_100_should_work_for_nested_iframe(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator(
        "iframe >> internal:control=enter-frame >> iframe >> internal:control=enter-frame >> button"
    )
    button.wait_for()
    assert button.inner_text() == "Hello nested iframe"
    expect(button).to_have_text("Hello nested iframe")
    button.click()


def test_SE_101_should_work_for_nested_iframe_handle(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    button = body.wait_for_selector(
        "iframe >> internal:control=enter-frame >> iframe >> internal:control=enter-frame >> button"
    )
    assert button
    assert button.inner_text() == "Hello nested iframe"
    assert button.text_content() == "Hello nested iframe"
    button.click()


def test_SE_102_should_work_for_and(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    element = page.query_selector("iframe >> internal:control=enter-frame >> button")
    assert element
    assert element.text_content() == "Hello iframe"
    elements = page.query_selector_all("iframe >> internal:control=enter-frame >> span")
    assert len(elements) == 2


def test_SE_103_should_not_wait_for_frame(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert not page.query_selector("iframe >> internal:control=enter-frame >> canvas")
    body = page.query_selector("body")
    assert body
    assert not body.query_selector("iframe >> internal:control=enter-frame >> canvas")


def test_SE_104_should_not_wait_for_frame(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    assert (
        len(page.query_selector_all("iframe >> internal:control=enter-frame >> canvas"))
        == 0
    )
    body = page.query_selector("body")
    assert body
    assert (
        len(body.query_selector_all("iframe >> internal:control=enter-frame >> canvas"))
        == 0
    )


def test_SE_105_eval_should_throw_for_missing_frame(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        page.eval_on_selector(
            "iframe >> internal:control=enter-frame >> canvas", "e => 1"
        )
    assert (
        "Page.eval_on_selector: Failed to find element matching selector"
        in exc_info.value.message
    )
    body = page.query_selector("body")
    assert body
    with pytest.raises(Error) as exc_info:
        body.eval_on_selector(
            "iframe >> internal:control=enter-frame >> canvas", "e => 1"
        )
    assert (
        "ElementHandle.eval_on_selector: Failed to find element matching selector"
        in exc_info.value.message
    )


def test_SE_106_eval_should_not_throw_for_missing_frame(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert (
        page.eval_on_selector_all(
            "iframe >> internal:control=enter-frame >> canvas", "e => e.length"
        )
        == 0
    )
    body = page.query_selector("body")
    assert body
    assert (
        body.eval_on_selector_all(
            "iframe >> internal:control=enter-frame >> canvas", "e => e.length"
        )
        == 0
    )


def test_SE_107_should_work_for_and_handle(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    element = body.query_selector("iframe >> internal:control=enter-frame >> button")
    assert element
    assert element.text_content() == "Hello iframe"
    elements = body.query_selector_all("iframe >> internal:control=enter-frame >> span")
    assert len(elements) == 2


def test_SE_108_should_work_for_eval(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    value = page.eval_on_selector(
        "iframe >> internal:control=enter-frame >> button", "b => b.nodeName"
    )
    assert value == "BUTTON"


def test_SE_109_should_work_for_eval_handle(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    value = body.eval_on_selector(
        "iframe >> internal:control=enter-frame >> button", "b => b.nodeName"
    )
    assert value == "BUTTON"


def test_SE_110_should_work_for_eval(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    value = page.eval_on_selector_all(
        "iframe >> internal:control=enter-frame >> span",
        "ss => ss.map(s => s.textContent)",
    )
    assert value == ["1", "2"]


def test_SE_111_should_work_for_eval_handle(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    value = body.eval_on_selector_all(
        "iframe >> internal:control=enter-frame >> span",
        "ss => ss.map(s => s.textContent)",
    )
    assert value == ["1", "2"]


def test_SE_112_should_not_allow_dangling_enter_frame(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("iframe >> internal:control=enter-frame")
    with pytest.raises(Error) as exc_info:
        button.click()
    assert "Selector cannot end with" in exc_info.value.message
    assert "iframe >> internal:control=enter-frame" in exc_info.value.message


def test_SE_113_should_not_allow_leading_enter_frame(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("internal:control=enter-frame >> button")
    assert "Selector cannot start with" in exc_info.value.message


def test_SE_114_should_not_allow_capturing_before_enter_frame(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator("*css=iframe >> internal:control=enter-frame >> div")
    with pytest.raises(Error) as exc_info:
        button.click()
    assert (
        "Can not capture the selector before diving into the frame"
        in exc_info.value.message
    )


def test_SE_115_should_capture_after_the_enter_frame(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    div = page.locator("iframe >> internal:control=enter-frame >> *css=div >> button")
    assert "<button>" in div.inner_html()


def test_SE_116_should_click_in_lazy_iframe(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_html(page, "**/iframe.html", "<html><button>Hello iframe</button></html>")

    # empty pge
    page.goto(server.EMPTY_PAGE)

    def add_iframe_later() -> None:
        # add blank iframe
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
    button = page.locator("iframe >> internal:control=enter-frame >> button")
    _, text, _, _ = sync_gather(
        lambda: button.click(),
        lambda: button.inner_text(),
        lambda: expect(button).to_have_text("Hello iframe"),
        add_iframe_later,
    )
    assert text == "Hello iframe"


def reattach_iframe(page: Page) -> None:
    page.locator("iframe").evaluate("e => e.remove()")
    page.evaluate(
        """() => {
          const iframe = document.createElement('iframe');
          iframe.src = 'iframe-2.html';
          document.body.appendChild(iframe);
        }"""
    )


def test_SE_117_wait_for_should_survive_frame_reattach(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator(
        'iframe >> internal:control=enter-frame >> button:has-text("Hello nested iframe")'
    )
    sync_gather(lambda: button.wait_for(), lambda: reattach_iframe(page))


def test_SE_118_wait_for_selector_should_survive_frame_reattach_handle(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    sync_gather(
        lambda: body.wait_for_selector(
            'iframe >> internal:control=enter-frame >> button:has-text("Hello nested iframe")'
        ),
        lambda: reattach_iframe(page),
    )


def test_SE_119_wait_for_selector_should_survive_iframe_navigation_handle(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    body = page.query_selector("body")
    assert body
    sync_gather(
        lambda: body.wait_for_selector(
            'iframe >> internal:control=enter-frame >> button:has-text("Hello nested iframe")'
        ),
        lambda: page.locator("iframe").evaluate("e => e.src = 'iframe-2.html'"),
    )


def test_SE_120_click_should_survive_frame_reattach(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator(
        'iframe >> internal:control=enter-frame >> button:has-text("Hello nested iframe")'
    )
    sync_gather(lambda: button.click(), lambda: reattach_iframe(page))


def test_SE_121_click_should_survive_iframe_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator(
        'iframe >> internal:control=enter-frame >> button:has-text("Hello nested iframe")'
    )
    sync_gather(
        lambda: button.click(),
        lambda: page.locator("iframe").evaluate("e => e.src = 'iframe-2.html'"),
    )


def test_SE_122_click_should_survive_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    route_iframe(page)
    page.goto(server.PREFIX + "/iframe.html")

    def navigate() -> None:
        page.wait_for_timeout(100)
        page.goto(server.PREFIX + "/iframe-2.html")

    sync_gather(lambda: page.click('button:has-text("Hello nested iframe")'), navigate)


def test_SE_123_should_non_work_for_non_frame(page: Page, server: Server) -> None:
    route_iframe(page)
    page.set_content("<div></div>")
    button = page.locator("div >> internal:control=enter-frame >> button")
    with pytest.raises(Error) as exc_info:
        button.wait_for()
    assert "<div></div>" in exc_info.value.message
    assert "<iframe> was expected" in exc_info.value.message


def test_SE_124_should_match_in_a_descendant_frame(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    # The main frame has no <div>; only the iframe.html child frame does.
    div = page.locator("internal:control=any-frame >> div")
    div.wait_for()
    expect(div).to_have_count(1)
    assert "<button>Hello iframe</button>" in div.inner_html()


def test_SE_125_should_match_in_a_deeply_nested_frame(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    # The main frame has no <div>; only the iframe.html child frame does.
    button = page.locator('internal:control=any-frame >> button[tag="iframe2"]')
    button.wait_for()
    expect(button).to_have_count(1)
    assert button.text_content() == "Hello nested iframe"


def test_SE_126_should_not_match_a_chain_across_frames(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    # The <div> lives in the iframe.html frame, while the button lives in the frame nested below it.
    expect(
        page.locator('internal:control=any-frame >> div >> button[tag="iframe2"]')
    ).to_have_count(0)
    expect(page.locator("internal:control=any-frame >> div >> button")).to_have_text(
        "Hello iframe"
    )


def test_SE_127_should_match_multiple_elements(page: Page, server: Server) -> None:
    route_html(
        page,
        "**/empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_html(page, "**/a.html", "<div>one</div>")
    route_html(page, "**/b.html", "<span>two</span><span>three</span>")
    page.goto(server.EMPTY_PAGE)

    texts = page.eval_on_selector_all(
        "internal:control=any-frame >> span", "els => els.map(e => e.textContent)"
    )
    assert texts == ["two", "three"]


def test_SE_128_should_throw_when_matching_elements_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_html(
        page,
        "**/empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_html(page, "**/a.html", "<div>one</div>")
    route_html(page, "**/b.html", "<div>two</div>")
    page.goto(server.EMPTY_PAGE)

    # Make sure both child frames have their <div> before matching, otherwise resolution
    # may transiently collapse to a single frame.
    # Port of expect.poll(() => page.frames().length).toBe(3).
    for _ in range(50):
        if len(page.frames) == 3:
            break
        page.wait_for_timeout(100)
    assert len(page.frames) == 3
    for frame in page.frames:
        if frame != page.main_frame:
            frame.wait_for_selector("div")

    with pytest.raises(Error) as exc_info:
        page.locator("internal:control=any-frame >> div").inner_html()
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )


def test_SE_129_should_not_allow_any_frame_in_the_middle_of_a_selector(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        page.locator("iframe >> internal:control=any-frame >> div").wait_for()
    assert (
        '"any-frame" is only allowed as the first selector token'
        in exc_info.value.message
    )


def test_SE_130_should_allow_entering_frames_from_any_frame(
    page: Page, server: Server
) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.locator(
        'internal:control=any-frame >> iframe[src="iframe-2.html"] >> internal:control=enter-frame >> button'
    )
    button.wait_for()
    assert button.inner_text() == "Hello nested iframe"


def test_SE_131_should_not_allow_any_frame_after_entering_a_frame(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.locator(
            "iframe >> internal:control=enter-frame >> internal:control=any-frame >> button"
        ).count()
    assert (
        '"any-frame" is only allowed as the first selector token'
        in exc_info.value.message
    )


def test_SE_132_should_not_allow_dangling_enter_frame_after_any_frame(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.locator(
            "internal:control=any-frame >> iframe >> internal:control=enter-frame"
        ).count()
    assert "Selector cannot end with entering frame" in exc_info.value.message
