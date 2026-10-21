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
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from playwright.sync_api import (
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
from tests.utils import must, relative_path

from ..utils import Utils

LaunchPersistent = Callable[..., Tuple[BrowserContext, Page]]

# The JavaScript client sends a function engine as "(<function source>)()".
DEFAULT_CONTEXT_CSS = """(() => ({
  query(root, selector) {
    return root.querySelector(selector);
  },
  queryAll(root, selector) {
    return Array.from(root.querySelectorAll(selector));
  }
}))()"""


def test_DC_012_should_support_has_touch_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(has_touch=True)
    page.goto(server.PREFIX + "/mobile.html")
    assert page.evaluate("() => 'ontouchstart' in window") is True


def test_DC_013_should_work_in_persistent_context(
    server: Server, launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = launch_persistent(viewport={"width": 320, "height": 480}, is_mobile=True)
    page.goto(server.PREFIX + "/empty.html")
    assert page.evaluate("() => window.innerWidth") == 980


def test_DC_014_should_support_color_scheme_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = launch_persistent(color_scheme="dark")
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is False
    )
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )


def test_DC_015_should_support_reduced_motion_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = launch_persistent(reduced_motion="reduce")
    assert (
        page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        is True
    )
    assert (
        page.evaluate(
            "() => matchMedia('(prefers-reduced-motion: no-preference)').matches"
        )
        is False
    )


