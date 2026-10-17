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

"""Port of tests/page/page-event-pageerror.spec.ts."""


from typing import Optional

import pytest

from playwright.async_api import Page
from tests.server import Server, TestServerRequest


def expect_failure(request: pytest.FixtureRequest, reason: str) -> None:
    """Like `it.fail()`: the test must fail."""
    request.applymarker(pytest.mark.xfail(reason=f"upstream: {reason}", strict=True))


async def test_ER_001_should_fire(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "chromium":
        request.applymarker(
            pytest.mark.xfail(
                reason="driver: the bundled driver predates upstream #43468, so Chromium "
                "reports zero-based locations for the cross-origin page error",
                strict=True,
            )
        )
    url = server.PREFIX + "/error.html"
    async with page.expect_event("pageerror") as error_info:
        await page.goto(url)
    error = await error_info.value
    assert error.name == "Error"
    assert error.message == "Fancy error!"
    if browser_name == "chromium":
        assert (
            error.stack
            == """Error: Fancy error!
    at c (myscript.js:14:11)
    at b (myscript.js:10:5)
    at a (myscript.js:6:5)
    at myscript.js:3:1"""
        )
    elif browser_name == "webkit":
        assert (
            error.stack
            == f"""Error: Fancy error!
    at c ({url}:14:36)
    at b ({url}:10:6)
    at a ({url}:6:6)
    at global code ({url}:3:2)"""
        )
    elif browser_name == "firefox":
        assert (
            error.stack
            == """Error: Fancy error!
    at c (myscript.js:14:11)
    at b (myscript.js:10:5)
    at a (myscript.js:6:5)
    at  (myscript.js:3:1)"""
        )

    # The same script from another origin: Chromium reports it without an exception object,
    # so the stack is built from the CDP call frames, which are zero-based.
    cross_origin_url = server.CROSS_PROCESS_PREFIX + "/error.js"

    def handle_script(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/javascript")
        # Same lines as error.html, so the stack has the same locations.
        request.write(
            b"""
console.error('Not a JS error');
a();

function a() {
    b();
}

function b() {
    c();
}

function c() {
    throw new Error('Fancy error!');
}
"""
        )
        request.finish()

    server.set_route("/error.js", handle_script)

    def handle_page(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(f'<script src="{cross_origin_url}"></script>'.encode())
        request.finish()

    server.set_route("/cross-origin-error.html", handle_page)
    async with page.expect_event("pageerror") as cross_origin_error_info:
        await page.goto(server.PREFIX + "/cross-origin-error.html")
    cross_origin_error = await cross_origin_error_info.value
    assert cross_origin_error.message == "Fancy error!"
    if browser_name == "chromium":
        assert (
            cross_origin_error.stack
            == f"""Uncaught Error: Fancy error!
    at c ({cross_origin_url}:14:11)
    at b ({cross_origin_url}:10:5)
    at a ({cross_origin_url}:6:5)
    at <anonymous> ({cross_origin_url}:3:1)"""
        )
    elif browser_name == "webkit":
        assert (
            cross_origin_error.stack
            == f"""Error: Fancy error!
    at c ({cross_origin_url}:14:36)
    at b ({cross_origin_url}:10:6)
    at a ({cross_origin_url}:6:6)
    at global code ({cross_origin_url}:3:2)"""
        )
    elif browser_name == "firefox":
        assert (
            cross_origin_error.stack
            == f"""Error: Fancy error!
    at c ({cross_origin_url}:14:11)
    at b ({cross_origin_url}:10:5)
    at a ({cross_origin_url}:6:5)
    at  ({cross_origin_url}:3:1)"""
        )


async def test_ER_002_should_not_receive_console_message_for_page_error(
    page: Page, server: Server
) -> None:
    messages = []
    page.on("console", lambda e: messages.append(e))
    async with page.expect_event("pageerror"):
        await page.goto(server.PREFIX + "/error.html")
    assert len(messages) == 1


async def test_ER_003_should_contain_source_url(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    if browser_name == "webkit":
        expect_failure(request, "it.fail(browserName === 'webkit')")

    async with page.expect_event("pageerror") as error_info:
        await page.goto(server.PREFIX + "/error.html")
    error = await error_info.value
    assert error.stack
    assert "myscript.js" in error.stack


async def test_ER_004_should_contain_the_error_name_property(page: Page) -> None:
    async with page.expect_event("pageerror") as error_info:
        await page.evaluate(
            """() => {
      window.builtins.setTimeout(() => {
        const error = new Error('my-message');
        error.name = 'my-name';
        throw error;
      }, 0);
    }"""
        )
    error = await error_info.value
    assert error.name == "my-name"
    assert error.message == "my-message"


async def test_ER_005_should_support_an_empty_error_name_property(page: Page) -> None:
    async with page.expect_event("pageerror") as error_info:
        await page.evaluate(
            """() => {
      window.builtins.setTimeout(() => {
        const error = new Error('my-message');
        error.name = '';
        throw error;
      }, 0);
    }"""
        )
    error = await error_info.value
    assert error.name == ""
    assert error.message == "my-message"


async def test_ER_006_should_handle_odd_values(page: Page) -> None:
    # Python has no undefined value to pass as the argument, so each value is
    # written into the script.
    cases = [
        ["null", "null"],
        ["undefined", "undefined"],
        ["0", "0"],
        ["''", ""],
    ]
    for value, message in cases:
        async with page.expect_event("pageerror") as error_info:
            await page.evaluate(
                f"""() => {{
        window.builtins.setTimeout(() => {{ throw {value}; }}, 0);
      }}"""
            )
        error = await error_info.value
        assert error.message == message


async def test_ER_007_should_handle_object(page: Page, browser_name: str) -> None:
    async with page.expect_event("pageerror") as error_info:
        await page.evaluate(
            """() => {
      window.builtins.setTimeout(() => { throw {}; }, 0);
    }"""
        )
    error = await error_info.value
    assert error.message == (
        "Object" if browser_name == "chromium" else "[object Object]"
    )


async def test_ER_008_should_handle_window(page: Page, browser_name: str) -> None:
    async with page.expect_event("pageerror") as error_info:
        await page.evaluate(
            """() => {
      window.builtins.setTimeout(() => { throw window; }, 0);
    }"""
        )
    error = await error_info.value
    assert error.message == (
        "Window" if browser_name == "chromium" else "[object Window]"
    )


async def test_ER_009_should_remove_a_listener_of_a_non_existing_event_handler(
    page: Page,
) -> None:
    page.remove_listener("pageerror", lambda: None)


async def test_ER_010_should_emit_error_from_unhandled_rejects(page: Page) -> None:
    async with page.expect_event("pageerror") as error_info:
        await page.set_content(
            """
        <script>
          Promise.reject(new Error('sad :('));
        </script>
    """
        )
    error = await error_info.value
    assert "sad :(" in error.message


async def test_ER_011_page_errors_should_work(page: Page) -> None:
    await page.evaluate(
        """async () => {
    for (let i = 0; i < 301; i++)
      window.builtins.setTimeout(() => { throw new Error('error' + i); }, 0);
    await new Promise(f => window.builtins.setTimeout(f, 2000));
  }"""
    )

    errors = await page.page_errors()
    messages = [e.message for e in errors]

    expected = []
    for i in range(201, 301):
        expected.append("error" + str(i))

    assert len(messages) >= 100, "should be at least 100 errors"
    start = len(messages) - len(expected)
    assert messages[start:] == expected, "should return last errors"


async def test_ER_012_clear_page_errors_should_work(page: Page) -> None:
    await page.evaluate(
        """() => {
    window.builtins.setTimeout(() => { throw new Error('error1'); }, 0);
    window.builtins.setTimeout(() => { throw new Error('error2'); }, 0);
  }"""
    )
    await page.wait_for_timeout(1000)

    errors = await page.page_errors()
    assert "error1" in [e.message for e in errors]
    assert "error2" in [e.message for e in errors]

    await page.clear_page_errors()

    errors = await page.page_errors()
    assert errors == []

    await page.evaluate(
        """() => {
    window.builtins.setTimeout(() => { throw new Error('error3'); }, 0);
  }"""
    )
    await page.wait_for_timeout(1000)

    errors = await page.page_errors()
    assert len(errors) == 1
    assert "error3" in errors[0].message


async def test_ER_013_should_fire_illegal_character_error(
    page: Page,
    server: Server,
    browser_name: str,
    is_win: bool,
    browser_channel: Optional[str],
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(
            """
      <!doctype html>
      <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>vite-project</title>
        </head>
        <body>
          <div id="app"></div>
          <script >
            let a=10；//   !!!note: ； not ;
          </script>
        </body>
      </html>
    """.encode()
        )
        request.finish()

    server.set_route("/error.html", handle)
    url = server.PREFIX + "/error.html"
    async with page.expect_event("pageerror") as error_info:
        await page.goto(url)
    error = await error_info.value
    if browser_name == "chromium":
        assert "Invalid or unexpected token" in error.message
    elif browser_name == "webkit" and is_win and browser_channel != "webkit-wsl":
        assert "No identifiers allowed directly after numeric literal" in error.message
    elif browser_name == "webkit":
        assert "Invalid character" in error.message
    else:
        assert "illegal character" in error.message
