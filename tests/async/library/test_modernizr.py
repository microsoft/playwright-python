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

"""Port of tests/library/modernizr.spec.ts."""

import json
import platform as os_platform
from pathlib import Path
from typing import Any, Optional, Tuple

import pytest

from playwright.async_api import Browser, BrowserContext, Playwright
from tests.server import Server


async def check_features(
    name: str, context: BrowserContext, server: Server, assetdir: Path
) -> Tuple[Any, Any]:
    try:
        page = await context.new_page()
        await page.goto(server.PREFIX + "/modernizr/index.html")
        actual = await page.evaluate("window.report")
        expected = json.loads((assetdir / "modernizr" / f"{name}.json").read_text())
        return actual, expected
    finally:
        await context.close()


def skip_unless_supported(
    browser_name: str, platform: str, is_frozen_webkit: bool
) -> None:
    if browser_name != "webkit":
        pytest.skip("webkit only")
    if (
        browser_name == "webkit"
        and platform == "darwin"
        and os_platform.machine() == "x86_64"
    ):
        pytest.skip(
            "Modernizr uses WebGL which is not available on Intel macOS - https://bugs.webkit.org/show_bug.cgi?id=278277"
        )
    if is_frozen_webkit:
        pytest.skip("frozen webkit")


def apply_platform_overrides(
    actual: Any, expected: Any, platform: str, browser_channel: Optional[str]
) -> None:
    if platform == "linux" or browser_channel == "webkit-wsl":
        expected["speechrecognition"] = False
        expected["mediastream"] = False
        expected["todataurlwebp"] = True

        # GHA
        actual.pop("variablefonts", None)
        expected.pop("variablefonts", None)

    if platform == "win32" and browser_channel != "webkit-wsl":
        expected["getusermedia"] = False
        expected["peerconnection"] = False
        expected["speechrecognition"] = False
        expected["speechsynthesis"] = False
        expected["todataurlwebp"] = True
        expected["webaudio"] = False
        expected["gamepads"] = False

        expected.pop("datalistelem", None)

        expected["mediastream"] = False
        expected["mediasource"] = False
        expected["datachannel"] = False

        expected["inputtypes"]["color"] = False
        expected["inputtypes"]["date"] = False
        expected["inputtypes"]["datetime-local"] = False
        expected["inputtypes"]["time"] = False


async def test_CA_030_safari_desktop(
    browser: Browser,
    browser_name: str,
    platform: str,
    https_server: Server,
    browser_channel: Optional[str],
    is_frozen_webkit: bool,
    assetdir: Path,
) -> None:
    skip_unless_supported(browser_name, platform, is_frozen_webkit)
    context = await browser.new_context(
        device_scale_factor=2,
        ignore_https_errors=True,
        # @playwright/test passes isMobile: false to every new context. Without it,
        # WebKit keeps <input type=month> enabled, which desktop Safari does not have.
        is_mobile=False,
    )
    actual, expected = await check_features(
        "safari-26", context, https_server, assetdir
    )

    # Shipping Safari exposes `font-display` as a settable CSS property (element.style.fontDisplay === ''),
    # but open-source WebKit keeps it a @font-face descriptor only, so it is undefined here. No runtime
    # flag bridges the gap, hence the override.
    expected["fontdisplay"] = False

    expected.pop("webglextensions", None)
    actual.pop("webglextensions", None)
    expected["audio"] = bool(expected["audio"])
    actual["audio"] = bool(actual["audio"])
    expected["video"] = bool(expected["video"])
    actual["video"] = bool(actual["video"])

    apply_platform_overrides(actual, expected, platform, browser_channel)

    assert actual == expected


async def test_CA_031_mobile_safari(
    playwright: Playwright,
    browser: Browser,
    browser_name: str,
    platform: str,
    https_server: Server,
    browser_channel: Optional[str],
    is_frozen_webkit: bool,
    assetdir: Path,
) -> None:
    skip_unless_supported(browser_name, platform, is_frozen_webkit)
    iphone = playwright.devices["iPhone 12"]
    context = await browser.new_context(
        **iphone,
        ignore_https_errors=True,
    )
    actual, expected = await check_features(
        "mobile-safari-26", context, https_server, assetdir
    )

    # All platforms.
    expected["capture"] = False
    expected["cssscrollbar"] = True
    expected["cssvhunit"] = True
    expected["cssvmaxunit"] = True
    expected["overflowscrolling"] = False
    expected["mediasource"] = True
    expected["scrolltooptions"] = False

    # Shipping Safari exposes `font-display` as a settable CSS property (element.style.fontDisplay === ''),
    # but open-source WebKit keeps it a @font-face descriptor only, so it is undefined here. No runtime
    # flag bridges the gap, hence the override.
    expected["fontdisplay"] = False

    expected.pop("webglextensions", None)
    actual.pop("webglextensions", None)
    expected["audio"] = bool(expected["audio"])
    actual["audio"] = bool(actual["audio"])
    expected["video"] = bool(expected["video"])
    actual["video"] = bool(actual["video"])

    apply_platform_overrides(actual, expected, platform, browser_channel)

    assert actual == expected
