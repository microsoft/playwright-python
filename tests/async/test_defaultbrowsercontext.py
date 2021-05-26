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

import asyncio
import os

import pytest

from playwright._impl._api_types import Error


@pytest.fixture()
async def launch_persistent(tmpdir, launch_arguments, browser_type):
    context = None

    async def _launch(**options):
        nonlocal context
        if context:
            raise ValueError("can only launch one persitent context")
        context = await browser_type.launch_persistent_context(
            str(tmpdir), **{**launch_arguments, **options}
        )
        return (context.pages[0], context)

    yield _launch
    await context.close()


async def test_context_cookies_should_work(server, launch_persistent, is_firefox):
    (page, context) = await launch_persistent()
    await page.goto(server.EMPTY_PAGE)
    document_cookie = await page.evaluate(
        """() => {
    document.cookie = 'username=John Doe';
    return document.cookie;
  }"""
    )

    assert document_cookie == "username=John Doe"
    assert await page.context.cookies() == [
        {
            "name": "username",
            "value": "John Doe",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "None",
        }
    ]


async def test_context_add_cookies_should_work(server, launch_persistent):
    (page, context) = await launch_persistent()
    await page.goto(server.EMPTY_PAGE)
    await page.context.add_cookies(
        [{"url": server.EMPTY_PAGE, "name": "username", "value": "John Doe"}]
    )
    assert await page.evaluate("() => document.cookie") == "username=John Doe"
    assert await page.context.cookies() == [
        {
            "name": "username",
            "value": "John Doe",
            "domain": "localhost",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": False,
            "sameSite": "None",
        }
    ]


async def test_context_clear_cookies_should_work(server, launch_persistent):
    (page, context) = await launch_persistent()
    await page.goto(server.EMPTY_PAGE)
    await page.context.add_cookies(
        [
            {"url": server.EMPTY_PAGE, "name": "cookie1", "value": "1"},
            {"url": server.EMPTY_PAGE, "name": "cookie2", "value": "2"},
        ]
    )
    assert await page.evaluate("document.cookie") == "cookie1=1; cookie2=2"
    await page.context.clear_cookies()
    await page.reload()
    assert await page.context.cookies([]) == []
    assert await page.evaluate("document.cookie") == ""


async def test_should_not_block_third_party_cookies(
    server, launch_persistent, is_chromium, is_firefox
):
    (page, context) = await launch_persistent()
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
    allows_third_party = is_chromium or is_firefox
    assert document_cookie == ("username=John Doe" if allows_third_party else "")
    cookies = await context.cookies(server.CROSS_PROCESS_PREFIX + "/grid.html")
    if allows_third_party:
        assert cookies == [
            {
                "domain": "127.0.0.1",
                "expires": -1,
                "httpOnly": False,
                "name": "username",
                "path": "/",
                "sameSite": "None",
                "secure": False,
                "value": "John Doe",
            }
        ]
    else:
        assert cookies == []


async def test_should_support_viewport_option(launch_persistent, utils):
    (page, context) = await launch_persistent(viewport={"width": 456, "height": 789})
    await utils.verify_viewport(page, 456, 789)
    page2 = await context.new_page()
    await utils.verify_viewport(page2, 456, 789)


async def test_should_support_device_scale_factor_option(launch_persistent, utils):
    (page, context) = await launch_persistent(device_scale_factor=3)
    assert await page.evaluate("window.devicePixelRatio") == 3


async def test_should_support_user_agent_option(launch_persistent, server):
    (page, context) = await launch_persistent(user_agent="foobar")
    assert await page.evaluate("() => navigator.userAgent") == "foobar"
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        page.goto(server.EMPTY_PAGE),
    )
    assert request.getHeader("user-agent") == "foobar"


async def test_should_support_bypass_csp_option(launch_persistent, server):
    (page, context) = await launch_persistent(bypass_csp=True)
    await page.goto(server.PREFIX + "/csp.html")
    await page.add_script_tag(content="window.__injected = 42;")
    assert await page.evaluate("() => window.__injected") == 42


async def test_should_support_javascript_enabled_option(launch_persistent, is_webkit):
    (page, context) = await launch_persistent(java_script_enabled=False)
    await page.goto('data:text/html, <script>var something = "forbidden"</script>')
    with pytest.raises(Error) as exc:
        await page.evaluate("something")
    if is_webkit:
        assert "Can't find variable: something" in exc.value.message
    else:
        assert "something is not defined" in exc.value.message


async def test_should_support_http_credentials_option(server, launch_persistent):
    (page, context) = await launch_persistent(
        http_credentials={"username": "user", "password": "pass"}
    )
    server.set_auth("/playground.html", b"user", b"pass")
    response = await page.goto(server.PREFIX + "/playground.html")
    assert response.status == 200


async def test_should_support_offline_option(server, launch_persistent):
    (page, context) = await launch_persistent(offline=True)
    with pytest.raises(Error):
        await page.goto(server.EMPTY_PAGE)


async def test_should_support_has_touch_option(server, launch_persistent):
    (page, context) = await launch_persistent(has_touch=True)
    await page.goto(server.PREFIX + "/mobile.html")
    assert await page.evaluate('() => "ontouchstart" in window')


@pytest.mark.skip_browser("firefox")
async def test_should_work_in_persistent_context(server, launch_persistent):
    # Firefox does not support mobile.
    (page, context) = await launch_persistent(
        viewport={"width": 320, "height": 480}, is_mobile=True
    )
    await page.goto(server.PREFIX + "/empty.html")
    assert await page.evaluate("() => window.innerWidth") == 980


