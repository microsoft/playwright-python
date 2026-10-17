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

"""Port of tests/library/browsercontext-dsf.spec.ts."""

from typing import Awaitable, Callable

from playwright.async_api import BrowserContext
from tests.server import Server

ContextFactory = Callable[..., Awaitable[BrowserContext]]


async def test_DV_009_should_fetch_lodpi_assets_smoke(
    context_factory: ContextFactory, server: Server
) -> None:
    context = await context_factory(device_scale_factor=1)
    page = await context.new_page()
    async with page.expect_request("**/image*") as request_info:
        await page.goto(server.PREFIX + "/highdpi.html")
    request = await request_info.value
    assert "image1x" in request.url


async def test_DV_010_should_fetch_hidpi_assets(
    context_factory: ContextFactory, server: Server
) -> None:
    context = await context_factory(device_scale_factor=2)
    page = await context.new_page()
    async with page.expect_request("**/image*") as request_info:
        await page.goto(server.PREFIX + "/highdpi.html")
    request = await request_info.value
    assert "image2x" in request.url