def test_DC_016_should_support_forced_colors_option(
    launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = launch_persistent(forced_colors="active")
    assert page.evaluate("() => matchMedia('(forced-colors: active)').matches") is True
    assert page.evaluate("() => matchMedia('(forced-colors: none)').matches") is False


def test_DC_017_should_support_contrast_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = launch_persistent(contrast="more")
    assert page.evaluate("() => matchMedia('(prefers-contrast: more)').matches") is True
    assert (
        page.evaluate("() => matchMedia('(prefers-contrast: no-preference)').matches")
        is False
    )


def test_DC_018_should_support_timezone_id_option(
    launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = launch_persistent(locale="en-US", timezone_id="America/Jamaica")
    assert (
        page.evaluate("() => new Date(1479579154987).toString()")
        == "Sat Nov 19 2016 13:12:34 GMT-0500 (Eastern Standard Time)"
    )


def test_DC_019_should_support_locale_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = launch_persistent(locale="fr-FR")
    assert page.evaluate("() => navigator.language") == "fr-FR"


def test_DC_020_should_support_geolocation_and_permissions_options(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(
        geolocation={"longitude": 10, "latitude": 10}, permissions=["geolocation"]
    )
    page.goto(server.EMPTY_PAGE)
    geolocation = page.evaluate(
        """() => new Promise(resolve => navigator.geolocation.getCurrentPosition(position => {
          resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude });
        }))"""
    )
    assert geolocation == {"latitude": 10, "longitude": 10}


def test_DC_021_should_support_ignore_https_errors_option(
    https_server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(ignore_https_errors=True)
    error: Optional[Error] = None
    response = None
    try:
        response = page.goto(https_server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error is None
    assert must(response).ok is True


def test_DC_022_should_support_extra_http_headers_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(extra_http_headers={"foo": "bar"})
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    assert request_info.value.getHeader("foo") == "bar"


def test_DC_023_should_accept_user_data_dir(
    create_user_data_dir: Callable[[], Path],
    browser_type: BrowserType,
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir()
    context = browser_type.launch_persistent_context(user_data_dir, **launch_arguments)
    assert len(os.listdir(user_data_dir)) > 0
    context.close()
    assert len(os.listdir(user_data_dir)) > 0


def test_DC_024_should_accept_relative_user_data_dir(
    create_user_data_dir: Callable[[], Path],
    browser_type: BrowserType,
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir()
    context = browser_type.launch_persistent_context(
        relative_path(user_data_dir / "foobar"), **launch_arguments
    )
    assert len(os.listdir(user_data_dir / "foobar")) > 0
    context.close()


@pytest.mark.slow
def test_DC_025_should_restore_state_from_user_data_dir(
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
    browser_context = browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    page = browser_context.new_page()
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => localStorage.hey = 'hello'")
    # Browsers do not persist local storage immediately, they do it asynchronously in another process.
    # Navigate away to give it a chance to save (best-effort).
    page.goto(server.EMPTY_PAGE)
    browser_context.close()

    browser_context2 = browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments
    )
    page2 = browser_context2.new_page()
    page2.goto(server.EMPTY_PAGE)
    assert page2.evaluate("() => localStorage.hey") == "hello"
    browser_context2.close()

    user_data_dir2 = create_user_data_dir()
    browser_context3 = browser_type.launch_persistent_context(
        user_data_dir2, **launch_arguments
    )
    page3 = browser_context3.new_page()
    page3.goto(server.EMPTY_PAGE)
    assert page3.evaluate("() => localStorage.hey") != "hello"
    browser_context3.close()


def test_DC_026_should_create_user_data_dir_if_it_does_not_exist(
    create_user_data_dir: Callable[[], Path],
    browser_type: BrowserType,
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir() / "nonexisting"
    context = browser_type.launch_persistent_context(user_data_dir, **launch_arguments)
    context.close()
    assert len(os.listdir(user_data_dir)) > 0


def test_DC_027_should_goto_about_blank_on_relaunched_persistent_context(
    browser_type: BrowserType,
    create_user_data_dir: Callable[[], Path],
    browser_name: str,
    launch_arguments: Dict,
) -> None:
    if browser_name == "firefox":
        pytest.skip("fixme")

    user_data_dir = create_user_data_dir()

    context1 = browser_type.launch_persistent_context(user_data_dir, **launch_arguments)
    context1.pages[0].goto("about:blank")
    context1.close()

    # When relaunching with an existing profile, Firefox session restore can race with the user's goto and cause "interrupted by another navigation".
    # This issue is timing-sensitive and might not fire on every run, so rely on CI's --repeat-each matrix for coverage.
    context2 = browser_type.launch_persistent_context(user_data_dir, **launch_arguments)
    context2.pages[0].goto("about:blank")
    assert context2.pages[0].url == "about:blank"
    context2.close()


def test_DC_028_should_have_default_url_when_launching_browser(
    launch_persistent: LaunchPersistent,
) -> None:
    context, _ = launch_persistent()
    urls = [page.url for page in context.pages]
    assert urls == ["about:blank"]


def test_DC_029_should_throw_if_page_argument_is_passed(
    browser_type: BrowserType,
    server: Server,
    create_user_data_dir: Callable[[], Path],
    browser_name: str,
    launch_arguments: Dict,
) -> None:
    if browser_name == "firefox":
        pytest.skip()

    with pytest.raises(Error) as exc_info:
        browser_type.launch_persistent_context(
            create_user_data_dir(), **launch_arguments, args=[server.EMPTY_PAGE]
        )
    assert "can not specify page" in exc_info.value.message


def test_DC_033_should_fire_close_event_for_a_persistent_context(
    launch_persistent: LaunchPersistent,
) -> None:
    context, _ = launch_persistent()
    closed: List[bool] = []
    context.on("close", lambda _: closed.append(True))
    context.close()
    assert closed == [True]


def test_DC_035_should_respect_selectors(
    playwright: Playwright, launch_persistent: LaunchPersistent, utils: Utils
) -> None:
    utils.register_selector_engine(
        playwright.selectors, "defaultContextCSS", DEFAULT_CONTEXT_CSS
    )

    _, page = launch_persistent()
    page.set_content("<div>hello</div>")
    assert page.inner_html("css=div") == "hello"
    assert page.inner_html("defaultContextCSS=div") == "hello"


def test_DC_037_should_support_har_option(
    launch_persistent: LaunchPersistent, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    _, page = launch_persistent()
    page.route_from_har(path)
    page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


def test_DC_038_user_agent_is_up_to_date(
    launch_persistent: LaunchPersistent, browser: Browser
) -> None:
    result = browser._sync(browser._impl_obj._channel.defaultUserAgentForTest())
    context, page = launch_persistent()
    assert page.evaluate("() => navigator.userAgent") == result["userAgent"]
    context.close()


def test_DC_039_dialog_accept_should_work(
    launch_persistent: LaunchPersistent,
) -> None:
    context, page = launch_persistent()
    page.goto(
        "data:text/html,<html><title>Title</title><button onclick=\"alert('Alert')\">Button</button></html>"
    )
    shown = False

    def on_dialog(dialog: Dialog) -> None:
        nonlocal shown
        shown = True
        dialog.accept()

    page.on("dialog", on_dialog)
    page.get_by_role("button", name="Button").click()
    assert shown is True
    context.close()


def test_DC_040_cache_storage_entry_should_survive_page_reload(
    launch_persistent: LaunchPersistent, server: Server
) -> None:
    context, page = launch_persistent()
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """async () => {
          const cache = await caches.open('repro-cache');
          await cache.put('/meta', new Response('payload'));
        }"""
    )

    page.reload()

    after = page.evaluate(
        """async () => {
          const cache = await caches.open('repro-cache');
          const resp = await cache.match('/meta');
          return resp ? await resp.text() : null;
        }"""
    )
    assert after == "payload"
    context.close()


def test_DC_041_exposes_browser(launch_persistent: LaunchPersistent) -> None:
    context, _ = launch_persistent()
    browser = must(context.browser)
    assert browser.version
    page = browser.new_page()
    page.goto("data:text/html,<html><title>Title</title></html>")
    assert page.title() == "Title"
    browser.close()
    assert len(context.pages) == 0
    # Next line should not throw.
    context.close()


def test_DC_042_should_support_storage_get_directory(
    launch_persistent: LaunchPersistent, server: Server
) -> None:
    context, _ = launch_persistent()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    name = page.evaluate(
        """async () => {
          const dir = await navigator.storage.getDirectory();
          return dir.name;
        }"""
    )
    assert name == ""
    context.close()