async def test_should_support_color_scheme_option(server, launch_persistent):
    (page, context) = await launch_persistent(color_scheme="dark")
    assert (
        await page.evaluate('() => matchMedia("(prefers-color-scheme: light)").matches')
        is False
    )
    assert await page.evaluate(
        '() => matchMedia("(prefers-color-scheme: dark)").matches'
    )


async def test_should_support_timezone_id_option(launch_persistent):
    (page, context) = await launch_persistent(timezone_id="America/Jamaica")
    assert (
        await page.evaluate("() => new Date(1479579154987).toString()")
        == "Sat Nov 19 2016 13:12:34 GMT-0500 (Eastern Standard Time)"
    )


async def test_should_support_locale_option(launch_persistent):
    (page, context) = await launch_persistent(locale="fr-CH")
    assert await page.evaluate("() => navigator.language") == "fr-CH"


async def test_should_support_geolocation_and_permission_option(
    server, launch_persistent
):
    (page, context) = await launch_persistent(
        geolocation={"longitude": 10, "latitude": 10}, permissions=["geolocation"]
    )
    await page.goto(server.EMPTY_PAGE)
    geolocation = await page.evaluate(
        """() => new Promise(resolve => navigator.geolocation.getCurrentPosition(position => {
    resolve({latitude: position.coords.latitude, longitude: position.coords.longitude});
  }))"""
    )
    assert geolocation == {"latitude": 10, "longitude": 10}


async def test_should_support_ignore_https_errors_option(
    https_server, launch_persistent
):
    (page, context) = await launch_persistent(ignore_https_errors=True)
    response = await page.goto(https_server.EMPTY_PAGE)
    assert response.ok


async def test_should_support_extra_http_headers_option(server, launch_persistent):
    (page, context) = await launch_persistent(extra_http_headers={"foo": "bar"})
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        page.goto(server.EMPTY_PAGE),
    )
    assert request.getHeader("foo") == "bar"


async def test_should_accept_user_data_dir(server, tmpdir, launch_persistent):
    (page, context) = await launch_persistent()
    # Note: we need an open page to make sure its functional.
    assert len(os.listdir(tmpdir)) > 0
    await context.close()
    assert len(os.listdir(tmpdir)) > 0


async def test_should_restore_state_from_userDataDir(
    browser_type, launch_arguments, server, tmp_path_factory
):
    user_data_dir1 = tmp_path_factory.mktemp("test")
    browser_context = await browser_type.launch_persistent_context(
        user_data_dir1, **launch_arguments
    )
    page = await browser_context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate('() => localStorage.hey = "hello"')
    await browser_context.close()

    browser_context2 = await browser_type.launch_persistent_context(
        user_data_dir1, **launch_arguments
    )
    page2 = await browser_context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await page2.evaluate("() => localStorage.hey") == "hello"
    await browser_context2.close()

    user_data_dir2 = tmp_path_factory.mktemp("test")
    browser_context3 = await browser_type.launch_persistent_context(
        user_data_dir2, **launch_arguments
    )
    page3 = await browser_context3.new_page()
    await page3.goto(server.EMPTY_PAGE)
    assert await page3.evaluate("() => localStorage.hey") != "hello"
    await browser_context3.close()


async def test_should_restore_cookies_from_userDataDir(
    browser_type,
    launch_arguments,
    tmp_path_factory,
    server,
    is_chromium,
    is_win,
    is_mac,
):
    if is_chromium and (is_win or is_mac):
        pytest.skip()
    userDataDir = tmp_path_factory.mktemp("1")
    browser_context = await browser_type.launch_persistent_context(
        userDataDir, **launch_arguments
    )
    page = await browser_context.new_page()
    await page.goto(server.EMPTY_PAGE)
    document_cookie = await page.evaluate(
        """() => {
    document.cookie = 'doSomethingOnlyOnce=true; expires=Fri, 31 Dec 9999 23:59:59 GMT';
    return document.cookie;
  }"""
    )

    assert document_cookie == "doSomethingOnlyOnce=true"
    await browser_context.close()

    browser_context2 = await browser_type.launch_persistent_context(
        userDataDir, **launch_arguments
    )
    page2 = await browser_context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await page2.evaluate("() => document.cookie") == "doSomethingOnlyOnce=true"
    await browser_context2.close()

    userDataDir2 = tmp_path_factory.mktemp("2")
    browser_context3 = await browser_type.launch_persistent_context(
        userDataDir2, **launch_arguments
    )
    page3 = await browser_context3.new_page()
    await page3.goto(server.EMPTY_PAGE)
    assert await page3.evaluate("() => document.cookie") != "doSomethingOnlyOnce=true"
    await browser_context3.close()


async def test_should_have_default_url_when_launching_browser(launch_persistent):
    (page, context) = await launch_persistent()
    urls = list(map(lambda p: p.url, context.pages))
    assert urls == ["about:blank"]


@pytest.mark.skip_browser("firefox")
async def test_should_throw_if_page_argument_is_passed(
    browser_type, server, tmpdir, launch_arguments
):
    options = {**launch_arguments, "args": [server.EMPTY_PAGE]}
    with pytest.raises(Error) as exc:
        await browser_type.launch_persistent_context(tmpdir, **options)
    assert "can not specify page" in exc.value.message


async def test_should_fire_close_event_for_a_persistent_context(launch_persistent):
    (page, context) = await launch_persistent()
    fired_event = asyncio.Future()
    context.on("close", lambda: fired_event.set_result(True))
    await context.close()
    await fired_event


async def test_should_support_reduced_motion(launch_persistent):
    (page, context) = await launch_persistent(reduced_motion="reduce")
    assert await page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
