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

"""Port of tests/page/page-autowaiting-basic.spec.ts."""

import re
from typing import List

import pytest

from playwright.sync_api import Error, Page, expect
from tests.server import Server, TestServerRequest


def strip_ansi(text: str) -> str:
    """Port of stripAnsi in tests/config/utils.ts."""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def init_server(server: Server) -> List[str]:
    messages: List[str] = []

    def handler(request: TestServerRequest) -> None:
        messages.append("route")
        request.setHeader("Content-Type", "text/html")
        request.write(b"<link rel='stylesheet' href='./one-style.css'>")
        request.finish()

    server.set_route("/empty.html", handler)
    return messages


def test_AW_001_should_await_navigation_when_clicking_anchor(
    page: Page, server: Server
) -> None:
    messages = init_server(server)
    page.set_content(f'<a id="anchor" href="{server.EMPTY_PAGE}">empty.html</a>')
    page.once("framenavigated", lambda _: messages.append("navigated"))
    page.click("a")
    messages.append("click")
    assert "|".join(messages) == "route|navigated|click"


def test_AW_002_should_not_stall_on_js_navigation_link(page: Page) -> None:
    page.set_content('<a href="javascript:console.log(1)">console.log</a>')
    page.click("a")


def test_AW_003_should_await_cross_process_navigation_when_clicking_anchor(
    page: Page, server: Server
) -> None:
    messages = init_server(server)
    page.set_content(
        f'<a href="{server.CROSS_PROCESS_PREFIX + "/empty.html"}">empty.html</a>'
    )

    page.once("framenavigated", lambda _: messages.append("navigated"))
    page.click("a")
    messages.append("click")
    assert "|".join(messages) == "route|navigated|click"


def test_AW_004_should_await_form_get_on_click(page: Page, server: Server) -> None:
    messages: List[str] = []

    def handler(request: TestServerRequest) -> None:
        messages.append("route")
        request.setHeader("Content-Type", "text/html")
        request.write(b"<link rel='stylesheet' href='./one-style.css'>")
        request.finish()

    server.set_route("/empty.html?foo=bar", handler)

    page.set_content(
        f"""
    <form action="{server.EMPTY_PAGE}" method="get">
      <input name="foo" value="bar">
      <input type="submit" value="Submit">
    </form>"""
    )

    page.once("framenavigated", lambda _: messages.append("navigated"))
    page.click("input[type=submit]")
    messages.append("click")
    assert "|".join(messages) == "route|navigated|click"


def test_AW_005_should_await_form_post_on_click(page: Page, server: Server) -> None:
    messages = init_server(server)
    page.set_content(
        f"""
    <form action="{server.EMPTY_PAGE}" method="post">
      <input name="foo" value="bar">
      <input type="submit" value="Submit">
    </form>"""
    )

    page.once("framenavigated", lambda _: messages.append("navigated"))
    page.click("input[type=submit]")
    messages.append("click")
    assert "|".join(messages) == "route|navigated|click"


def test_AW_006_should_work_with_no_wait_after_true(page: Page, server: Server) -> None:
    server.set_route("/empty.html", lambda request: None)
    page.set_content(f'<a id="anchor" href="{server.EMPTY_PAGE}">empty.html</a>')
    page.click("a", no_wait_after=True)


def test_AW_007_should_work_with_dblclick_without_no_wait_after_when_navigation_is_stalled(
    page: Page, server: Server
) -> None:
    server.set_route("/empty.html", lambda request: None)
    page.set_content(f'<a id="anchor" href="{server.EMPTY_PAGE}">empty.html</a>')
    page.dblclick("a")


def test_AW_008_should_work_with_wait_for_load_state_load(
    page: Page, server: Server
) -> None:
    messages = init_server(server)
    page.set_content(f'<a id="anchor" href="{server.EMPTY_PAGE}">empty.html</a>')
    page.once("load", lambda _: messages.append("load"))
    page.click("a")
    page.wait_for_load_state("load")
    messages.append("clickload")
    assert "|".join(messages) == "route|load|clickload"


def test_AW_009_should_work_with_goto_following_click(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(b"You are logged in")
        request.finish()

    server.set_route("/login.html", handler)

    page.set_content(
        f"""
    <form action="{server.PREFIX}/login.html" method="get">
      <input type="text">
      <input type="submit" value="Submit">
    </form>"""
    )

    page.fill("input[type=text]", "admin")
    page.click("input[type=submit]")
    page.goto(server.EMPTY_PAGE)


def test_AW_011_should_report_and_collapse_log_in_action(page: Page) -> None:
    page.set_content(
        "<input id='checkbox' type='checkbox' style=\"visibility: hidden\"></input>"
    )
    with pytest.raises(Error) as exc_info:
        page.locator("input").click(timeout=5000)
    message = strip_ansi(exc_info.value.message)
    assert "Call log:" in message
    assert re.search(r"\d+ × waiting for", message)
    call_log_start = message.index("Call log:")
    log_lines = message[call_log_start:].split("\n")
    assert len(log_lines) < 30


def test_AW_012_should_report_and_collapse_log_in_expect(page: Page) -> None:
    page.set_content(
        "<input id='checkbox' type='checkbox' style=\"visibility: hidden\"></input>"
    )
    # Python assertions raise AssertionError, not Error.
    with pytest.raises(AssertionError) as exc_info:
        expect(page.locator("input")).to_be_visible(timeout=5000)
    message = strip_ansi(str(exc_info.value))
    assert "Call log:" in message
    assert re.search(r"\d+ × locator resolved to", message)
