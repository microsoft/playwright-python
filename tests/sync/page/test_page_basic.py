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

"""Port of tests/page/page-basic.spec.ts."""


import re
from typing import Any, Callable, List, Optional

from playwright.sync_api import ConsoleMessage, Error, Page, expect
from tests.server import Server, TestServerRequest


def test_PA_001_should_fire_load_when_expected(page: Page) -> None:
    with page.expect_event("load"):
        page.goto("about:blank")


def test_PA_002_async_stacks_should_work(page: Page, server: Server) -> None:
    def handle(request: TestServerRequest) -> None:
        # Like req.socket.end().
        assert request.transport
        request.transport.loseConnection()

    server.set_route("/empty.html", handle)
    error: Optional[Error] = None
    try:
        page.goto(server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is not None
    assert error.stack
    assert __file__ in error.stack


def test_PA_003_should_provide_access_to_the_opener_page(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('about:blank')")
    popup = popup_info.value
    opener = popup.opener()
    assert opener == page


def test_PA_004_should_fire_domcontentloaded_when_expected(page: Page) -> None:
    with page.expect_event("domcontentloaded"):
        page.goto("about:blank")


def test_PA_005_should_pass_self_as_argument_to_domcontentloaded_event(
    page: Page,
) -> None:
    with page.expect_event("domcontentloaded") as event_info:
        page.goto("about:blank")
    assert event_info.value == page


def test_PA_006_should_pass_self_as_argument_to_load_event(page: Page) -> None:
    with page.expect_event("load") as event_info:
        page.goto("about:blank")
    assert event_info.value == page


def test_PA_007_page_url_should_work(page: Page, server: Server) -> None:
    assert page.url == "about:blank"
    page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE


def test_PA_008_page_url_should_include_hashes(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE + "#hash")
    assert page.url == server.EMPTY_PAGE + "#hash"
    page.evaluate(
        """() => {
    window.location.hash = 'dynamic';
  }"""
    )
    assert page.url == server.EMPTY_PAGE + "#dynamic"


def test_PA_009_page_title_should_return_the_page_title(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/title.html")
    assert page.title() == "Woof-Woof"


def test_PA_010_page_title_should_not_throw_during_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content("<title>hello</title>")

    def title_or_error() -> Any:
        try:
            return page.title()
        except Error as e:
            return e

    _, title = sync_gather(
        lambda: page.goto(server.PREFIX + "/title.html"), title_or_error
    )
    assert isinstance(title, str)
    assert re.match(r"^(hello|Loading http.*title.html||Woof-Woof)$", title)
    expect(page).to_have_title("Woof-Woof")


def test_PA_011_page_close_should_work_with_window_close(page: Page) -> None:
    with page.expect_popup() as popup_info:
        page.evaluate("() => window['newPage'] = window.open('about:blank')")
    new_page = popup_info.value
    with new_page.expect_event("close"):
        page.evaluate("() => window['newPage'].close()")


def test_PA_012_page_frame_should_respect_name(page: Page) -> None:
    page.set_content("<iframe name=target></iframe>")
    assert page.frame(name="bogus") is None
    frame = page.frame(name="target")
    assert frame
    assert frame == page.main_frame.child_frames[0]


def test_PA_013_page_frame_should_respect_url(page: Page, server: Server) -> None:
    page.set_content(f'<iframe src="{server.EMPTY_PAGE}"></iframe>')
    assert page.frame(url=re.compile(r"bogus")) is None
    frame = page.frame(url=re.compile(r"empty"))
    assert frame
    assert frame.url == server.EMPTY_PAGE


def test_PA_014_should_have_sane_user_agent(page: Page, browser_name: str) -> None:
    user_agent = page.evaluate("() => navigator.userAgent")
    parts = [part.strip() for part in re.split(r"[()]", user_agent)]
    part1 = parts[0]
    part3 = parts[2]
    part4 = parts[3] if len(parts) > 3 else None
    part5 = parts[4] if len(parts) > 4 else None
    # First part is always "Mozilla/5.0"
    assert part1 == "Mozilla/5.0"
    # Second part in parenthesis is platform - ignore it.

    # Third part for Firefox is the last one and encodes engine and browser versions.
    if browser_name == "firefox":
        engine, browser = part3.split(" ")[:2]
        assert engine.startswith("Gecko")
        assert browser.startswith("Firefox")
        assert part4 is None
        assert part5 is None
        return
    # For both options.CHROMIUM and options.WEBKIT, third part is the AppleWebKit version.
    assert part3.startswith("AppleWebKit/")
    assert part4 == "KHTML, like Gecko"
    # 5th part encodes real browser name and engine version.
    assert part5 is not None
    tokens = part5.split(" ")
    engine = tokens[0]
    browser = next((t for t in tokens if t.startswith("Safari/")), None)
    assert browser is not None and browser.startswith("Safari/")
    if browser_name == "chromium":
        assert "Chrome/" in engine
    else:
        assert engine.startswith("Version/")


def test_PA_015_page_press_should_work(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.press("textarea", "a")
    assert page.evaluate("() => document.querySelector('textarea').value") == "a"


def test_PA_016_page_press_should_work_for_enter(page: Page) -> None:
    page.set_content("<input onkeypress=\"console.log('press')\"></input>")
    messages: List[ConsoleMessage] = []
    page.on("console", lambda message: messages.append(message))
    page.press("input", "Enter")
    assert messages[0].text == "press"


def test_PA_017_frame_press_should_work(page: Page, server: Server) -> None:
    page.set_content(
        f'<iframe name=inner src="{server.PREFIX}/input/textarea.html"></iframe>'
    )
    frame = page.frame("inner")
    assert frame
    frame.press("textarea", "a")
    assert frame.evaluate("() => document.querySelector('textarea').value") == "a"


def test_PA_018_has_navigator_webdriver_set_to_true(page: Page) -> None:
    assert page.evaluate("() => navigator.webdriver") is True


def test_PA_019_should_iterate_over_page_properties(page: Page) -> None:
    props = []
    for prop in dir(page):
        value = getattr(page, prop)
        if value is not None and not callable(value):
            props.append(getattr(value, "__iter__", None))
