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

"""Port of tests/page/page-click-timeout-3.spec.ts."""

import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_CL_117_should_timeout_waiting_for_hit_target(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate(
        """() => {
    document.body.style.position = 'relative';
    const blocker = document.createElement('div');
    blocker.id = 'blocker';
    blocker.style.position = 'absolute';
    blocker.style.width = '400px';
    blocker.style.height = '20px';
    blocker.style.left = '0';
    blocker.style.top = '0';
    document.body.appendChild(blocker);
  }"""
    )
    with pytest.raises(Error) as exc_info:
        await button.click(timeout=5000)
    assert "ElementHandle.click: Timeout 5000ms exceeded." in exc_info.value.message
    assert (
        '<div id="blocker"></div> intercepts pointer events' in exc_info.value.message
    )
    assert "retrying click action" in exc_info.value.message
    assert "waiting 500ms" in exc_info.value.message


async def test_CL_118_should_still_click_when_force_but_hit_target_is_obscured(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate(
        """() => {
    document.body.style.position = 'relative';
    const blocker = document.createElement('div');
    blocker.id = 'blocker';
    blocker.style.position = 'absolute';
    blocker.style.width = '400px';
    blocker.style.height = '200px';
    blocker.style.left = '0';
    blocker.style.top = '0';
    document.body.appendChild(blocker);
  }"""
    )
    await button.click(force=True)


async def test_CL_119_should_report_wrong_hit_target_subtree(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate(
        """() => {
    document.body.style.position = 'relative';

    const blocker = document.createElement('div');
    blocker.id = 'blocker';
    blocker.style.position = 'absolute';
    blocker.style.width = '400px';
    blocker.style.height = '20px';
    blocker.style.left = '0';
    blocker.style.top = '0';
    document.body.appendChild(blocker);

    const inner = document.createElement('div');
    inner.id = 'inner';
    inner.style.position = 'absolute';
    inner.style.left = '0';
    inner.style.top = '0';
    inner.style.right = '0';
    inner.style.bottom = '0';
    blocker.appendChild(inner);
  }"""
    )
    with pytest.raises(Error) as exc_info:
        await button.click(timeout=5000)
    assert "ElementHandle.click: Timeout 5000ms exceeded." in exc_info.value.message
    assert (
        '<div id="inner"></div> from <div id="blocker">…</div> subtree intercepts pointer events'
        in exc_info.value.message
    )
    assert "retrying click action" in exc_info.value.message
