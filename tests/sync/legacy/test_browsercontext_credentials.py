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

from playwright.sync_api import Browser, BrowserContext, Page
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
    result = creds.create(rp_id="localhost")
    assert result["rpId"] == "localhost"
    assert "id" in result

    credentials = creds.get()
    assert len(credentials) == 1
    assert credentials[0]["id"] == result["id"]

    creds.delete(id=result["id"])
    credentials = creds.get()
    assert len(credentials) == 0
    context.close()


def test_should_seed_and_report_sign_count(
    browser: Browser, https_server: Server
) -> None:
    def assert_and_get_sign_count(page: Page) -> int:
        return page.evaluate(
            """async () => {
              const challenge = crypto.getRandomValues(new Uint8Array(32));
              const cred = await navigator.credentials.get({
                publicKey: { challenge, rpId: 'localhost', userVerification: 'preferred' },
              });
              return new DataView(cred.response.authenticatorData).getUint32(33);
            }"""
        )

    context = browser.new_context(ignore_https_errors=True)
    with context:
        fresh = context.credentials.create(rp_id="fresh.example.com")
        assert fresh["signCount"] == 0
        seeded = context.credentials.create(rp_id="localhost", sign_count=41)
        assert seeded["signCount"] == 41
        context.credentials.install()
        page = context.new_page()
        page.goto(https_server.EMPTY_PAGE)
        # Each assertion increments the counter and reports the new value to the page.
        assert assert_and_get_sign_count(page) == 42
        assert assert_and_get_sign_count(page) == 43
        assert context.credentials.get(id=seeded["id"]) == [{**seeded, "signCount": 43}]
        assert context.credentials.get(id=fresh["id"]) == [fresh]
