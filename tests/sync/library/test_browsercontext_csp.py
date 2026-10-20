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

"""Port of tests/library/browsercontext-csp.spec.ts."""


from playwright.sync_api import Browser, Error
from tests.server import Server, TestServerRequest

from ..utils import Utils


def test_CS_001_should_bypass_csp_meta_tag_smoke(
    browser: Browser, server: Server
) -> None:
    # Make sure CSP prohibits addScriptTag.
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/csp.html")
    assert page.evaluate('window["__inlineScriptValue"]') is None
    try:
        page.add_script_tag(content='window["__injected"] = 42;')
    except Error:
        pass
    assert page.evaluate('window["__injected"]') is None
    context.close()

    # By-pass CSP and try one more time.
    context = browser.new_context(bypass_csp=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/csp.html")
    assert page.evaluate('window["__inlineScriptValue"]') == 42
    page.add_script_tag(content='window["__injected"] = 42;')
    assert page.evaluate('window["__injected"]') == 42
    context.close()


def test_CS_002_should_bypass_csp_header(browser: Browser, server: Server) -> None:
    # Make sure CSP prohibits addScriptTag.
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Security-Policy", 'default-src "self"')
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"<script type='text/javascript'>window.__inlineScriptValue = 42;</script>"
        )
        request.finish()

    server.set_route("/empty.html", handle)

    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    assert page.evaluate('window["__inlineScriptValue"]') is None
    try:
        page.add_script_tag(content='window["__injected"] = 42;')
    except Error:
        pass
    assert page.evaluate('window["__injected"]') is None
    context.close()

    # By-pass CSP and try one more time.
    context = browser.new_context(bypass_csp=True)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    assert page.evaluate('window["__inlineScriptValue"]') == 42
    page.add_script_tag(content='window["__injected"] = 42;')
    assert page.evaluate('window["__injected"]') == 42
    context.close()


def test_CS_003_should_bypass_after_cross_process_navigation(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(bypass_csp=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/csp.html")
    assert page.evaluate('window["__inlineScriptValue"]') == 42
    page.add_script_tag(content='window["__injected"] = 42;')
    assert page.evaluate('window["__injected"]') == 42

    page.goto(server.CROSS_PROCESS_PREFIX + "/csp.html")
    assert page.evaluate('window["__inlineScriptValue"]') == 42
    page.add_script_tag(content='window["__injected"] = 42;')
    assert page.evaluate('window["__injected"]') == 42
    context.close()


def test_CS_004_should_bypass_csp_in_iframes_as_well(
    browser: Browser, server: Server, utils: Utils
) -> None:
    # Make sure CSP prohibits addScriptTag in an iframe.
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    frame = utils.attach_frame(page, "frame1", server.PREFIX + "/csp.html")
    assert frame.evaluate('window["__inlineScriptValue"]') is None
    try:
        frame.add_script_tag(content='window["__injected"] = 42;')
    except Error:
        pass
    assert frame.evaluate('window["__injected"]') is None
    context.close()

    # By-pass CSP and try one more time.
    context = browser.new_context(bypass_csp=True)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    frame = utils.attach_frame(page, "frame1", server.PREFIX + "/csp.html")
    assert frame.evaluate('window["__inlineScriptValue"]') == 42
    try:
        frame.add_script_tag(content='window["__injected"] = 42;')
    except Error:
        pass
    assert frame.evaluate('window["__injected"]') == 42
    context.close()


def test_CS_005_should_not_crash_on_javascript_navigation(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(bypass_csp=True)
    page = context.new_page()
    crashed = False

    def on_crash() -> None:
        nonlocal crashed
        crashed = True

    page.on("crash", lambda _: on_crash())
    page.goto(server.EMPTY_PAGE)
    page.set_content('<a id="a" href="javascript:window.__clicked = true">click</a>')
    page.click("#a")
    # Port of expect.poll(() => page.evaluate(() => window['__clicked'])).toBe(true).
    page.wait_for_function("() => window['__clicked'] === true")
    assert crashed is False
    context.close()
