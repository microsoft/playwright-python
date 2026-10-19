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

"""Port of tests/library/emulation-coop.spec.ts."""

from typing import Any, Dict, Optional

from playwright.sync_api import Browser
from tests.server import Server, TestServerRequest


def setup_routes(server: Server) -> None:
    for path, coop in [("/plain.html", False), ("/coop.html", True)]:

        def handler(request: TestServerRequest, coop: bool = coop) -> None:
            if coop:
                request.setHeader("Cross-Origin-Opener-Policy", "same-origin")
            request.setHeader("Content-Type", "text/html")
            request.write(b"<title>t</title><p>hello</p>")
            request.finish()

        server.set_route(path, handler)


def probe(
    browser: Browser,
    server: Server,
    options: Dict[str, Any],
    path: str,
    media: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = browser.new_context(**options)
    page = context.new_page()
    if media:
        page.emulate_media(**media)
    page.goto(server.PREFIX + path)
    result = page.evaluate(
        """() => ({
    dark: matchMedia('(prefers-color-scheme: dark)').matches,
    dpr: devicePixelRatio,
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    forcedColors: matchMedia('(forced-colors: active)').matches,
    contrast: matchMedia('(prefers-contrast: more)').matches,
    print: matchMedia('print').matches,
    lang: navigator.language,
    tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
    ua: navigator.userAgent,
    touch: 'ontouchstart' in window,
    coarse: matchMedia('(pointer: coarse)').matches,
    viewport: [innerWidth, innerHeight],
    screen: [screen.width, screen.height],
    orientation: screen.orientation.type,
  })"""
    )
    context.close()
    return result


def object_containing(actual: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    """Port of expect.objectContaining for a flat object."""
    return {key: actual.get(key) for key in expected} == expected


def test_EM_025_emulation_with_coop_should_preserve_context_options(
    browser: Browser, server: Server
) -> None:
    setup_routes(server)
    options: Dict[str, Any] = {
        "color_scheme": "dark",
        "device_scale_factor": 2,
        "reduced_motion": "reduce",
        "contrast": "more",
        "locale": "de-DE",
        "timezone_id": "Asia/Tokyo",
        "user_agent": "MyUA",
        "has_touch": True,
        "viewport": {"width": 500, "height": 600},
    }
    plain = probe(browser, server, options, "/plain.html")
    assert object_containing(
        plain,
        {
            "dark": True,
            "dpr": 2,
            "reducedMotion": True,
            "contrast": True,
            "lang": "de-DE",
            "tz": "Asia/Tokyo",
            "ua": "MyUA",
            "touch": True,
            "viewport": [500, 600],
        },
    ), plain
    coop = probe(browser, server, options, "/coop.html")
    assert coop == plain


def test_EM_026_emulation_with_coop_should_preserve_page_emulate_media(
    browser: Browser, server: Server
) -> None:
    setup_routes(server)
    media: Dict[str, Any] = {
        "media": "print",
        "color_scheme": "dark",
        "reduced_motion": "reduce",
        "contrast": "more",
        "forced_colors": "active",
    }
    plain = probe(browser, server, {}, "/plain.html", media)
    assert object_containing(
        plain,
        {
            "print": True,
            "reducedMotion": True,
            "contrast": True,
            "forcedColors": True,
        },
    ), plain
    coop = probe(browser, server, {}, "/coop.html", media)
    assert coop == plain


def test_EM_027_emulation_with_coop_should_preserve_mobile_emulation(
    browser: Browser, server: Server
) -> None:
    setup_routes(server)
    options: Dict[str, Any] = {
        "is_mobile": True,
        "has_touch": True,
        "viewport": {"width": 500, "height": 600},
        "screen": {"width": 700, "height": 900},
    }
    plain = probe(browser, server, options, "/plain.html")
    assert object_containing(
        plain,
        {
            "coarse": True,
            "orientation": "portrait-primary",
        },
    ), plain
    coop = probe(browser, server, options, "/coop.html")
    assert coop == plain
