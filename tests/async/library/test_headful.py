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

"""Port of tests/library/headful.spec.ts.

Upstream runs this file only in its headed test runs. Here the browser, the context,
the page and launch_persistent of this module are always headed, and the tests skip
when there is no display.
"""

import asyncio
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

import pytest

from playwright.async_api import Browser, BrowserContext, BrowserType, Error, Page
from tests.helpers.image_compare import count_different_pixels
from tests.server import Server, TestServerRequest


@pytest.fixture(scope="module", autouse=True)
def headed_launch_arguments(
    launch_arguments: Dict, browser_channel: Optional[str]
) -> Dict:
    """The launch arguments of the run, headed."""
    if browser_channel == "chromium-headless-shell":
        pytest.skip("shell is never headed")
    return {**launch_arguments, "headless": False}


@pytest.fixture(scope="module")
async def headed_browser(
    browser_type: BrowserType, headed_launch_arguments: Dict
) -> AsyncGenerator[Dict[str, Browser], None]:
    """The headed browser of the module, launched by the browser fixture."""
    holder: Dict[str, Browser] = {}
    yield holder
    if "browser" in holder:
        await holder["browser"].close()


@pytest.fixture
async def browser(
    browser_type: BrowserType,
    headed_launch_arguments: Dict,
    headed_browser: Dict[str, Browser],
) -> Browser:
    # Launch it again when it crashed, so that a rerun does not get the dead browser:
    # Playwright Test starts a new worker after a failure.
    if "browser" not in headed_browser or not headed_browser["browser"].is_connected():
        headed_browser["browser"] = await browser_type.launch(**headed_launch_arguments)
    return headed_browser["browser"]


@pytest.fixture(autouse=True)
async def close_leaked_contexts(
    headed_browser: Dict[str, Browser],
) -> AsyncGenerator[None, None]:
    # The cleanup of the conftest, for the headed browser of this module.
    yield
    if "browser" not in headed_browser:
        return
    for context in headed_browser["browser"].contexts:
        try:
            await context.close()
        except Error:
            pass


@pytest.fixture
async def launch_persistent(
    browser_type: BrowserType,
    headed_launch_arguments: Dict,
    create_user_data_dir: Callable[[], Path],
) -> AsyncGenerator[Callable[..., Awaitable[Tuple[BrowserContext, Page]]], None]:
    contexts: List[BrowserContext] = []

    async def launch(**kwargs: Any) -> Tuple[BrowserContext, Page]:
        if contexts:
            raise Exception("can only launch one persistent context")
        context = await browser_type.launch_persistent_context(
            create_user_data_dir(), **{**headed_launch_arguments, **kwargs}
        )
        contexts.append(context)
        return context, context.pages[0]

    yield launch
    for context in contexts:
        await context.close()


LaunchPersistent = Callable[..., Awaitable[Tuple[BrowserContext, Page]]]


async def test_HE_001_should_have_default_url_when_launching_browser_smoke(
    launch_persistent: LaunchPersistent,
) -> None:
    context, _ = await launch_persistent()
    urls = [page.url for page in context.pages]
    assert urls == ["about:blank"]


async def test_HE_002_should_close_browser_with_beforeunload_page(
    launch_persistent: LaunchPersistent, server: Server
) -> None:
    context, _ = await launch_persistent()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    await context.close()


async def test_HE_003_should_close_browsercontext_with_pending_beforeunload_dialog(
    server: Server, context: BrowserContext
) -> None:
    page = await context.new_page()
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    async with page.expect_event("dialog"):
        await page.close(run_before_unload=True)
    await context.close()


async def test_HE_004_should_not_crash_when_creating_second_context(
    browser: Browser,
) -> None:
    browser_context = await browser.new_context()
    await browser_context.new_page()
    await browser_context.close()

    browser_context = await browser.new_context()
    await browser_context.new_page()
    await browser_context.close()


async def test_HE_005_should_click_when_viewport_size_is_larger_than_screen(
    page: Page,
) -> None:
    await page.set_viewport_size(
        {
            "width": 3000,
            "height": 3000,
        }
    )
    await page.set_content(
        """
    <style>
      html, body { position: absolute; left: 0; top: 0; right: 0; bottom: 0; }
    </style>
    <button style="position: absolute; right: 0; bottom: 0;">Button in the bottom-right corner</button>
  """
    )
    await page.locator("button").click()


