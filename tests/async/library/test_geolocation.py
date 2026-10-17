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

"""Port of tests/library/geolocation.spec.ts."""

from typing import Any, Awaitable, Callable, Dict, List

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Geolocation
from tests.server import Server

GET_CURRENT_POSITION = """() => new Promise(resolve => navigator.geolocation.getCurrentPosition(position => {
    resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude });
  }))"""


async def test_GE_001_should_work_smoke(
    server: Server, context_factory: Callable[..., Awaitable[BrowserContext]]
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await context.grant_permissions(["geolocation"])
    await page.goto(server.EMPTY_PAGE)
    await context.set_geolocation({"longitude": 10, "latitude": 10})
    geolocation = await page.evaluate(GET_CURRENT_POSITION)
    assert geolocation == {"latitude": 10, "longitude": 10}


async def test_GE_002_should_throw_when_invalid_longitude(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory()
    with pytest.raises(Error) as exc_info:
        await context.set_geolocation({"longitude": 200, "latitude": 10})
    assert (
        "geolocation.longitude: precondition -180 <= LONGITUDE <= 180 failed."
        in exc_info.value.message
    )


async def test_GE_003_should_isolate_contexts(
    server: Server,
    context_factory: Callable[..., Awaitable[BrowserContext]],
    browser: Browser,
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await context.grant_permissions(["geolocation"])
    await context.set_geolocation({"longitude": 10, "latitude": 10})
    await page.goto(server.EMPTY_PAGE)

    context2 = await browser.new_context(
        permissions=["geolocation"],
        geolocation={"longitude": 20, "latitude": 20},
    )
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)

    geolocation = await page.evaluate(GET_CURRENT_POSITION)
    assert geolocation == {"latitude": 10, "longitude": 10}

    geolocation2 = await page2.evaluate(GET_CURRENT_POSITION)
    assert geolocation2 == {"latitude": 20, "longitude": 20}

    await context2.close()


@pytest.mark.skip_protocol_check
async def test_GE_004_should_throw_with_missing_latitude(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> None:
    context = await context_factory()
    with pytest.raises(Error) as exc_info:
        # setGeolocation must have latitude
        await context.set_geolocation({"longitude": 10})  # type: ignore
    assert (
        "geolocation.latitude: expected float, got undefined" in exc_info.value.message
    )


async def test_GE_005_should_not_modify_passed_default_options_object(
    browser: Browser,
) -> None:
    geolocation: Geolocation = {"longitude": 10, "latitude": 10}
    options: Dict[str, Any] = {"geolocation": geolocation}
    context = await browser.new_context(**options)
    await context.set_geolocation({"longitude": 20, "latitude": 20})
    assert options["geolocation"] is geolocation
    await context.close()


@pytest.mark.skip_protocol_check
async def test_GE_006_should_throw_with_missing_longitude_in_default_options(
    browser: Browser,
) -> None:
    with pytest.raises(Error) as exc_info:
        # geolocation must have longitude
        context = await browser.new_context(geolocation={"latitude": 10})  # type: ignore
        await context.close()
    assert (
        "geolocation.longitude: expected float, got undefined" in exc_info.value.message
    )


async def test_GE_007_should_use_context_options(
    browser: Browser, server: Server
) -> None:
    options: Dict[str, Any] = {
        "geolocation": {"longitude": 10, "latitude": 10},
        "permissions": ["geolocation"],
    }
    context = await browser.new_context(**options)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    geolocation = await page.evaluate(GET_CURRENT_POSITION)
    assert geolocation == {"latitude": 10, "longitude": 10}
    await context.close()


async def test_GE_008_watch_position_should_be_notified(
    server: Server, context_factory: Callable[..., Awaitable[BrowserContext]]
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await context.grant_permissions(["geolocation"])
    await page.goto(server.EMPTY_PAGE)
    messages: List[str] = []
    page.on("console", lambda message: messages.append(message.text))

    await context.set_geolocation({"latitude": 0, "longitude": 0})
    await page.evaluate(
        """() => {
    navigator.geolocation.watchPosition(pos => {
      const coords = pos.coords;
      console.log(`lat=${coords.latitude} lng=${coords.longitude}`);
    }, err => {});
  }"""
    )
    async with page.expect_console_message(
        lambda message: "lat=0 lng=10" in message.text
    ):
        await context.set_geolocation({"latitude": 0, "longitude": 10})
    async with page.expect_console_message(
        lambda message: "lat=20 lng=30" in message.text
    ):
        await context.set_geolocation({"latitude": 20, "longitude": 30})
    async with page.expect_console_message(
        lambda message: "lat=40 lng=50" in message.text
    ):
        await context.set_geolocation({"latitude": 40, "longitude": 50})

    all_messages = "|".join(messages)
    assert "lat=0 lng=10" in all_messages
    assert "lat=20 lng=30" in all_messages
    assert "lat=40 lng=50" in all_messages


async def test_GE_009_should_use_context_options_for_popup(
    context_factory: Callable[..., Awaitable[BrowserContext]], server: Server
) -> None:
    context = await context_factory()
    page = await context.new_page()
    await context.grant_permissions(["geolocation"])
    await context.set_geolocation({"longitude": 10, "latitude": 10})
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window['_popup'] = window.open(url)",
            server.PREFIX + "/geolocation.html",
        )
    popup = await popup_info.value
    await popup.wait_for_load_state()
    geolocation = await popup.evaluate("() => window['geolocationPromise']")
    assert geolocation == {"longitude": 10, "latitude": 10}
