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

"""Port of tests/page/locator-any-frame.spec.ts."""

import re
import time

import pytest

from playwright.sync_api import Error, Frame, Page, Route, expect
from tests.server import Server


def route_page(page: Page, url: str, body: str) -> None:
    def handler(route: Route) -> None:
        try:
            route.fulfill(body=body, content_type="text/html")
        except Error:
            pass

    page.route("**/" + url, handler)


def stall_route(route: Route) -> None:
    pass


def poll_frame_count(page: Page, count: int) -> None:
    """Port of expect.poll(() => page.frames().length).toBe(count)."""
    deadline = time.monotonic() + 5
    while len(page.frames) != count and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    assert len(page.frames) == count


def wait_for_all_frames(page: Page, frame_count: int, selector: str) -> None:
    # Wait for all child frames to load their content, so that the search
    # deterministically sees elements in all of them.
    poll_frame_count(page, frame_count)
    for frame in page.frames:
        if frame != page.main_frame:
            frame.wait_for_selector(selector, state="attached")


def find_frame(page: Page, url_part: str) -> Frame:
    return next(f for f in page.frames if url_part in f.url)


def test_LO_001_should_click_a_button_inside_an_iframe(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(
        page,
        "a.html",
        '<button onclick="window.__clicked = true">Click me</button>',
    )
    page.goto(server.EMPTY_PAGE)
    page.frame_locator().get_by_role("button", name="Click me").click()
    assert page.frames[1].evaluate("() => window.__clicked") is True


def test_LO_002_should_click_a_button_in_the_main_frame(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><button onclick="window.__clicked = true">Click me</button>',
    )
    route_page(page, "a.html", "<div>No buttons here</div>")
    page.goto(server.EMPTY_PAGE)
    page.frame_locator().locator("button").click()
    assert page.evaluate("() => window.__clicked") is True


def test_LO_003_should_fail_click_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", "<button>one</button>")
    route_page(page, "b.html", "<button>two</button>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 3, "button")
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("button").click(timeout=3000)
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )
    assert 'waiting for frame_locator().locator("button")' in exc_info.value.message


def test_LO_004_should_fail_click_upon_strict_mode_violation_inside_a_single_frame(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<button>one</button><button>two</button>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "button")
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("button").click(timeout=3000)
    assert "strict mode violation" in exc_info.value.message
    assert 'waiting for frame_locator().locator("button")' in exc_info.value.message


def test_LO_005_should_time_out_on_click_when_there_are_no_matches(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>Nothing here</div>")
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("button").click(timeout=1000)
    assert "Timeout 1000ms exceeded" in exc_info.value.message
    assert 'waiting for frame_locator().locator("button")' in exc_info.value.message


def test_LO_006_should_count_elements_in_a_single_frame(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>1</div><div>2</div><div>3</div>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "div")
    assert page.frame_locator().locator("div").count() == 3
    assert page.frame_locator().locator("button").count() == 0


def test_LO_007_should_fail_count_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<div>main</div><iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>child</div>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "div")
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("div").count()
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )


def test_LO_008_should_support_to_have_count(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<span>one</span><span>two</span>")
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("span")).to_have_count(2)
    expect(page.frame_locator().locator("button")).to_have_count(0)