async def test_HE_006_should_dispatch_click_events_to_oversized_viewports(
    page: Page,
) -> None:
    # Some prime numbers for width/height.
    width = 2971
    height = 3067
    await page.set_viewport_size({"width": width, "height": height})
    await page.evaluate(
        """() => {
      window['events'] = [];
      window.addEventListener('click', event => window['events'].push({ x: event.clientX, y: event.clientY }), false);
    }"""
    )
    expected_events = []
    # Allow a little padding from the edges of viewport.
    for i in range(3, 23):
        x = width - i
        y = height - i
        expected_events.append({"x": x, "y": y})
        await page.mouse.move(x, y)
        await page.mouse.down()
        await page.mouse.up()
    actual_events = await page.evaluate("() => window['events']")
    assert expected_events == actual_events


async def test_HE_007_should_click_background_tab(page: Page, server: Server) -> None:
    await page.set_content(
        f'<button>Hello</button><a target=_blank href="{server.EMPTY_PAGE}">empty.html</a>'
    )
    await page.click("a")
    await page.click("button")


async def test_HE_008_should_close_browser_after_context_menu_was_triggered(
    browser_type: BrowserType, headed_launch_arguments: Dict, server: Server
) -> None:
    browser = await browser_type.launch(**headed_launch_arguments)
    page = await browser.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await page.click("body", button="right")
    await browser.close()


async def test_HE_009_should_not_block_third_party_cookies(
    page: Page,
    server: Server,
    allows_third_party: bool,
    default_same_site_cookie_value: str,
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """src => {
      let fulfill;
      const promise = new Promise(x => fulfill = x);
      const iframe = document.createElement('iframe');
      document.body.appendChild(iframe);
      iframe.onload = fulfill;
      iframe.src = src;
      return promise;
    }""",
        server.CROSS_PROCESS_PREFIX + "/grid.html",
    )
    document_cookie = await page.frames[1].evaluate(
        """() => {
      document.cookie = 'username=John Doe';
      return document.cookie;
    }"""
    )
    await page.wait_for_timeout(2000)
    assert document_cookie == ("username=John Doe" if allows_third_party else "")
    cookies = await page.context.cookies(server.CROSS_PROCESS_PREFIX + "/grid.html")
    if allows_third_party:
        assert cookies == [
            {
                "domain": "127.0.0.1",
                "expires": -1,
                "httpOnly": False,
                "name": "username",
                "path": "/",
                "sameSite": default_same_site_cookie_value,
                "secure": False,
                "value": "John Doe",
            }
        ]
    else:
        assert cookies == []


