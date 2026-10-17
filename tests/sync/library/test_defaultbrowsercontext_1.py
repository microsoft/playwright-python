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

"""Port of tests/library/defaultbrowsercontext-1.spec.ts."""

import os
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import pytest

from playwright.sync_api import BrowserContext, Cookie, Error, Page
from tests.server import Server, TestServerRequest
from tests.utils import must

from ..utils import Utils

LaunchPersistent = Callable[..., Tuple[BrowserContext, Page]]


def maybe_filter_cookies(
    channel: Optional[str], cookies: Sequence[Cookie]
) -> List[Cookie]:
    if channel and channel.startswith("msedge"):
        return [c for c in cookies if not c["domain"].endswith("microsoft.com")]
    return list(cookies)


def test_DC_001_context_cookies_should_work_smoke(
    server: Server,
    launch_persistent: LaunchPersistent,
    default_same_site_cookie_value: str,
    browser_channel: Optional[str],
) -> None:
    _, page = launch_persistent()
    page.goto(server.EMPTY_PAGE)
    document_cookie = page.evaluate(
        """() => {
          document.cookie = 'username=John Doe';
          return document.cookie;
        }"""
    )
    assert document_cookie == "username=John Doe"
    assert maybe_filter_cookies(browser_channel, page.context.cookies()) == [
        {
            "name": "username",
            "value": "John Doe",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": default_same_site_cookie_value,
        }
    ]


def test_DC_002_context_add_cookies_should_work(
    server: Server,
    launch_persistent: LaunchPersistent,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    _, page = launch_persistent()
    page.goto(server.EMPTY_PAGE)
    page.context.add_cookies(
        [
            {
                "url": server.EMPTY_PAGE,
                "name": "username",
                "value": "John Doe",
                "sameSite": "Lax",
            }
        ]
    )
    assert page.evaluate("() => document.cookie") == "username=John Doe"
    assert maybe_filter_cookies(browser_channel, page.context.cookies()) == [
        {
            "name": "username",
            "value": "John Doe",
            "domain": server.HOSTNAME,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": (
                "None"
                if browser_name == "webkit"
                and is_win
                and browser_channel != "webkit-wsl"
                else "Lax"
            ),
        }
    ]


def test_DC_003_context_clear_cookies_should_work(
    server: Server,
    launch_persistent: LaunchPersistent,
    browser_channel: Optional[str],
) -> None:
    _, page = launch_persistent()
    page.goto(server.EMPTY_PAGE)
    page.context.add_cookies(
        [
            {"url": server.EMPTY_PAGE, "name": "cookie1", "value": "1"},
            {"url": server.EMPTY_PAGE, "name": "cookie2", "value": "2"},
        ]
    )
    assert page.evaluate("document.cookie") == "cookie1=1; cookie2=2"
    page.context.clear_cookies()
    page.reload()
    assert maybe_filter_cookies(browser_channel, page.context.cookies([])) == []
    assert page.evaluate("document.cookie") == ""


def test_DC_004_should_support_viewport_option(
    launch_persistent: LaunchPersistent, utils: Utils
) -> None:
    context, page = launch_persistent(viewport={"width": 456, "height": 789})
    utils.verify_viewport(page, 456, 789)
    page2 = context.new_page()
    utils.verify_viewport(page2, 456, 789)


def test_DC_005_should_support_device_scale_factor_option(
    launch_persistent: LaunchPersistent,
) -> None:
    _, page = launch_persistent(device_scale_factor=3)
    assert page.evaluate("window.devicePixelRatio") == 3


def test_DC_006_should_support_user_agent_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(user_agent="foobar")
    assert page.evaluate("() => navigator.userAgent") == "foobar"
    with server.expect_request("/empty.html") as request_info:
        page.goto(server.EMPTY_PAGE)
    assert request_info.value.getHeader("user-agent") == "foobar"


def test_DC_007_should_support_bypass_csp_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(bypass_csp=True)
    page.goto(server.PREFIX + "/csp.html")
    page.add_script_tag(content='window["__injected"] = 42;')
    assert page.evaluate("__injected") == 42
    assert page.evaluate('window["__inlineScriptValue"]') == 42


def test_DC_008_should_support_javascript_enabled_option(
    launch_persistent: LaunchPersistent, browser_name: str
) -> None:
    _, page = launch_persistent(java_script_enabled=False)
    page.goto('data:text/html, <script>var something = "forbidden"</script>')
    with pytest.raises(Error) as exc_info:
        page.evaluate("something")
    if browser_name == "webkit":
        assert "Can't find variable: something" in exc_info.value.message
    else:
        assert "something is not defined" in exc_info.value.message


def test_DC_009_should_support_http_credentials_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(
        http_credentials={"username": "user", "password": "pass"}
    )
    server.set_auth("/playground.html", "user", "pass")
    response = page.goto(server.PREFIX + "/playground.html")
    assert must(response).status == 200


def test_DC_010_should_support_offline_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent(offline=True)
    with pytest.raises(Error):
        page.goto(server.EMPTY_PAGE)


def test_DC_011_should_support_accept_downloads_option(
    server: Server, launch_persistent: LaunchPersistent
) -> None:
    _, page = launch_persistent()

    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/octet-stream")
        request.setHeader("Content-Disposition", "attachment")
        request.write(b"Hello world")
        request.finish()

    server.set_route("/download", handler)
    page.set_content(f'<a href="{server.PREFIX}/download">download</a>')
    with page.expect_download() as download_info:
        page.click("a")
    download = download_info.value
    path = download.path()
    assert os.path.exists(path)
    assert Path(path).read_text() == "Hello world"
