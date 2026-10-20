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

"""Port of tests/library/page-clock.frozen.spec.ts.

Run with PW_CLOCK=frozen or PW_CLOCK=realtime; otherwise both tests skip, as upstream.
"""

import os
from typing import AsyncGenerator, Awaitable, Callable

import pytest

from playwright.async_api import BrowserContext, Page


@pytest.fixture
async def context(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> AsyncGenerator[BrowserContext, None]:
    # Port of the PW_CLOCK handling in _contextFactory of tests/config/browserTest.ts.
    context = await context_factory()
    if os.environ.get("PW_CLOCK") == "frozen":
        await context.clock.install(time=0)
        await context.clock.pause_at(1)
    elif os.environ.get("PW_CLOCK") == "realtime":
        await context.clock.install(time=0)
    yield context


async def test_CK_055_clock_should_be_frozen(page: Page) -> None:
    if os.environ.get("PW_CLOCK") != "frozen":
        pytest.skip("PW_CLOCK is not frozen")
    assert await page.evaluate("Date.now()") == 1000


async def test_CK_056_clock_should_be_realtime(page: Page) -> None:
    if os.environ.get("PW_CLOCK") != "realtime":
        pytest.skip("PW_CLOCK is not realtime")
    assert await page.evaluate("Date.now()") < 10000