async def test_HE_010_should_not_block_third_party_same_site_none_cookies(
    https_server: Server, browser_name: str, browser: Browser
) -> None:
    if browser_name == "webkit":
        pytest.skip("No third party cookies in WebKit")
    page = await browser.new_page(
        ignore_https_errors=True,
    )

    def handle_empty(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            f'<iframe src="{https_server.CROSS_PROCESS_PREFIX}/grid.html"></iframe>'.encode()
        )
        request.finish()

    def handle_grid(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader(
            "Set-Cookie", "a=b; Path=/; Max-Age=3600; SameSite=None; Secure"
        )
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""Hello world
    <script>
    setTimeout(() => fetch('/json'), 1000);
    </script>"""
        )
        request.finish()

    cookies: List[Optional[str]] = []

    def handle_json(request: TestServerRequest) -> None:
        cookies.append(request.getHeader("cookie"))
        request.finish()

    https_server.set_route("/empty.html", handle_empty)
    https_server.set_route("/grid.html", handle_grid)
    https_server.set_route("/json", handle_json)

    await page.goto(https_server.EMPTY_PAGE)
    # Port of `await cookie`: wait until the server gets /json.
    while not cookies:
        await asyncio.sleep(0.05)
    assert cookies[0] == "a=b"
    await page.close()


async def test_HE_011_should_not_override_viewport_size_when_passed_null(
    browser_name: str, server: Server, browser: Browser
) -> None:
    if browser_name == "webkit":
        pytest.skip("Our WebKit embedder does not respect window features")

    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            """() => {
        const win = window.open(window.location.href, 'Title', 'toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=600,height=300,top=0,left=0');
        win.resizeTo(500, 450);
      }"""
        )
    popup = await popup_info.value
    await popup.wait_for_load_state()
    await popup.wait_for_function(
        "() => window.outerWidth === 500 && window.outerHeight === 450"
    )
    await context.close()


async def test_HE_012_page_bring_to_front_should_work(browser: Browser) -> None:
    page1 = await browser.new_page()
    await page1.set_content("Page1")
    page2 = await browser.new_page()
    await page2.set_content("Page2")

    await page1.bring_to_front()
    assert await page1.evaluate("document.visibilityState") == "visible"
    assert await page2.evaluate("document.visibilityState") == "visible"

    await page2.bring_to_front()
    assert await page1.evaluate("document.visibilityState") == "visible"
    assert await page2.evaluate("document.visibilityState") == "visible"

    await page1.close()
    await page2.close()


async def test_HE_013_should_click_in_oopif(
    browser_name: str, launch_persistent: LaunchPersistent, server: Server
) -> None:
    def handle_empty(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            f'<iframe src="{server.CROSS_PROCESS_PREFIX}/iframe.html"></iframe>'.encode()
        )
        request.finish()

    def handle_iframe(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""<button id="button" onclick="console.log('ok')">Submit</button>
    <script>console.log('frame loaded')</script>"""
        )
        request.finish()

    server.set_route("/empty.html", handle_empty)
    server.set_route("/iframe.html", handle_iframe)

    _, page = await launch_persistent()
    console_log: List[str] = []
    page.on("console", lambda m: console_log.append(m.text))
    await page.goto(server.EMPTY_PAGE)
    await page.frames[1].click("text=Submit")
    assert "ok" in console_log


