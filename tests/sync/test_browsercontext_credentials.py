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

from playwright.sync_api import Browser, BrowserContext
from tests.server import Server


def test_should_expose_credentials_property(context: BrowserContext) -> None:
    assert context.credentials is context.credentials


def test_install_create_get_and_delete_credentials(
    browser: Browser, https_server: Server
) -> None:
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto(https_server.EMPTY_PAGE, wait_until="networkidle")
    creds = context.credentials
    creds.install()
    result = creds.create(
        rp_id="localhost",
        id="test-credential-id",
        private_key="private-key-data",
        public_key="public-key-data",
    )
    assert result["id"] == "test-credential-id"
    assert result["rpId"] == "localhost"

    credentials = creds.get()
    assert len(credentials) == 1
    assert credentials[0]["id"] == "test-credential-id"

    creds.delete(id="test-credential-id")
    credentials = creds.get()
    assert len(credentials) == 0
    context.close()
