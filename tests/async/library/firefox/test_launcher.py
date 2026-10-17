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

"""Port of tests/library/firefox/launcher.spec.ts."""

import json
import os
from pathlib import Path
from typing import Awaitable, Callable, Dict, Tuple, Union

import pytest

from playwright.async_api import BrowserContext, BrowserType, Error, Page, expect
from tests.helpers.static_https_server import StaticHTTPSServer

pytestmark = pytest.mark.only_browser("firefox")

# Port of inheritAndCleanEnv() in tests/config/utils.ts.
RESERVED_CI_ENV = [
    "CI",
    "BUILD_URL",
    "CI_COMMIT_SHA",
    "CI_JOB_URL",
    "CI_PROJECT_URL",
    "GITHUB_ACTIONS",
    "GITHUB_REPOSITORY",
    "GITHUB_RUN_ID",
    "GITHUB_SERVER_URL",
    "GITHUB_SHA",
    "GITHUB_EVENT_PATH",
]


def inherit_and_clean_env(env: Dict[str, str]) -> Dict[str, Union[str, float, bool]]:
    result: Dict[str, Union[str, float, bool]] = {
        name: value for name, value in os.environ.items() if name not in RESERVED_CI_ENV
    }
    return {**result, **env}


async def test_FF_001_should_pass_firefox_user_preferences(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = await browser_type.launch(
        **launch_arguments,
        firefox_user_prefs={
            "network.proxy.type": 1,
            "network.proxy.ssl": "127.0.0.1",
            "network.proxy.ssl_port": 3333,
        },
    )
    page = await browser.new_page()
    with pytest.raises(Error) as exc_info:
        await page.goto("https://example.com")
    assert "NS_ERROR_PROXY_CONNECTION_REFUSED" in exc_info.value.message
    await browser.close()


async def test_FF_002_should_pass_firefox_user_preferences_in_persistent(
    launch_persistent: Callable[..., Awaitable[Tuple[BrowserContext, Page]]],
) -> None:
    _, page = await launch_persistent(
        firefox_user_prefs={
            "network.proxy.type": 1,
            "network.proxy.ssl": "127.0.0.1",
            "network.proxy.ssl_port": 3333,
        }
    )
    with pytest.raises(Error) as exc_info:
        await page.goto("https://example.com")
    assert "NS_ERROR_PROXY_CONNECTION_REFUSED" in exc_info.value.message


async def test_FF_003_should_support_custom_firefox_policies(
    browser_type: BrowserType, launch_arguments: Dict, assetdir: Path, tmp_path: Path
) -> None:
    policies = {
        "policies": {
            "Certificates": {
                "Install": [
                    str(assetdir / "client-certificates/server/server_cert.pem")
                ],
            },
        },
    }
    policies_path = tmp_path / "policies.json"
    policies_path.write_text(json.dumps(policies))

    # Upstream listens on the port 13122.
    server = StaticHTTPSServer(
        assetdir,
        cert=assetdir / "client-certificates/client/localhost/localhost.pem",
        key=assetdir / "client-certificates/client/localhost/localhost.key",
    )

    browser = await browser_type.launch(
        **launch_arguments,
        env=inherit_and_clean_env(
            {"PLAYWRIGHT_FIREFOX_POLICIES_JSON": str(policies_path)}
        ),
    )

    page = await browser.new_page()
    await page.goto(server.PREFIX + "/frames/frame.html")
    await expect(page.locator("body")).to_have_text("Hi, I'm frame")
    await browser.close()
    server.stop()


async def test_FF_004_should_resize_viewport_with_fractional_device_scale_factor(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    # A fractional device scale factor makes the viewport size fractional in CSS pixels,
    # e.g. 400.27x799.9 instead of 400x800. Web content still sees rounded values.
    browser = await browser_type.launch(
        **launch_arguments, firefox_user_prefs={"layout.css.devPixelsPerPx": "1.1"}
    )
    page = await browser.new_page()
    await page.set_viewport_size({"width": 400, "height": 800})
    assert await page.evaluate("() => [window.innerWidth, window.innerHeight]") == [
        400,
        800,
    ]
    await browser.close()
