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

"""Port of tests/page/page-emulate-media.spec.ts."""

from typing import Any, Callable, Literal, Optional, cast

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server, TestServerRequest


def to_match_media(page: Page, media_query: str) -> bool:
    """Port of the toMatchMedia matcher: whether the media query matches."""
    try:
        return page.evaluate(
            "mediaQuery => matchMedia(mediaQuery).matches", media_query
        )
    except Error:
        return False


def test_EM_001_should_emulate_type_smoke(page: Page) -> None:
    assert page.evaluate("() => matchMedia('screen').matches") is True
    assert page.evaluate("() => matchMedia('print').matches") is False
    page.emulate_media(media="print")
    assert page.evaluate("() => matchMedia('screen').matches") is False
    assert page.evaluate("() => matchMedia('print').matches") is True
    page.emulate_media()
    assert page.evaluate("() => matchMedia('screen').matches") is False
    assert page.evaluate("() => matchMedia('print').matches") is True
    page.emulate_media(media="null")
    assert page.evaluate("() => matchMedia('screen').matches") is True
    assert page.evaluate("() => matchMedia('print').matches") is False


def test_EM_002_should_throw_in_case_of_bad_media_argument(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.emulate_media(media=cast(Any, "bad"))
    assert "media: expected one of (screen|print|no-override)" in exc_info.value.message


def test_EM_003_should_emulate_color_scheme_should_work_smoke(
    page: Page,
) -> None:
    page.emulate_media(color_scheme="light")
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is True
    )
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is False
    )
    page.emulate_media(color_scheme="dark")
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is False
    )


def test_EM_004_should_default_to_light(page: Page) -> None:
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is True
    )
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is False
    )

    page.emulate_media(color_scheme="dark")
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is False
    )

    page.emulate_media(color_scheme="null")
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is False
    )
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: light)').matches")
        is True
    )


def test_EM_005_should_throw_in_case_of_bad_color_scheme_argument(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        page.emulate_media(color_scheme=cast(Any, "bad"))
    # The driver names the option in Python's snake_case.
    assert (
        "color_scheme: expected one of (dark|light|no-preference|no-override)"
        in exc_info.value.message
    )


def test_EM_006_should_work_during_navigation(
    page: Page, server: Server, sync_gather: Callable
) -> None:
    page.emulate_media(color_scheme="light")

    def emulate() -> None:
        schemes: "tuple[Literal['dark'], Literal['light']]" = ("dark", "light")
        for i in range(9):
            page.emulate_media(color_scheme=schemes[i & 1])
            page.wait_for_timeout(1)

    sync_gather(lambda: page.goto(server.EMPTY_PAGE), emulate)
    assert (
        page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches")
        is True
    )


def test_EM_007_should_change_the_actual_colors_in_css(page: Page) -> None:
    page.set_content(
        """
    <style>
      @media (prefers-color-scheme: dark) {
        div {
          background: black;
          color: white;
        }
      }
      @media (prefers-color-scheme: light) {
        div {
          background: white;
          color: black;
        }
      }

    </style>
    <div>Hello</div>
  """
    )

    def get_background_color() -> Optional[str]:
        return page.eval_on_selector(
            "div", "div => window.getComputedStyle(div).backgroundColor"
        )

    page.emulate_media(color_scheme="light")
    assert get_background_color() == "rgb(255, 255, 255)"

    page.emulate_media(color_scheme="dark")
    assert get_background_color() == "rgb(0, 0, 0)"

    page.emulate_media(color_scheme="light")
    assert get_background_color() == "rgb(255, 255, 255)"


def test_EM_008_should_emulate_reduced_motion(page: Page) -> None:
    assert (
        page.evaluate(
            "() => matchMedia('(prefers-reduced-motion: no-preference)').matches"
        )
        is True
    )
    page.emulate_media(reduced_motion="reduce")
    assert (
        page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        is True
    )
    assert (
        page.evaluate(
            "() => matchMedia('(prefers-reduced-motion: no-preference)').matches"
        )
        is False
    )
    page.emulate_media(reduced_motion="no-preference")
    assert (
        page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        is False
    )
    assert (
        page.evaluate(
            "() => matchMedia('(prefers-reduced-motion: no-preference)').matches"
        )
        is True
    )
    page.emulate_media(reduced_motion="null")


def test_EM_009_should_keep_reduced_motion_and_color_emulation_after_reload(
    page: Page, server: Server
) -> None:
    # Pre-conditions
    assert (
        page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        is False
    )
    assert page.evaluate("() => matchMedia('(forced-colors: active)').matches") is False

    # Emulation
    page.emulate_media(forced_colors="active", reduced_motion="reduce")
    assert (
        page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        is True
    )
    assert page.evaluate("() => matchMedia('(forced-colors: active)').matches") is True

    # Force CanonicalBrowsingContext replacement in Firefox.
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Cross-Origin-Opener-Policy", "same-origin")
        # Note: without 'onload', Firefox sometimes does not fire the load event
        # over the protocol. The reason is unclear.
        request.write(
            b"""
      <div>Hello there!</div>
      <script>window.onload = () => console.log('onload')</script>
    """
        )
        request.finish()

    server.set_route("/empty.html", handler)
    page.goto(server.EMPTY_PAGE)

    assert (
        page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        is True
    )
    assert page.evaluate("() => matchMedia('(forced-colors: active)').matches") is True


def test_EM_010_should_emulate_forced_colors(page: Page) -> None:
    assert page.evaluate("() => matchMedia('(forced-colors: none)').matches") is True
    page.emulate_media(forced_colors="none")
    assert page.evaluate("() => matchMedia('(forced-colors: none)').matches") is True
    assert page.evaluate("() => matchMedia('(forced-colors: active)').matches") is False
    page.emulate_media(forced_colors="active")
    assert page.evaluate("() => matchMedia('(forced-colors: none)').matches") is False
    assert page.evaluate("() => matchMedia('(forced-colors: active)').matches") is True
    page.emulate_media(forced_colors="null")
    assert page.evaluate("() => matchMedia('(forced-colors: none)').matches") is True


def test_EM_011_should_emulate_contrast(page: Page) -> None:
    assert to_match_media(page, "(prefers-contrast: no-preference)")
    page.emulate_media(contrast="no-preference")
    assert to_match_media(page, "(prefers-contrast: no-preference)")
    assert not to_match_media(page, "(prefers-contrast: more)")
    page.emulate_media(contrast="more")
    assert not to_match_media(page, "(prefers-contrast: no-preference)")
    assert to_match_media(page, "(prefers-contrast: more)")
    page.emulate_media(contrast="null")
    assert to_match_media(page, "(prefers-contrast: no-preference)")


def test_EM_012_should_report_hover_and_fine_pointer_for_desktop(
    page: Page,
) -> None:
    assert to_match_media(page, "(hover: hover)")
    assert to_match_media(page, "(pointer: fine)")
