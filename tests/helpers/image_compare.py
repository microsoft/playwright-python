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

"""Image helpers for the screenshot tests, in both flavors.

compare_images() is a port of comparePNGs() in tests/config/comparator.ts.
assert_to_match_golden() is toMatchSnapshot() with maxDiffPixels: it compares with
tests/golden-<browser>/<name> like the assert_to_be_golden fixture, but allows some
different pixels. is_lossless_webp() is a port of isLosslessWebp() in
packages/utils/webp/webp.ts.
"""

import io
import struct
from pathlib import Path
from typing import Optional, Tuple, cast

from PIL import Image
from pixelmatch import pixelmatch
from pixelmatch.contrib.PIL import from_PIL_to_raw_data

_tests_dir = Path(__file__).parent.parent


def decode_image(data: bytes) -> Image.Image:
    """Decodes a png, jpeg or webp image to RGBA."""
    return Image.open(io.BytesIO(data)).convert("RGBA")


def pixel(image: Image.Image, x: int, y: int) -> Tuple[int, int, int, int]:
    """The RGBA value of one pixel."""
    return cast(Tuple[int, int, int, int], image.getpixel((x, y)))


def count_different_pixels(
    actual: bytes, expected: bytes, threshold: float
) -> Optional[int]:
    """The number of pixels that differ, or None when the image sizes differ."""
    actual_image = decode_image(actual)
    expected_image = decode_image(expected)
    if actual_image.size != expected_image.size:
        return None
    width, height = expected_image.size
    return pixelmatch(
        from_PIL_to_raw_data(actual_image),
        from_PIL_to_raw_data(expected_image),
        width,
        height,
        threshold=threshold,
    )


def compare_images(actual: bytes, expected: bytes, max_diff_pixels: int = 0) -> bool:
    """True when the images are the same: comparePNGs(...) === null.

    Like upstream, the threshold is strict: any change of a pixel counts.
    """
    count = count_different_pixels(actual, expected, threshold=0)
    return count is not None and count <= max_diff_pixels


def assert_to_match_golden(
    browser_name: str, actual: bytes, golden_name: str, max_diff_pixels: int
) -> None:
    """expect(actual).toMatchSnapshot(golden_name, { maxDiffPixels })."""
    golden = (_tests_dir / f"golden-{browser_name}" / golden_name).read_bytes()
    count = count_different_pixels(actual, golden, threshold=0.2)
    assert count is not None, "Image size differs to golden image"
    assert (
        count <= max_diff_pixels
    ), f"{count} pixels differ from {golden_name}, allowed: {max_diff_pixels}"


def is_lossless_webp(buffer: bytes) -> bool:
    """True when the webp image has a lossless (VP8L) bitstream."""
    if len(buffer) < 16 or buffer[0:4] != b"RIFF" or buffer[8:12] != b"WEBP":
        return False
    offset = 12
    while offset + 8 <= len(buffer):
        (fourcc,) = struct.unpack_from("4s", buffer, offset)
        if fourcc == b"VP8L":
            return True
        if fourcc == b"VP8 ":
            return False
        # Skip this chunk (8-byte header + payload, padded to an even size).
        (size,) = struct.unpack_from("<I", buffer, offset + 4)
        offset += 8 + size + (size & 1)
    return False