def test_LO_009_should_wait_for_a_frame_to_appear_with_to_have_count(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", "<div>No frames yet</div>")
    route_page(page, "a.html", "<span>one</span><span>two</span>")
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
        window.builtins.setTimeout(() => {
          const iframe = document.createElement('iframe');
          iframe.src = 'a.html';
          document.body.appendChild(iframe);
        }, 500);
      }"""
    )
    expect(page.frame_locator().locator("span")).to_have_count(2)


def test_LO_010_should_fail_to_have_count_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", "<span>one</span>")
    route_page(page, "b.html", "<span>two</span>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 3, "span")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.frame_locator().locator("span")).to_have_count(2, timeout=3000)
    assert "frameLocator() matched elements in multiple frames" in str(exc_info.value)
    assert 'waiting for frame_locator().locator("span")' in str(exc_info.value)


def test_LO_011_should_support_to_have_text(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>Hello iframe</div>")
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("div")).to_have_text("Hello iframe")


def test_LO_012_should_support_to_have_text_with_an_array(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<span>one</span><span>two</span>")
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("span")).to_have_text(["one", "two"])


def test_LO_013_should_fail_to_have_text_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", "<div>one</div>")
    route_page(page, "b.html", "<div>two</div>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 3, "div")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.frame_locator().locator("div")).to_have_text("one", timeout=3000)
    assert "frameLocator() matched elements in multiple frames" in str(exc_info.value)
    assert 'waiting for frame_locator().locator("div")' in str(exc_info.value)


def test_LO_014_should_fail_to_have_text_with_an_array_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", "<span>one</span>")
    route_page(page, "b.html", "<span>two</span>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 3, "span")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.frame_locator().locator("span")).to_have_text(
            ["one", "two"], timeout=3000
        )
    assert "frameLocator() matched elements in multiple frames" in str(exc_info.value)


def test_LO_015_should_fail_to_have_text_upon_strict_mode_violation_inside_a_single_frame(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>one</div><div>two</div>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "div")
    with pytest.raises(AssertionError) as exc_info:
        expect(page.frame_locator().locator("div")).to_have_text("one", timeout=3000)
    assert "strict mode violation" in str(exc_info.value)
    assert 'waiting for frame_locator().locator("div")' in str(exc_info.value)


def test_LO_016_should_support_evaluate(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", '<div data-foo="bar">Hello</div>')
    page.goto(server.EMPTY_PAGE)
    assert (
        page.frame_locator().locator("div").evaluate("e => e.getAttribute('data-foo')")
        == "bar"
    )


def test_LO_017_should_fail_evaluate_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", "<div>one</div>")
    route_page(page, "b.html", "<div>two</div>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 3, "div")
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("div").evaluate(
            "e => e.textContent", None, timeout=3000
        )
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )


def test_LO_018_should_time_out_on_evaluate_when_there_are_no_matches(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>Nothing here</div>")
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("button").evaluate(
            "e => e.textContent", None, timeout=1000
        )
    assert "Timeout 1000ms exceeded" in exc_info.value.message
    assert 'waiting for frame_locator().locator("button")' in exc_info.value.message


def test_LO_019_should_support_evaluate_all(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<span>one</span><span>two</span>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "span")
    assert page.frame_locator().locator("span").evaluate_all(
        "els => els.map(e => e.textContent)"
    ) == ["one", "two"]
    assert page.frame_locator().locator("button").evaluate_all("els => els.length") == 0


def test_LO_020_should_fail_evaluate_all_when_elements_match_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", "<span>one</span>")
    route_page(page, "b.html", "<span>two</span>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 3, "span")
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("span").evaluate_all("els => els.length")
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )


def test_LO_021_should_support_has_text_filter(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>foo</div><div>bar</div>")
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("div", has_text="bar")).to_have_text("bar")


def test_LO_022_should_support_first_last_nth(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<span>one</span><span>two</span><span>three</span>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "span")
    expect(page.frame_locator().locator("span").first).to_have_text("one")
    expect(page.frame_locator().locator("span").last).to_have_text("three")
    expect(page.frame_locator().locator("span").nth(1)).to_have_text("two")


def test_LO_023_should_support_nth_in_the_middle_of_the_chain(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div><span>one</span></div><div><span>two</span></div>")
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("div").nth(1).locator("span")).to_have_text(
        "two"
    )


def test_LO_024_should_support_composite_locators(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div><span>foo</span></div><div><i>bar</i></div>")
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("div", has=page.locator("span"))).to_have_text(
        "foo"
    )


def test_LO_025_should_support_capture(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", '<div id="target"><span>hello</span></div>')
    page.goto(server.EMPTY_PAGE)
    expect(page.frame_locator().locator("*css=div >> span")).to_have_attribute(
        "id", "target"
    )


def test_LO_026_should_find_a_frame_inside_the_scope(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<section><iframe src="a.html"></iframe></section><button>outside</button>',
    )
    route_page(page, "a.html", "<button>inside</button>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "button")
    scope = page.query_selector("section")
    assert scope
    buttons = scope.query_selector_all("internal:control=any-frame >> button")
    assert len(buttons) == 1
    assert buttons[0].text_content() == "inside"


def test_LO_027_should_find_a_nested_frame_inside_the_scope(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<section><iframe src="a.html"></iframe></section><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", '<iframe src="c.html"></iframe>')
    route_page(page, "b.html", "<button>outside</button>")
    route_page(page, "c.html", "<button>deep</button>")
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 4)
    for frame in page.frames:
        if "b.html" in frame.url or "c.html" in frame.url:
            frame.wait_for_selector("button", state="attached")
    scope = page.query_selector("section")
    assert scope
    buttons = scope.query_selector_all("internal:control=any-frame >> button")
    assert len(buttons) == 1
    assert buttons[0].text_content() == "deep"


def test_LO_028_should_find_a_frame_inside_the_scope_while_another_iframe_is_stalled(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<section><iframe src="a.html"></iframe><iframe src="stall.html"></iframe></section>',
    )
    route_page(page, "a.html", "<button>inside</button>")
    page.route("**/stall.html", stall_route)
    page.goto(server.EMPTY_PAGE, wait_until="domcontentloaded")
    poll_frame_count(page, 3)
    scope = page.query_selector("section")
    assert scope
    buttons = scope.query_selector_all("internal:control=any-frame >> button")
    assert len(buttons) == 1
    assert buttons[0].text_content() == "inside"


def test_LO_029_should_respect_the_scope_without_a_frame_inside_the_scope(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<section><button>target</button></section><iframe src="a.html"></iframe>',
    )
    route_page(page, "a.html", "<button>in-frame</button>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "button")
    scope = page.query_selector("section")
    assert scope
    buttons = scope.query_selector_all("internal:control=any-frame >> button")
    assert len(buttons) == 1
    assert buttons[0].text_content() == "target"


def test_LO_030_should_not_match_a_chain_across_a_frame_boundary(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<section><iframe src="a.html"></iframe></section>')
    route_page(page, "a.html", '<iframe src="b.html"></iframe>')
    route_page(page, "b.html", "<button>deep</button>")
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 3)
    deep_frame = find_frame(page, "b.html")
    deep_frame.wait_for_selector("button", state="attached")
    # "section" lives in the main frame, while the button is two frames below it.
    expect(page.frame_locator().locator("section").locator("button")).to_have_count(0)
    expect(page.frame_locator().locator("button")).to_have_text("deep")


def test_LO_031_should_only_search_frames_inside_the_starting_frame(
    page: Page, server: Server
) -> None:
    route_page(
        page, "empty.html", '<iframe src="a.html"></iframe><button>main</button>'
    )
    route_page(page, "a.html", '<iframe src="b.html"></iframe>')
    route_page(page, "b.html", "<button>deep</button>")
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 3)
    deep_frame = find_frame(page, "b.html")
    deep_frame.wait_for_selector("button", state="attached")
    middle_frame = find_frame(page, "a.html")
    expect(middle_frame.frame_locator().locator("button")).to_have_text("deep")


def test_LO_032_should_enter_a_frame_found_in_a_nested_frame(
    page: Page, server: Server
) -> None:
    route_page(
        page, "empty.html", '<iframe src="a.html"></iframe><button>main</button>'
    )
    route_page(
        page,
        "a.html",
        '<iframe id="target" src="b.html"></iframe><button>decoy</button>',
    )
    route_page(page, "b.html", "<button>inside</button>")
    page.goto(server.EMPTY_PAGE)
    expect(
        page.frame_locator().frame_locator("#target").locator("button")
    ).to_have_text("inside")


def test_LO_033_should_click_inside_an_entered_frame(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(
        page,
        "a.html",
        '<iframe id="target" src="b.html"></iframe><button>Click me</button>',
    )
    route_page(
        page,
        "b.html",
        '<button onclick="window.__clicked = true">Click me</button>',
    )
    page.goto(server.EMPTY_PAGE)
    page.frame_locator().frame_locator("#target").get_by_role(
        "button", name="Click me"
    ).click()
    frame = find_frame(page, "b.html")
    assert frame.evaluate("() => window.__clicked") is True


def test_LO_034_should_not_search_nested_frames_after_entering_a_frame(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe id="target" src="a.html"></iframe><button>main</button>',
    )
    route_page(page, "a.html", '<iframe src="b.html"></iframe>')
    route_page(page, "b.html", "<button>deep</button>")
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 3)
    # The entered frame itself has no button, and we do not look inside its nested frames.
    expect(
        page.frame_locator().frame_locator("#target").locator("button")
    ).to_have_count(0)


def test_LO_035_should_support_two_frame_locators(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", '<iframe id="x" src="b.html"></iframe>')
    route_page(
        page,
        "b.html",
        '<iframe id="y" src="c.html"></iframe><button>decoy</button>',
    )
    route_page(page, "c.html", "<button>bottom</button>")
    page.goto(server.EMPTY_PAGE)
    expect(
        page.frame_locator().frame_locator("#x").frame_locator("#y").locator("button")
    ).to_have_text("bottom")


def test_LO_036_should_support_locator_before_frame_locator(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(
        page,
        "a.html",
        '<section><iframe src="b.html"></iframe></section><iframe src="c.html"></iframe>',
    )
    route_page(page, "b.html", "<button>in-section</button>")
    route_page(page, "c.html", "<button>outside</button>")
    page.goto(server.EMPTY_PAGE)
    expect(
        page.frame_locator()
        .locator("section")
        .frame_locator("iframe")
        .locator("button")
    ).to_have_text("in-section")


def test_LO_037_should_support_owner_of_a_frame_locator(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", '<iframe id="target" src="b.html"></iframe>')
    route_page(page, "b.html", "<button>inside</button>")
    page.goto(server.EMPTY_PAGE)
    assert (
        page.frame_locator().frame_locator("#target").owner.get_attribute("id")
        == "target"
    )


def test_LO_038_should_wait_for_the_frame_to_enter_to_appear(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", "<div>Nothing yet</div>")
    route_page(page, "b.html", "<button>late</button>")
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 2)
    page.frames[1].evaluate(
        """() => {
        window.builtins.setTimeout(() => {
          const iframe = document.createElement('iframe');
          iframe.id = 'late';
          iframe.src = 'b.html';
          document.body.appendChild(iframe);
        }, 3000);
      }"""
    )
    expect(page.frame_locator().frame_locator("#late").locator("button")).to_have_text(
        "late"
    )


def test_LO_039_should_fail_when_the_frame_to_enter_matches_in_multiple_frames(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="b.html"></iframe>',
    )
    route_page(page, "a.html", '<iframe class="inner" src="c.html"></iframe>')
    route_page(page, "b.html", '<iframe class="inner" src="c.html"></iframe>')
    route_page(page, "c.html", "<button>Click me</button>")
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 5)
    for frame in page.frames:
        if "c.html" in frame.url:
            frame.wait_for_selector("button", state="attached")
    with pytest.raises(Error) as exc_info:
        page.frame_locator().frame_locator(".inner").locator("button").click(
            timeout=3000
        )
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )


def test_LO_040_should_support_content_frame(page: Page, server: Server) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(
        page,
        "a.html",
        '<iframe id="target" src="b.html"></iframe><button>decoy</button>',
    )
    route_page(page, "b.html", "<button>inside</button>")
    page.goto(server.EMPTY_PAGE)
    expect(
        page.frame_locator().locator("#target").content_frame.locator("button")
    ).to_have_text("inside")


def test_LO_041_should_render_frame_locator_in_the_locator_description(
    page: Page,
) -> None:
    # Locator.toString() is JavaScript-only: Python shows the locator description
    # in the call log of an error instead.
    with pytest.raises(Error) as exc_info:
        page.frame_locator().frame_locator("#x").locator("button").click(timeout=1)
    assert (
        'waiting for frame_locator().locator("#x").content_frame.locator("button")'
        in exc_info.value.message
    )
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("section").frame_locator("iframe").get_by_text(
            "foo"
        ).click(timeout=1)
    assert (
        'waiting for frame_locator().locator("section").locator("iframe").content_frame.get_by_text("foo")'
        in exc_info.value.message
    )


def test_LO_042_should_not_allow_frame_locator_inside_a_composite_locator(
    page: Page, server: Server
) -> None:
    route_page(
        page, "empty.html", '<button>main</button><iframe src="a.html"></iframe>'
    )
    route_page(page, "a.html", '<a href="#">link</a>')
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "a")

    with pytest.raises(Error) as exc_info:
        page.locator("button").or_(page.frame_locator().locator("a")).count()
    assert (
        'frameLocator() is not allowed inside composite locators, while querying "locator("button").or_(frame_locator().locator("a"))"'
        in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        page.locator("button").filter(has=page.frame_locator().locator("a")).count()
    assert (
        "frameLocator() is not allowed inside composite locators"
        in exc_info.value.message
    )

    # Repeating frameLocator() in the operand is not allowed either, even though the outer locator has it.
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("button").or_(
            page.frame_locator().locator("a")
        ).count()
    assert (
        'frameLocator() is not allowed inside composite locators, while querying "frame_locator().locator("button").or_(frame_locator().locator("a"))"'
        in exc_info.value.message
    )

    # Repeating frameLocator() is not allowed even when the rest of the frame chain matches.
    with pytest.raises(Error) as exc_info:
        page.frame_locator().frame_locator("#f").locator("a").or_(
            page.frame_locator().frame_locator("#f").locator("button")
        ).count()
    assert (
        "frameLocator() is not allowed inside composite locators"
        in exc_info.value.message
    )

    # With frameLocator() first, the token applies to the whole locator, so both operands are searched in every frame.
    with pytest.raises(Error) as exc_info:
        page.frame_locator().locator("a").or_(page.locator("button")).count()
    assert (
        "frameLocator() matched elements in multiple frames" in exc_info.value.message
    )


def test_LO_043_should_support_a_composite_locator_under_frame_locator(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(
        page,
        "a.html",
        '<div class="classname">first</div><button>second</button>',
    )
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "button")
    expect(
        page.frame_locator().locator(".classname").or_(page.get_by_role("button"))
    ).to_have_text(["first", "second"])


def test_LO_044_should_support_a_composite_locator_under_frame_locator_and_a_frame_locator(
    page: Page, server: Server
) -> None:
    route_page(page, "empty.html", '<iframe src="a.html"></iframe>')
    route_page(page, "a.html", '<iframe id="f" src="b.html"></iframe>')
    route_page(
        page,
        "b.html",
        '<div class="classname">first</div><button>second</button>',
    )
    page.goto(server.EMPTY_PAGE)
    poll_frame_count(page, 3)
    expect(
        page.frame_locator()
        .frame_locator("#f")
        .locator(".classname")
        .or_(page.frame_locator("#f").get_by_role("button"))
    ).to_have_text(["first", "second"])


def test_LO_045_should_not_allow_first_last_nth_on_frame_locator(
    page: Page,
) -> None:
    with pytest.raises(
        Error,
        match=re.escape("Selecting the nth frame is not allowed on frame_locator()"),
    ):
        page.frame_locator().first
    with pytest.raises(
        Error,
        match=re.escape("Selecting the nth frame is not allowed on frame_locator()"),
    ):
        page.frame_locator().last
    with pytest.raises(
        Error,
        match=re.escape("Selecting the nth frame is not allowed on frame_locator()"),
    ):
        page.frame_locator().nth(1)


def test_LO_046_should_not_allow_owner_on_frame_locator(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.frame_locator().owner.count()
    assert "Selector cannot be empty after frameLocator()" in exc_info.value.message


def test_LO_047_should_resolve_aria_ref_selectors(page: Page, server: Server) -> None:
    route_page(
        page, "empty.html", '<button>main</button><iframe src="a.html"></iframe>'
    )
    route_page(page, "a.html", "<button>inside</button>")
    page.goto(server.EMPTY_PAGE)
    wait_for_all_frames(page, 2, "button")
    snapshot = page.aria_snapshot(mode="ai")
    # Refs are unique across frames, so every starting frame resolves them to the same element.
    inside_match = re.search(r'button "inside" \[ref=(.*?)\]', snapshot)
    assert inside_match
    assert re.match(r"^f\d+e\d+$", inside_match.group(1))
    expect(
        page.frame_locator().locator(f"aria-ref={inside_match.group(1)}")
    ).to_have_text("inside")


def test_LO_048_should_click_while_another_iframe_is_stalled(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="stall.html"></iframe>',
    )
    route_page(
        page,
        "a.html",
        '<button onclick="window.__clicked = true">Click me</button>',
    )
    page.route("**/stall.html", stall_route)
    page.goto(server.EMPTY_PAGE, wait_until="domcontentloaded")
    poll_frame_count(page, 3)
    page.frame_locator().locator("button").click()
    frame = find_frame(page, "a.html")
    assert frame.evaluate("() => window.__clicked") is True


def test_LO_049_should_support_to_be_visible_while_another_iframe_is_stalled(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="stall.html"></iframe>',
    )
    route_page(page, "a.html", "<button>Click me</button>")
    page.route("**/stall.html", stall_route)
    page.goto(server.EMPTY_PAGE, wait_until="domcontentloaded")
    poll_frame_count(page, 3)
    expect(page.frame_locator().locator("button")).to_be_visible()


def test_LO_050_should_support_to_have_count_while_another_iframe_is_stalled(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html"></iframe><iframe src="stall.html"></iframe>',
    )
    route_page(page, "a.html", "<button>Click me</button>")
    page.route("**/stall.html", stall_route)
    page.goto(server.EMPTY_PAGE, wait_until="domcontentloaded")
    poll_frame_count(page, 3)
    expect(page.frame_locator().locator("button")).to_have_count(1)


def test_LO_051_should_treat_elements_inside_hidden_iframe_as_hidden(
    page: Page, server: Server
) -> None:
    route_page(
        page,
        "empty.html",
        '<iframe src="a.html" style="visibility: hidden"></iframe>',
    )
    route_page(
        page,
        "a.html",
        '<button onclick="window.__clicked = true">Click me</button>',
    )
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator().locator("button")
    expect(button).to_be_attached()
    assert button.is_visible() is False
    expect(button).to_be_hidden()

    with pytest.raises(Error) as exc_info:
        button.click(timeout=1000)
    assert "element is inside a hidden frame, retrying" in exc_info.value.message
    assert page.frames[1].evaluate("() => window.__clicked") is None

    page.evaluate("() => document.querySelector('iframe').style.visibility = 'visible'")
    expect(button).to_be_visible()
    button.click()
    assert page.frames[1].evaluate("() => window.__clicked") is True
