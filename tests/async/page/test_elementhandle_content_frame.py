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

"""Port of tests/page/elementhandle-content-frame.spec.ts."""

from playwright.async_api import Page
from tests.server import Server

from ..utils import Utils


async def test_EH_019_should_work(page: Page, server: Server, utils: Utils) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    element_handle = await page.query_selector("#frame1")
    assert element_handle
    frame = await element_handle.content_frame()
    assert frame == page.frames[1]


async def test_EH_020_should_work_for_cross_process_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )
    element_handle = await page.query_selector("#frame1")
    assert element_handle
    frame = await element_handle.content_frame()
    assert frame == page.frames[1]


async def test_EH_021_should_work_for_cross_frame_evaluations(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = (
        await frame.evaluate_handle(
            "() => window.top.document.querySelector('#frame1')"
        )
    ).as_element()
    assert element_handle
    assert await element_handle.content_frame() == frame


async def test_EH_022_should_return_null_for_non_iframes(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = (await frame.evaluate_handle("() => document.body")).as_element()
    assert element_handle
    assert await element_handle.content_frame() is None


async def test_EH_023_should_return_null_for_document_document_element(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]
    element_handle = (
        await frame.evaluate_handle("() => document.documentElement")
    ).as_element()
    assert element_handle
    assert await element_handle.content_frame() is None
