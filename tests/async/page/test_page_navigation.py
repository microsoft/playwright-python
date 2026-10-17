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

"""Port of tests/page/page-navigation.spec.ts."""

from typing import Callable

from playwright.async_api import Page, expect
from tests.server import Server, TestServerRequest


def serve(body: str) -> Callable[[TestServerRequest], None]:
    def handle(request: TestServerRequest) -> None:
        request.write(body.encode())
        request.finish()

    return handle


async def test_NA_067_should_work_with_blank_target(page: Page, server: Server) -> None:
    server.set_route(
        "/empty.html",
        serve(f'<a href="{server.EMPTY_PAGE}" target="_blank">Click me</a>'),
    )
    await page.goto(server.EMPTY_PAGE)
    await page.click('"Click me"')


async def test_NA_068_should_work_with_cross_process_blank_target(
    page: Page, server: Server
) -> None:
    server.set_route(
        "/empty.html",
        serve(
            f'<a href="{server.CROSS_PROCESS_PREFIX}/empty.html" target="_blank">Click me</a>'
        ),
    )
    await page.goto(server.EMPTY_PAGE)
    await page.click('"Click me"')


async def test_NA_069_should_work_with_blank_target_in_form(
    page: Page, server: Server
) -> None:
    server.set_route("/done.html?", serve("Done"))
    server.set_route("/done.html", serve("Done"))
    await page.goto(server.EMPTY_PAGE)

    await page.set_content(
        """<form target="_blank" action="done.html" >
    <input type="submit" value="Click me">
  </form>"""
    )
    async with page.expect_popup():
        await page.click('"Click me"')

    await page.set_content(
        """<form target="_blank" action="done.html" method="post">
    <input type="submit" value="Click me">
  </form>"""
    )
    async with page.expect_popup():
        await page.click('"Click me"')


async def test_NA_070_should_not_throw_target_closed_exception_on_cross_origin_redirect_after_click(
    page: Page, server: Server
) -> None:
    server.set_route("/target.html", serve("<title>final page</title>"))
    server.set_redirect("/redirect", server.CROSS_PROCESS_PREFIX + "/target.html")
    await page.goto(server.PREFIX + "/empty.html")
    await page.set_content(
        f"""
    <form action="{server.PREFIX}/redirect" method="POST">
      <button type="submit">Submit</button>
    </form>
  """
    )
    async with page.expect_navigation():
        # triggers POST -> 302 -> cross-origin
        await page.click("button")
    await expect(page).to_have_url(server.CROSS_PROCESS_PREFIX + "/target.html")
    await expect(page).to_have_title("final page")
