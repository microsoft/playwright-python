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

from playwright.async_api import Browser, BrowserContext
from tests.server import Server


async def test_should_expose_credentials_property(
    context: BrowserContext,
) -> None:
    assert context.credentials is context.credentials


async def test_install_create_get_and_delete_credentials(
    browser: Browser, https_server: Server
) -> None:
    context = await browser.new_context(ignore_https_errors=True)
    async with context:
        page = await context.new_page()
        await page.goto(https_server.EMPTY_PAGE, wait_until="networkidle")
        creds = context.credentials
        await creds.install()
        result = await creds.create(
            rp_id="localhost",
            id="test-credential-id",
            private_key="private-key-data",
            public_key="public-key-data",
        )
        assert result["id"] == "test-credential-id"
        assert result["rpId"] == "localhost"

        credentials = await creds.get()
        assert len(credentials) == 1
        assert credentials[0]["id"] == "test-credential-id"

        await creds.delete(id="test-credential-id")
        credentials = await creds.get()
        assert len(credentials) == 0
