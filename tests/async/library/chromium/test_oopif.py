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

"""Port of tests/library/chromium/oopif.spec.ts."""

import asyncio
import json
import time
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
)

import pytest

from playwright.async_api import (
    Browser,
    BrowserType,
    Frame,
    Page,
    Playwright,
    Route,
    expect,
)
from tests.server import Server, TestServerRequest, find_free_port

from ...utils import Utils

pytestmark = pytest.mark.only_browser("chromium")


@pytest.fixture(scope="module")
async def browser(
    browser_name: str, browser_type: BrowserType, launch_arguments: Dict
) -> AsyncGenerator[Browser, None]:
    # Port of it.use({ launchOptions: { args: ['--site-per-process'] } }).
    if browser_name != "chromium":
        pytest.skip("chromium only")
    browser = await browser_type.launch(**launch_arguments, args=["--site-per-process"])
    yield browser
    await browser.close()


async def poll(
    actual: Callable[[], Awaitable[Any]], expected: Any, timeout: float = 10000
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = await actual()
    while value != expected and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
        value = await actual()
    assert value == expected


async def assert_oopif_count(browser: Browser, count: int) -> None:
    if browser.browser_type.name != "chromium":
        return
    assert await count_oopifs(browser) == count


async def count_oopifs(browser: Browser) -> int:
    browser_session = await browser.new_browser_cdp_session()
    oopifs: List[Dict] = []

    def on_target_created(event: Dict) -> None:
        if event["targetInfo"]["type"] == "iframe":
            oopifs.append(event["targetInfo"])

    browser_session.on("Target.targetCreated", on_target_created)
    await browser_session.send("Target.setDiscoverTargets", {"discover": True})
    await browser_session.detach()
    return len(oopifs)


async def test_OO_001_should_report_oopif_frames(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    assert len(page.frames) == 2
    assert (
        await page.frames[1].evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )


async def test_OO_002_should_handle_oopif_detach(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    assert len(page.frames) == 2
    frame = page.frames[1]
    assert (
        await frame.evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )
    async with page.expect_event("framedetached") as detached_frame_info:
        await page.evaluate("() => document.querySelector('iframe').remove()")
    detached_frame = await detached_frame_info.value
    assert detached_frame == frame


async def test_OO_003_should_remove_workers_of_a_detached_oopif(
    page: Page, browser: Browser, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker() as worker_info:
        await utils.attach_frame(
            page, "frame1", server.CROSS_PROCESS_PREFIX + "/worker/worker.html"
        )
    worker = await worker_info.value
    await assert_oopif_count(browser, 1)
    assert len(page.workers) == 1
    async with worker.expect_event("close"):
        await page.goto(server.PREFIX + "/title.html")
    assert len(page.workers) == 0


async def test_OO_004_should_not_hang_in_unroute_all_when_oopif_worker_is_gone(
    page: Page, browser: Browser, server: Server, utils: Utils
) -> None:
    async def handle(route: Route) -> None:
        await route.continue_()

    await page.context.route("**/*", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_worker():
        await utils.attach_frame(
            page, "frame1", server.CROSS_PROCESS_PREFIX + "/worker/worker.html"
        )
    await assert_oopif_count(browser, 1)
    await page.goto(server.CROSS_PROCESS_PREFIX + "/title.html")
    await page.context.unroute_all()


async def test_OO_005_should_handle_remote_local_remote_transitions(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    assert (
        await page.frames[1].evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )
    async with page.frames[1].expect_navigation():
        await page.evaluate("goLocal()")
    assert (
        await page.frames[1].evaluate("() => '' + location.href")
        == server.PREFIX + "/grid.html"
    )
    await assert_oopif_count(browser, 0)
    async with page.frames[1].expect_navigation():
        await page.evaluate("goRemote()")
    assert (
        await page.frames[1].evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )
    await assert_oopif_count(browser, 1)


async def test_OO_006_should_get_the_proper_viewport(
    page: Page, browser: Browser, server: Server
) -> None:
    pytest.skip("fixme")
    assert page.viewport_size == {"width": 1280, "height": 720}
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    oopif = page.frames[1]
    assert await oopif.evaluate("() => screen.width") == 1280
    assert await oopif.evaluate("() => screen.height") == 720
    assert (
        await oopif.evaluate("() => matchMedia('(device-width: 1280px)').matches")
        is True
    )
    assert (
        await oopif.evaluate("() => matchMedia('(device-height: 720px)').matches")
        is True
    )
    assert await oopif.evaluate("() => 'ontouchstart' in window") is False
    await page.set_viewport_size({"width": 123, "height": 456})
    assert await oopif.evaluate("() => screen.width") == 123
    assert await oopif.evaluate("() => screen.height") == 456
    assert (
        await oopif.evaluate("() => matchMedia('(device-width: 123px)').matches")
        is True
    )
    assert (
        await oopif.evaluate("() => matchMedia('(device-height: 456px)').matches")
        is True
    )
    assert await oopif.evaluate("() => 'ontouchstart' in window") is False


async def test_OO_007_should_expose_function(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    oopif = page.frames[1]
    await page.expose_function("mul", lambda a, b: a * b)
    result = await oopif.evaluate(
        """async function() {
        return await window['mul'](9, 4);
      }"""
    )
    assert result == 36


async def test_OO_008_should_emulate_media(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    oopif = page.frames[1]
    assert (
        await oopif.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is False
    )
    await page.emulate_media(color_scheme="dark")
    assert (
        await oopif.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )


async def test_OO_009_should_emulate_offline(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    oopif = page.frames[1]
    assert await oopif.evaluate("() => navigator.onLine") is True
    await page.context.set_offline(True)
    assert await oopif.evaluate("() => navigator.onLine") is False


async def test_OO_010_should_support_context_options(
    browser: Browser, server: Server, playwright: Playwright
) -> None:
    iphone = {**playwright.devices["iPhone 6"]}
    del iphone["default_browser_type"]
    context = await browser.new_context(
        **{
            **iphone,
            "timezone_id": "America/Jamaica",
            "locale": "fr-CH",
            "user_agent": "UA",
        }
    )
    page = await context.new_page()

    with server.expect_request("/grid.html") as request_info:
        await page.goto(server.PREFIX + "/dynamic-oopif.html")
    request = request_info.value
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    oopif = page.frames[1]

    assert await oopif.evaluate("() => 'ontouchstart' in window") is True
    assert (
        await oopif.evaluate("() => new Date(1479579154987).toString()")
        == "Sat Nov 19 2016 13:12:34 GMT-0500 (heure normale de l’Est nord-américain)"
    )
    assert await oopif.evaluate("() => navigator.language") == "fr-CH"
    assert await oopif.evaluate("() => navigator.userAgent") == "UA"
    assert request.getHeader("user-agent") == "UA"

    await context.close()


async def test_OO_011_should_respect_route(
    page: Page, browser: Browser, server: Server
) -> None:
    intercepted = False

    async def handle(route: Route) -> None:
        nonlocal intercepted
        intercepted = True
        await route.continue_()

    await page.route("**/digits/0.png", handle)
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    assert intercepted is True


async def test_OO_012_should_take_screenshot(
    page: Page,
    browser: Browser,
    server: Server,
    assert_to_be_golden: Callable[[bytes, str], None],
    utils: Utils,
) -> None:
    await page.set_viewport_size({"width": 500, "height": 500})
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    await utils.rafraf(page.frames[1])
    assert_to_be_golden(await page.screenshot(), "screenshot-oopif.png")


async def test_OO_013_should_load_oopif_iframes_with_subresources_and_route(
    page: Page, browser: Browser, server: Server
) -> None:
    async def handle(route: Route) -> None:
        await route.continue_()

    await page.route("**/*", handle)
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)


async def test_OO_014_should_report_main_requests(
    page: Page, browser: Browser, server: Server
) -> None:
    request_frames: List[Frame] = []
    page.on("request", lambda r: request_frames.append(r.frame))
    finished_frames: List[Frame] = []
    page.on("requestfinished", lambda r: finished_frames.append(r.frame))

    await page.goto(server.PREFIX + "/empty.html")
    main = page.main_frame

    await main.evaluate(
        """url => {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        document.body.appendChild(iframe);
        return new Promise(f => iframe.onload = f);
      }""",
        server.CROSS_PROCESS_PREFIX + "/empty.html",
    )
    assert len(page.frames) == 2
    child = main.child_frames[0]
    await child.wait_for_load_state("domcontentloaded")

    await child.evaluate(
        """url => {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        document.body.appendChild(iframe);
        return new Promise(f => iframe.onload = f);
      }""",
        server.PREFIX + "/empty.html",
    )
    assert len(page.frames) == 3
    grand_child = child.child_frames[0]
    await grand_child.wait_for_load_state("domcontentloaded")

    await assert_oopif_count(browser, 2)
    assert request_frames[0] == main
    assert finished_frames[0] == main
    assert request_frames[1] == child
    assert finished_frames[1] == child
    assert request_frames[2] == grand_child
    assert finished_frames[2] == grand_child


async def test_OO_015_should_support_expose_function(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.context.expose_function("dec", lambda a: a - 1)
    await page.expose_function("inc", lambda a: a + 1)
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    assert len(page.frames) == 2
    assert await page.frames[0].evaluate("() => window['inc'](3)") == 4
    assert await page.frames[1].evaluate("() => window['inc'](4)") == 5
    assert await page.frames[0].evaluate("() => window['dec'](3)") == 2
    assert await page.frames[1].evaluate("() => window['dec'](4)") == 3


async def test_OO_016_should_support_add_init_script(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.context.add_init_script("window['bar'] = 17")
    await page.add_init_script("window['foo'] = 42")
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    assert len(page.frames) == 2
    assert await page.frames[0].evaluate("() => window['foo']") == 42
    assert await page.frames[1].evaluate("() => window['foo']") == 42
    assert await page.frames[0].evaluate("() => window['bar']") == 17
    assert await page.frames[1].evaluate("() => window['bar']") == 17


# @see https://github.com/microsoft/playwright/issues/1240
async def test_OO_017_should_click_a_button_when_it_overlays_oopif(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/button-overlay-oopif.html")
    await assert_oopif_count(browser, 1)
    await page.click("button")
    assert await page.evaluate("() => window['BUTTON_CLICKED']") is True


async def test_OO_018_should_report_google_com_frame_with_headed(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    browser_channel: Optional[str],
) -> None:
    if browser_channel == "chromium-headless-shell":
        pytest.skip("Headless Shell does not support headed mode")
    # @see https://github.com/GoogleChrome/puppeteer/issues/2548
    # https://google.com is isolated by default in Chromium embedder.
    browser = await browser_type.launch(**{**launch_arguments, "headless": False})
    page = await browser.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.route("**/*", lambda route: route.fulfill(body="YO, GOOGLE.COM"))
    await page.evaluate(
        """() => {
        const frame = document.createElement('iframe');
        frame.setAttribute('src', 'https://google.com/');
        document.body.appendChild(frame);
        return new Promise(x => frame.onload = x);
      }"""
    )
    await page.wait_for_selector('iframe[src="https://google.com/"]')
    await assert_oopif_count(browser, 1)
    urls = [frame.url for frame in page.frames]
    assert urls == [server.EMPTY_PAGE, "https://google.com/"]
    await browser.close()


async def test_OO_019_element_handle_bounding_box_should_work(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await page.eval_on_selector(
        "iframe",
        """iframe => {
        iframe.style.width = '520px';
        iframe.style.height = '520px';
        iframe.style.marginLeft = '42px';
        iframe.style.marginTop = '17px';
      }""",
    )
    await page.frames[1].goto(page.frames[1].url)

    await assert_oopif_count(browser, 1)
    handle1 = await page.frames[1].query_selector(".box:nth-of-type(13)")
    assert handle1
    await poll(
        handle1.bounding_box,
        {"x": 100 + 42, "y": 50 + 17, "width": 50, "height": 50},
    )

    async with page.frames[1].expect_navigation():
        await page.evaluate("goLocal()")
    await assert_oopif_count(browser, 0)
    handle2 = await page.frames[1].query_selector(".box:nth-of-type(13)")
    assert handle2
    await poll(
        handle2.bounding_box,
        {"x": 100 + 42, "y": 50 + 17, "width": 50, "height": 50},
    )


async def test_OO_020_should_click(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await page.eval_on_selector(
        "iframe",
        """iframe => {
        iframe.style.width = '500px';
        iframe.style.height = '500px';
        iframe.style.marginLeft = '102px';
        iframe.style.marginTop = '117px';
      }""",
    )
    await page.frames[1].goto(page.frames[1].url)

    await assert_oopif_count(browser, 1)
    handle1 = await page.frames[1].query_selector(".box:nth-of-type(13)")
    assert handle1
    await handle1.evaluate(
        "div => div.addEventListener('click', () => window['_clicked'] = true, false)"
    )
    await handle1.click()
    assert await handle1.evaluate("() => window['_clicked']") is True


async def test_OO_021_content_frame_should_work(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    assert await page.locator("iframe").content_frame.locator("div").count() == 200
    oopif = await page.query_selector("iframe")
    assert oopif
    content = await oopif.content_frame()
    assert content
    assert await content.locator("div").count() == 200


async def test_OO_022_should_allow_cdp_sessions_on_oopifs(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    assert len(page.frames) == 2
    assert (
        await page.frames[1].evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )

    parent_cdp = await page.context.new_cdp_session(page.frames[0])
    parent = await parent_cdp.send("DOM.getDocument", {"pierce": True, "depth": -1})
    assert "./digits/1.png" not in json_stringify(parent)

    oopif_cdp = await page.context.new_cdp_session(page.frames[1])
    oopif = await oopif_cdp.send("DOM.getDocument", {"pierce": True, "depth": -1})
    assert "./digits/1.png" in json_stringify(oopif)


def json_stringify(value: Any) -> str:
    """Port of JSON.stringify()."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


async def test_OO_023_should_emit_filechooser_event_for_iframe(
    page: Page, server: Server, browser: Browser
) -> None:
    # Add listener before OOPIF is created.
    async with page.expect_file_chooser() as chooser_info:
        await page.goto(server.PREFIX + "/dynamic-oopif.html")
        await assert_oopif_count(browser, 1)
        assert len(page.frames) == 2
        frame = page.frames[1]
        await frame.set_content("<input type=file>")
        await frame.click("input")
    chooser = await chooser_info.value
    assert chooser


async def test_OO_024_should_be_able_to_click_in_iframe(
    page: Page, server: Server, browser: Browser
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    assert len(page.frames) == 2
    frame = page.frames[1]
    await frame.set_content("<button onclick=\"console.log('clicked')\">OK</button>")
    async with page.expect_console_message() as message_info:
        await frame.click("button")
    message = await message_info.value
    assert message.text == "clicked"


async def test_OO_025_should_not_throw_on_expose_function_when_oopif_detaches(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/dynamic-oopif.html")
    await assert_oopif_count(browser, 1)
    await asyncio.gather(
        page.expose_function("myFunc", lambda: 2022),
        page.evaluate("() => document.querySelector('iframe').remove()"),
    )
    assert await page.evaluate("() => window.myFunc()") == 2022


async def test_OO_026_should_intercept_response_body_from_oopif(
    page: Page, browser: Browser, server: Server
) -> None:
    async with page.expect_response("**/grid.html") as response_info:
        await page.goto(server.PREFIX + "/dynamic-oopif.html")
    response = await response_info.value
    assert await response.text()


async def test_OO_027_should_navigate_a_local_frame_to_oopif_with_frame_goto(
    page: Page, browser: Browser, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    await assert_oopif_count(browser, 0)
    frame = page.frames[1]
    assert frame.url == server.PREFIX + "/frames/frame.html"

    navigations: List[str] = []
    page.on("framenavigated", lambda f: navigations.append(f.url))

    response = await frame.goto(server.CROSS_PROCESS_PREFIX + "/grid.html")
    await assert_oopif_count(browser, 1)
    assert response
    assert response.url == server.CROSS_PROCESS_PREFIX + "/grid.html"
    assert response.frame == frame
    assert frame.url == server.CROSS_PROCESS_PREFIX + "/grid.html"
    assert (
        await frame.evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )
    assert navigations == [server.CROSS_PROCESS_PREFIX + "/grid.html"]
    assert len(page.frames) == 2


async def test_OO_028_should_allow_to_re_connect_to_oopi_fs_with_cdp_when_iframes_were_there_already(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    browser_channel: Optional[str],
) -> None:
    if browser_channel:
        pytest.skip("Test default channel only")

    cdp_port = find_free_port()
    host_browser = await browser_type.launch(
        **{
            **launch_arguments,
            "channel": "chromium",
            "args": [f"--remote-debugging-port={cdp_port}"],
        }
    )
    host_page = await host_browser.new_page()
    await host_page.goto(server.PREFIX + "/dynamic-oopif.html")

    browser = await browser_type.connect_over_cdp(f"http://localhost:{cdp_port}")
    page = browser.contexts[0].pages[0]
    assert len(page.frames) == 2
    await assert_oopif_count(browser, 1)
    assert (
        await page.frames[1].evaluate("() => '' + location.href")
        == server.CROSS_PROCESS_PREFIX + "/grid.html"
    )
    await browser.close()
    await host_browser.close()


async def test_OO_029_should_report_the_whole_frame_tree_when_connecting_over_cdp_to_nested_oopi_fs(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    browser_channel: Optional[str],
) -> None:
    if browser_channel:
        pytest.skip("Test default channel only")

    # top > cross-site iframe (oopif) > same-process child iframe > sandboxed srcdoc iframe (oopif).
    def html_route(body: str) -> Callable[[TestServerRequest], None]:
        def handle(request: TestServerRequest) -> None:
            request.setHeader("Content-Type", "text/html")
            request.write(body.encode())
            request.finish()

        return handle

    server.set_route(
        "/nested-top.html",
        html_route(
            f'<h1 id=top>TOP</h1><iframe src="{server.CROSS_PROCESS_PREFIX}/nested-b.html"></iframe>'
        ),
    )
    server.set_route(
        "/nested-b.html", html_route('<iframe src="/nested-c.html"></iframe>')
    )
    server.set_route(
        "/nested-c.html",
        html_route('<iframe sandbox="allow-scripts" srcdoc="<p>D</p>"></iframe>'),
    )

    cdp_port = find_free_port()
    host_browser = await browser_type.launch(
        **{
            **launch_arguments,
            "channel": "chromium",
            "args": [
                f"--remote-debugging-port={cdp_port}",
                "--site-per-process",
                "--enable-features=IsolateSandboxedIframes",
            ],
        }
    )
    host_page = await host_browser.new_page()
    await host_page.goto(server.PREFIX + "/nested-top.html")

    browser = await browser_type.connect_over_cdp(f"http://localhost:{cdp_port}")
    await assert_oopif_count(browser, 2)
    page = browser.contexts[0].pages[0]

    expected_tree = [
        server.PREFIX + "/nested-top.html",
        "    " + server.CROSS_PROCESS_PREFIX + "/nested-b.html",
        "        " + server.CROSS_PROCESS_PREFIX + "/nested-c.html",
        "            about:srcdoc",
    ]

    async def dump_frames(frame: Frame, indent: str = "") -> List[str]:
        assert await frame.evaluate("() => '' + location.href") == frame.url
        result = [indent + frame.url]
        for child in frame.child_frames:
            result.extend(await dump_frames(child, indent + "    "))
        return result

    assert await dump_frames(page.main_frame) == expected_tree
    assert len(page.frames) == 4

    assert page.url == server.PREFIX + "/nested-top.html"
    assert await page.evaluate("() => window.top === window") is True
    await expect(page.locator("#top")).to_have_text("TOP")
    await expect(
        page.frame_locator("iframe")
        .frame_locator("iframe")
        .frame_locator("iframe")
        .locator("p")
    ).to_have_text("D")

    await browser.close()
    await host_browser.close()
