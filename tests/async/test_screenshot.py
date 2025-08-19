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

from pathlib import Path
from typing import Callable

from PIL import Image

from playwright.async_api import Page
from tests.server import Server
from tests.utils import must


def assert_image_file_format(path: Path, image_format: str) -> None:
    with Image.open(path) as img:
        assert img.format == image_format


async def test_should_screenshot_with_mask(
    page: Page, server: Server, assert_to_be_golden: Callable[[bytes, str], None]
) -> None:
    await page.set_viewport_size(
        {
            "width": 500,
            "height": 500,
        }
    )
    await page.goto(server.PREFIX + "/grid.html")
    assert_to_be_golden(
        await page.screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work-with-page.png",
    )
    assert_to_be_golden(
        await page.locator("body").screenshot(mask=[page.locator("div").nth(5)]),
        "mask-should-work-with-locator.png",
    )
    assert_to_be_golden(
        await must(await page.query_selector("body")).screenshot(
            mask=[page.locator("div").nth(5)]
        ),
        "mask-should-work-with-element-handle.png",
    )


async def test_should_infer_screenshot_type_from_path(
    page: Page, tmp_path: Path
) -> None:
    output_png_file = tmp_path / "foo.png"
    await page.screenshot(path=output_png_file)
    assert_image_file_format(output_png_file, "PNG")

    output_jpeg_file = tmp_path / "bar.jpeg"
    await page.screenshot(path=output_jpeg_file)
    assert_image_file_format(output_jpeg_file, "JPEG")

    output_jpg_file = tmp_path / "bar.jpg"
    await page.screenshot(path=output_jpg_file)
    assert_image_file_format(output_jpg_file, "JPEG")


async def test_should_screenshot_with_type_argument(page: Page, tmp_path: Path) -> None:
    output_jpeg_with_png_extension = tmp_path / "foo_jpeg.png"
    await page.screenshot(path=output_jpeg_with_png_extension, type="jpeg")
    assert_image_file_format(output_jpeg_with_png_extension, "JPEG")

    output_png_with_jpeg_extension = tmp_path / "bar_png.jpeg"
    await page.screenshot(path=output_png_with_jpeg_extension, type="png")
    assert_image_file_format(output_png_with_jpeg_extension, "PNG")
