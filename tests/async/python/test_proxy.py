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

"""Python only: tests of behaviors that no upstream test covers."""

import asyncio
from typing import Callable

from playwright.async_api import Browser
from tests.server import Server


async def test_proxy_should_allow_none_for_optional_settings(
    browser_factory: "Callable[..., asyncio.Future[Browser]]", server: Server
) -> None:
    server.set_route(
        "/target.html",
        lambda r: (
            r.write(b"<html><title>Served by the proxy</title></html>"),
            r.finish(),
        ),
    )
    browser = await browser_factory(
        proxy={
            "server": f"localhost:{server.PORT}",
            "username": None,
            "password": None,
            "bypass": None,
        }
    )
    page = await browser.new_page()
    await page.goto("http://non-existent.com/target.html")
    assert await page.title() == "Served by the proxy"
