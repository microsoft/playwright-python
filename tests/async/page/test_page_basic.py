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


import asyncio
import re
from typing import Any, List, Optional

from playwright.async_api import ConsoleMessage, Error, Page, expect
from tests.server import Server, TestServerRequest


async def test_PA_001_should_fire_load_when_expected(page: Page) -> None:
    async with page.expect_event("load"):
        await page.goto("about:blank")


async def test_PA_002_async_stacks_should_work(page: Page, server: Server) -> None:
    def handle(request: TestServerRequest) -> None:
        # Like req.socket.end().
        assert request.transport
        request.transport.loseConnection()

    server.set_route("/empty.html", handle)
    error: Optional[Error] = None
    try:
        await page.goto(server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is not None
    assert error.stack
    assert __file__ in error.stack


async def test_PA_003_should_provide_access_to_the_opener_page(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window.open('about:blank')")
    popup = await popup_info.value
    opener = await popup.opener()
    assert opener == page


async def test_PA_004_should_fire_domcontentloaded_when_expected(page: Page) -> None:
    async with page.expect_event("domcontentloaded"):
        await page.goto("about:blank")


async def test_PA_005_should_pass_self_as_argument_to_domcontentloaded_event(
    page: Page,
) -> None:
    async with page.expect_event("domcontentloaded") as event_info:
        await page.goto("about:blank")
    assert await event_info.value == page


async def test_PA_006_should_pass_self_as_argument_to_load_event(page: Page) -> None:
    async with page.expect_event("load") as event_info:
        await page.goto("about:blank")
    assert await event_info.value == page


async def test_PA_007_page_url_should_work(page: Page, server: Server) -> None:
    assert page.url == "about:blank"
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE


async def test_PA_008_page_url_should_include_hashes(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE + "#hash")
    assert page.url == server.EMPTY_PAGE + "#hash"
    await page.evaluate(
        """() => {
    window.location.hash = 'dynamic';
  }"""
    )
    assert page.url == server.EMPTY_PAGE + "#dynamic"


async def test_PA_009_page_title_should_return_the_page_title(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/title.html")
    assert await page.title() == "Woof-Woof"


async def test_PA_010_page_title_should_not_throw_during_navigation(
    page: Page, server: Server
) -> None:
    await page.set_content("<title>hello</title>")

    async def title_or_error() -> Any:
        try:
            return await page.title()
        except Error as e:
            return e

    _, title = await asyncio.gather(
        page.goto(server.PREFIX + "/title.html"), title_or_error()
    )
    assert isinstance(title, str)
    assert re.match(r"^(hello|Loading http.*title.html||Woof-Woof)$", title)
    await expect(page).to_have_title("Woof-Woof")


async def test_PA_011_page_close_should_work_with_window_close(page: Page) -> None:
    async with page.expect_popup() as popup_info:
        await page.evaluate("() => window['newPage'] = window.open('about:blank')")
    new_page = await popup_info.value
    async with new_page.expect_event("close"):
        await page.evaluate("() => window['newPage'].close()")


async def test_PA_012_page_frame_should_respect_name(page: Page) -> None:
    await page.set_content("<iframe name=target></iframe>")
    assert page.frame(name="bogus") is None
    frame = page.frame(name="target")
    assert frame
    assert frame == page.main_frame.child_frames[0]


async def test_PA_013_page_frame_should_respect_url(page: Page, server: Server) -> None:
    await page.set_content(f'<iframe src="{server.EMPTY_PAGE}"></iframe>')
    assert page.frame(url=re.compile(r"bogus")) is None
    frame = page.frame(url=re.compile(r"empty"))
    assert frame
    assert frame.url == server.EMPTY_PAGE


async def test_PA_014_should_have_sane_user_agent(
    page: Page, browser_name: str
) -> None:
    user_agent = await page.evaluate("() => navigator.userAgent")
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


async def test_PA_015_page_press_should_work(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.press("textarea", "a")
    assert await page.evaluate("() => document.querySelector('textarea').value") == "a"


async def test_PA_016_page_press_should_work_for_enter(page: Page) -> None:
    await page.set_content("<input onkeypress=\"console.log('press')\"></input>")
    messages: List[ConsoleMessage] = []
    page.on("console", lambda message: messages.append(message))
    await page.press("input", "Enter")
    assert messages[0].text == "press"


async def test_PA_017_frame_press_should_work(page: Page, server: Server) -> None:
    await page.set_content(
        f'<iframe name=inner src="{server.PREFIX}/input/textarea.html"></iframe>'
    )
    frame = page.frame("inner")
    assert frame
    await frame.press("textarea", "a")
    assert await frame.evaluate("() => document.querySelector('textarea').value") == "a"


async def test_PA_018_has_navigator_webdriver_set_to_true(page: Page) -> None:
    assert await page.evaluate("() => navigator.webdriver") is True


async def test_PA_019_should_iterate_over_page_properties(page: Page) -> None:
    props = []
    for prop in dir(page):
        value = getattr(page, prop)
        if value is not None and not callable(value):
            props.append(getattr(value, "__iter__", None))
