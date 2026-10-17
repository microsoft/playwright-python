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

"""Port of tests/library/defaultbrowsercontext-2.spec.ts."""

import os
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

import pytest

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Dialog,
    Error,
    Page,
    Playwright,
    expect,
)
from tests.server import Server
from tests.utils import must

from ..utils import Utils

LaunchPersistent = Callable[..., Awaitable[Tuple[BrowserContext, Page]]]

# The JavaScript client sends a function engine as "(<function source>)()".
DEFAULT_CONTEXT_CSS = """(() => ({
  query(root, selector) {
    return root.querySelector(selector);
  },
  queryAll(root, selector) {
    return Array.from(root.querySelectorAll(selector));
  }
}))()"""


async def test_DC_012_should_support_has_touch_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = await launch_persistent(has_touch=True)
    await page.goto(server.PREFIX + "/mobile.html")
    assert await page.evaluate("() => 'ontouchstart' in window") is True


async def test_DC_013_should_work_in_persistent_context(
    server: Server, launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = await launch_persistent(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    await page.goto(server.PREFIX + "/empty.html")
    assert await page.evaluate("() => window.innerWidth") == 980


async def test_DC_014_should_support_color_scheme_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = await launch_persistent(color_scheme="dark")
    assert (
        await page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is False
    )
    assert (
        await page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )


async def test_DC_015_should_support_reduced_motion_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = await launch_persistent(reduced_motion="reduce")
    assert (
        await page.evaluate(
            "() => matchMedia('(prefers-reduced-motion: reduce)').matches"
        )
        is True
    )
    assert (
        await page.evaluate(
            "() => matchMedia('(prefers-reduced-motion: no-preference)').matches"
        )
        is False
    )


async def test_DC_016_should_support_forced_colors_option(
    launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = await launch_persistent(forced_colors="active")
    assert (
        await page.evaluate("() => matchMedia('(forced-colors: active)').matches")
        is True
    )
    assert (
        await page.evaluate("() => matchMedia('(forced-colors: none)').matches")
        is False
    )


async def test_DC_017_should_support_contrast_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = await launch_persistent(contrast="more")
    assert (
        await page.evaluate("() => matchMedia('(prefers-contrast: more)').matches")
        is True
    )
    assert (
        await page.evaluate(
            "() => matchMedia('(prefers-contrast: no-preference)').matches"
        )
        is False
    )


async def test_DC_018_should_support_timezone_id_option(
    launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = await launch_persistent(locale="en-US", timezone_id="America/Jamaica")
    assert (
        await page.evaluate("() => new Date(1479579154987).toString()")
        == "Sat Nov 19 2016 13:12:34 GMT-0500 (Eastern Standard Time)"
    )


async def test_DC_019_should_support_locale_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = await launch_persistent(locale="fr-FR")
    assert await page.evaluate("() => navigator.language") == "fr-FR"


async def test_DC_020_should_support_geolocation_and_permissions_options(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = await launch_persistent(
        geolocation={"longitude": 10, "latitude": 10}, permissions=["geolocation"]
    )
    await page.goto(server.EMPTY_PAGE)
    geolocation = await page.evaluate(
        """() => new Promise(resolve => navigator.geolocation.getCurrentPosition(position => {
          resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude });
        }))"""
    )
    assert geolocation == {"latitude": 10, "longitude": 10}


async def test_DC_021_should_support_ignore_https_errors_option(
    https_server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = await launch_persistent(ignore_https_errors=True)
    error: Optional[Error] = None
    response = None
    try:
        response = await page.goto(https_server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is None
    assert must(response).ok is True


async def test_DC_022_should_support_extra_http_headers_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = await launch_persistent(extra_http_headers={"foo": "bar"})
    with server.expect_request("/empty.html") as request_info:
        await page.goto(server.EMPTY_PAGE)
    assert request_info.value.getHeader("foo") == "bar"


async def test_DC_023_should_accept_user_data_dir(
    create_user_data_dir: Callable[[], Path],
    browser_type: BrowserType,
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir()
    context = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    assert len(os.listdir(user_data_dir)) > 0
    await context.close()
    assert len(os.listdir(user_data_dir)) > 0


async def test_DC_024_should_accept_relative_user_data_dir(
    create_user_data_dir: Callable[[], Path],
    browser_type: BrowserType,
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir()
    context = await browser_type.launch_persistent_context(
        os.path.relpath(user_data_dir / "foobar", os.getcwd()), **launch_arguments
    )
    assert len(os.listdir(user_data_dir / "foobar")) > 0
    await context.close()


async def test_DC_025_should_restore_state_from_user_data_dir(
    browser_type: BrowserType,
    server: Server,
    create_user_data_dir: Callable[[], Path],
    browser_channel: Optional[str],
    launch_arguments: Dict,
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip(
            "fixme: Pending local storage writes are lost on close, see https://github.com/microsoft/playwright-browsers/issues/2275"
        )

    user_data_dir = create_user_data_dir()
    browser_context = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    page = await browser_context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => localStorage.hey = 'hello'")
    # Browsers do not persist local storage immediately, they do it asynchronously in another process.
    # Navigate away to give it a chance to save (best-effort).
    await page.goto(server.EMPTY_PAGE)
    await browser_context.close()

    browser_context2 = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    page2 = await browser_context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await page2.evaluate("() => localStorage.hey") == "hello"
    await browser_context2.close()

    user_data_dir2 = create_user_data_dir()
    browser_context3 = await browser_type.launch_persistent_context(
        user_data_dir2, **launch_arguments
    )
    page3 = await browser_context3.new_page()
    await page3.goto(server.EMPTY_PAGE)
    assert await page3.evaluate("() => localStorage.hey") != "hello"
    await browser_context3.close()


async def test_DC_026_should_create_user_data_dir_if_it_does_not_exist(
    create_user_data_dir: Callable[[], Path],
    browser_type: BrowserType,
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir() / "nonexisting"
    context = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    await context.close()
    assert len(os.listdir(user_data_dir)) > 0


async def test_DC_027_should_goto_about_blank_on_relaunched_persistent_context(
    browser_type: BrowserType,
    create_user_data_dir: Callable[[], Path],
    browser_name: str,
    launch_arguments: Dict,
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme")

    user_data_dir = create_user_data_dir()

    context1 = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    await context1.pages[0].goto("about:blank")
    await context1.close()

    # When relaunching with an existing profile, Firefox session restore can race with the user's goto and cause "interrupted by another navigation".
    # This issue is timing-sensitive and might not fire on every run, so rely on CI's --repeat-each matrix for coverage.
    context2 = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    await context2.pages[0].goto("about:blank")
    assert context2.pages[0].url == "about:blank"
    await context2.close()


async def test_DC_028_should_have_default_url_when_launching_browser(
    launch_persistent: LaunchPersistent,
) -> None:
    context, _ = await launch_persistent()
    urls = [page.url for page in context.pages]
    assert urls == ["about:blank"]


async def test_DC_029_should_throw_if_page_argument_is_passed(
    browser_type: BrowserType,
    server: Server,
    create_user_data_dir: Callable[[], Path],
    browser_name: str,
    launch_arguments: Dict,
) -> None:
    if browser_name == "firefox":
        pytest.skip()

    with pytest.raises(Error) as exc_info:
        await browser_type.launch_persistent_context(
            create_user_data_dir(), **launch_arguments, args=[server.EMPTY_PAGE]
        )
    assert "can not specify page" in exc_info.value.message


async def test_DC_033_should_fire_close_event_for_a_persistent_context(
    launch_persistent: LaunchPersistent,
) -> None:
    context, _ = await launch_persistent()
    closed: List[bool] = []
    context.on("close", lambda _: closed.append(True))
    await context.close()
    assert closed == [True]


async def test_DC_035_should_respect_selectors(
    playwright: Playwright, launch_persistent: LaunchPersistent, utils: Utils
) -> None:
    await utils.register_selector_engine(
        playwright.selectors, "defaultContextCSS", DEFAULT_CONTEXT_CSS
    )

    _, page = await launch_persistent()
    await page.set_content("<div>hello</div>")
    assert await page.inner_html("css=div") == "hello"
    assert await page.inner_html("defaultContextCSS=div") == "hello"


async def test_DC_037_should_support_har_option(
    launch_persistent: LaunchPersistent, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    _, page = await launch_persistent()
    await page.route_from_har(path)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_DC_038_user_agent_is_up_to_date(
    launch_persistent: LaunchPersistent, browser: Browser
) -> None:
    result = await browser._impl_obj._channel.defaultUserAgentForTest()
    context, page = await launch_persistent()
    assert await page.evaluate("() => navigator.userAgent") == result["userAgent"]
    await context.close()


async def test_DC_039_dialog_accept_should_work(
    launch_persistent: LaunchPersistent,
) -> None:
    context, page = await launch_persistent()
    await page.goto(
        "data:text/html,<html><title>Title</title><button onclick=\"alert('Alert')\">Button</button></html>"
    )
    shown = False

    async def on_dialog(dialog: Dialog) -> None:
        nonlocal shown
        shown = True
        await dialog.accept()

    page.on("dialog", on_dialog)
    await page.get_by_role("button", name="Button").click()
    assert shown is True
    await context.close()


async def test_DC_040_cache_storage_entry_should_survive_page_reload(
    launch_persistent: LaunchPersistent, server: Server
) -> None:
    context, page = await launch_persistent()
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
          const cache = await caches.open('repro-cache');
          await cache.put('/meta', new Response('payload'));
        }"""
    )

    await page.reload()

    after = await page.evaluate(
        """async () => {
          const cache = await caches.open('repro-cache');
          const resp = await cache.match('/meta');
          return resp ? await resp.text() : null;
        }"""
    )
    assert after == "payload"
    await context.close()


async def test_DC_041_exposes_browser(launch_persistent: LaunchPersistent) -> None:
    context, _ = await launch_persistent()
    browser = must(context.browser)
    assert browser.version
    page = await browser.new_page()
    await page.goto("data:text/html,<html><title>Title</title></html>")
    assert await page.title() == "Title"
    await browser.close()
    assert len(context.pages) == 0
    # Next line should not throw.
    await context.close()


async def test_DC_042_should_support_storage_get_directory(
    launch_persistent: LaunchPersistent, server: Server
) -> None:
    context, _ = await launch_persistent()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    name = await page.evaluate(
        """async () => {
          const dir = await navigator.storage.getDirectory();
          return dir.name;
        }"""
    )
    assert name == ""
    await context.close()
