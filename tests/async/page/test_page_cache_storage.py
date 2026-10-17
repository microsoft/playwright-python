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

"""Port of tests/page/page-cache-storage.spec.ts."""

import pytest

from playwright.async_api import Page
from tests.server import Server


async def test_ST_032_cache_storage_entry_should_survive_page_reload(
    page: Page, server: Server, browser_name: str, request: pytest.FixtureRequest
) -> None:
    # https://github.com/microsoft/playwright/issues/41618
    if browser_name == "webkit":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: Ephemeral CacheStorage is not persisted across "
                "reload in WebKit, consistent with Safari",
                strict=True,
            )
        )

    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
        const cache = await caches.open('repro-cache');
        await cache.put('/meta', new Response('payload'));
    }"""
    )

    await page.reload()

    after = await page.evaluate(
        """async () => {
        const cache = await caches.open('repro-cache');
        const resp = await cache.match('/meta');
        return resp ? await resp.text() : null;
    }"""
    )
    assert after == "payload"