async def test_HE_014_should_click_bottom_row_w_infobar_in_oopif(
    browser_name: str, launch_persistent: LaunchPersistent, server: Server
) -> None:
    def handle_empty(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            f"""
      <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
        iframe {{ position: absolute; bottom: 0; }}
      </style>
      <iframe src="{server.CROSS_PROCESS_PREFIX}/iframe.html"></iframe>
    """.encode()
        )
        request.finish()

    def handle_iframe(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""
      <style>
        html, body { margin: 0; padding: 0; width: 100%; height: 100%; }
        button { position: absolute; bottom: 0; }
      </style>
      <button id="button" onclick="window._clicked=true">Submit</button>"""
        )
        request.finish()

    server.set_route("/empty.html", handle_empty)
    server.set_route("/iframe.html", handle_iframe)

    _, page = await launch_persistent()
    await page.goto(server.EMPTY_PAGE)
    if browser_name == "chromium":
        # CHROME BUG:
        #   Unfortunately, on some platforms the automation infobar is shown up late or animates in.
        #   Upon showing, it triggers a resize of WebContentsView and RenderWidgetHostView
        #   through the native view hierarchy. This in turn resizes the compositor to the visible view size
        #   instead of the emulated size specified in Emulation.setDeviceMetricsOverride.
        #   Hit testing for OOPIFs is affected by the new size, and clicks do not reach the iframe.
        #
        #   The workaround is to re-apply the viewport after a delay, in this case after the navigation.
        await page.set_viewport_size({"width": 800, "height": 600})
    await page.frames[1].click("text=Submit")
    assert await page.frames[1].evaluate("window._clicked") is True


FONTS_CONTENT = """<div style="font: 15px bold __FAMILY__; max-width: 300px; max-height: 300px; overflow: hidden">
      Lorem ipsum dolor sit amet consectetur adipiscing elit proin, integer curabitur imperdiet rhoncus cursus tincidunt bibendum, consequat sed magnis laoreet luctus mollis tellus. Nisl parturient mus accumsan feugiat sem laoreet magnis nisi, aptent per sollicitudin gravida orci ac blandit, viverra eros praesent auctor vivamus semper bibendum. Consequat sed habitasse luctus dictumst gravida platea semper phasellus, nascetur ridiculus purus est varius quisque et scelerisque, id vehicula eleifend montes sollicitudin dis velit. Pellentesque ridiculus per natoque et eleifend taciti nunc, laoreet auctor at condimentum imperdiet ante, conubia mi cubilia scelerisque sociosqu sem.</p> <p>Curabitur magna per felis primis mauris non dapibus luctus ultricies eros, quis et egestas condimentum lobortis eget semper montes litora purus, ridiculus elementum sollicitudin imperdiet dictum lacinia parturient cras eu. Risus cum varius rhoncus eros torquent pretium taciti id erat dis egestas, nibh tristique montes convallis metus lacus phasellus blandit ut auctor bibendum semper, facilisis mi integer eget ultrices lobortis odio viverra duis dui. Risus ullamcorper lacinia in venenatis sodales fusce tortor potenti volutpat quis, dictum vulputate suspendisse velit mollis torquent sociis aptent morbi, senectus nascetur justo maecenas conubia magnis viverra gravida fames. Phasellus sed nec gravida nibh class augue lectus, blandit quis turpis orci diam nam pellentesque, ultricies metus imperdiet hendrerit lacinia lacus.</p> <p>Inceptos facilisi montes cum hendrerit, pulvinar ut tellus eget velit, arcu nulla aenean. Phasellus augue urna nostra molestie interdum vehicula, posuere fames cum euismod massa curabitur donec, inceptos cubilia tellus facilisis fermentum. Lacus laoreet facilisis ultrices cursus quisque at ad porta vestibulum massa inceptos, curae class aliquet maecenas cum ullamcorper pulvinar erat mus vitae. Cum in aenean convallis dis quam tincidunt justo sed quisque, imperdiet faucibus hendrerit felis commodo scelerisque magnis vehicula etiam leo, eros varius platea lobortis maecenas condimentum nisi phasellus. Turpis vulputate mus himenaeos sociosqu facilisis dignissim leo quam, ultricies habitasse commodo molestie est tortor vitae et, porttitor risus erat cursus phasellus facilisi litora.</p> <p>Nostra habitasse egestas magnis velit pellentesque parturient cum lectus viverra, vestibulum sociosqu nunc vel urna consequat lacinia phasellus at sapien, aenean pretium dictum sed montes interdum imperdiet iaculis. Leo hac eros arcu senectus maecenas, tortor pulvinar venenatis lacinia volutpat, mattis platea ut facilisi. Aenean condimentum at et donec sociosqu fermentum luctus potenti semper vulputate, sapien justo non est auctor gravida ultricies fames per commodo, sed habitasse facilisi nulla quisque hendrerit aliquet viverra bibendum.</p> <p>Interdum nisl quam etiam montes porttitor laoreet nullam senectus velit, mauris proin tellus imperdiet litora venenatis fames massa quis, sollicitudin justo vivamus curae in sociis suscipit facilisi. Platea inceptos lacus elementum pellentesque quam euismod dictumst sociis tincidunt vulputate porttitor eros, turpis netus ut ad tempor sapien aliquet sodales molestie consequat nostra. Cum augue in quisque primis ut nunc sodales, sem orci tempus posuere cubilia suspendisse lacinia ligula, magna sed ridiculus at maecenas habitant.</p> <p>Natoque magna ac feugiat tellus bibendum diam, metus lobortis nisl ornare varius praesent, dictumst gravida lacus parturient semper. Pellentesque faucibus congue fusce posuere placerat dictum vitae, dui vestibulum eu sociis tempus aliquam ultricies malesuada, potenti laoreet lacus sem gravida nisi. Nostra platea sagittis hendrerit congue conubia senectus bibendum quis sapien pharetra, scelerisque nam imperdiet fermentum feugiat suspendisse viverra luctus at, semper ac consequat vitae mi gravida parturient mollis nascetur. Vel taciti justo consequat primis et blandit convallis sed, felis purus fusce a venenatis etiam aenean scelerisque, fringilla volutpat sagittis egestas rutrum id dis.</p> <p>Feugiat fermentum tortor ante ac iaculis sollicitudin ut interdum, cras orci ullamcorper potenti tristique vehicula. Molestie tortor ullamcorper rutrum turpis malesuada phasellus sem ultricies praesent mattis lobortis porta, senectus venenatis diam nostra laoreet volutpat per aptent justo elementum cum. Urna cursus vel felis cras eleifend arcu enim magnis, duis rutrum nibh nascetur cubilia interdum ultrices curae, id lacus aliquam dictumst diam fringilla lacinia.</p> <p>Luctus diam morbi eget tellus libero taciti faucibus inceptos, natoque facilisis lectus maecenas risus dapibus suscipit nibh, vel curae conubia orci imperdiet metus fusce. Condimentum massa donec luctus pharetra cum, in viverra placerat nisl litora facilisis, neque nascetur sociis dictumst. Suscipit accumsan eget rhoncus pharetra justo malesuada aliquet, suspendisse metus eleifend tincidunt varius ridiculus, convallis primis vitae curabitur quis mus.</p> <p>Gravida donec lacus molestie tortor aenean ultricies blandit per tempor, nostra penatibus orci vestibulum semper lectus vel a, montes potenti cum dapibus natoque eu volutpat nulla. Himenaeos purus nam malesuada habitasse nisl pharetra laoreet feugiat mi non, ultrices ultricies a cras ante eu venenatis ligula. Suscipit ut mus habitasse at aliquet sodales commodo justo, feugiat platea sagittis phasellus eleifend pellentesque interdum iaculis, integer cubilia montes metus hendrerit tincidunt purus.</p> <p>Vel posuere tellus dapibus eget duis cubilia, nec class vehicula libero gravida ligula, tempus urna taciti donec congue. Facilisis ridiculus congue cum dui per augue natoque, molestie hac etiam pellentesque dignissim urna class, feugiat aenean massa himenaeos penatibus ut eu, convallis purus et fusce tempus mattis. At mattis suscipit porta nostra nec facilisis sodales turpis, integer et lectus conubia justo nam congue taciti odio, fermentum semper cubilia fusce nunc purus velit.
      <div/>
    """


async def test_HE_015_headless_and_headful_should_use_same_default_fonts(
    page: Page,
    browser_name: str,
    browser_type: BrowserType,
    headed_launch_arguments: Dict,
) -> None:
    if browser_name == "firefox":
        pytest.skip("Text is misaligned in headed vs headless")

    generic_font_families = [
        "standard",
        "serif",
        "sans-serif",
        "monospace",
        "cursive",
        "fantasy",
        "emoji",
    ]
    headless_browser = await browser_type.launch(
        **{**headed_launch_arguments, "headless": True}
    )
    headless_page = await headless_browser.new_page()
    for family in generic_font_families:
        content = FONTS_CONTENT.replace(
            "__FAMILY__", "" if family == "standard" else family
        )
        await asyncio.gather(
            page.set_content(content), headless_page.set_content(content)
        )
        image1, image2 = await asyncio.gather(
            page.screenshot(), headless_page.screenshot()
        )
        # Port of utils.compare(image1, image2), which counts the different pixels.
        count = count_different_pixels(image1, image2, threshold=0.1)
        assert count == 0
    await headless_browser.close()


async def test_HE_016_should_have_the_same_hyphen_rendering_on_headless_and_headed(
    browser_type: BrowserType,
    page: Page,
    headed_launch_arguments: Dict,
    server: Server,
) -> None:
    content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <style>
        .hyphenated {
          width: 100px;
          hyphens: auto;
          text-align: justify;
          border: 1px solid black;
        }
      </style>
    </head>
    <body>
      <div class="hyphenated">
        supercalifragilisticexpialidocious
      </div>
    </body>
    </html>
  """

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(content.encode())
        request.finish()

    server.set_route("/hyphenated.html", handle)
    headless = headed_launch_arguments["headless"]
    opposite_browser = await browser_type.launch(
        **{**headed_launch_arguments, "headless": not headless}
    )
    opposite_page = await opposite_browser.new_page()
    await opposite_page.goto(server.PREFIX + "/hyphenated.html")
    await page.goto(server.PREFIX + "/hyphenated.html")

    div_height1, div_height2 = await asyncio.gather(
        page.evaluate(
            "() => document.querySelector('.hyphenated').getBoundingClientRect().height"
        ),
        opposite_page.evaluate(
            "() => document.querySelector('.hyphenated').getBoundingClientRect().height"
        ),
    )
    assert div_height1 == div_height2
    await opposite_browser.close()
