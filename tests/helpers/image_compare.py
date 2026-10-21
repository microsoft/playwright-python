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

assert_to_match_golden() is expect(buffer).toMatchSnapshot(name, { maxDiffPixels })
against tests/golden-<browser>/<name>: the matcher of @playwright/test compares with
pixelmatch at the threshold 0.2 (packages/utils/comparators.ts, compareImages()), as
the configs of the upstream tests set no other comparator. compare_images() is a port
of comparePNGs() in tests/config/comparator.ts, which compares with the ssim-cie94
comparator and no threshold. compare() and the classes and functions above it are a
port of packages/utils/image_tools: compare.ts, stats.ts, colorUtils.ts and
imageChannel.ts; count_different_pixels() is utils.compare() of the tests. The diff
image that compare() draws is not ported. is_lossless_webp() is a port of
isLosslessWebp() in packages/utils/webp/webp.ts.
"""

import io
import math
import struct
from functools import lru_cache
from itertools import accumulate
from operator import add, mul
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, cast

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


# colorUtils.ts


def blend_with_white(c: float, a: float) -> float:
    return 255 + (c - 255) * a


def rgb2gray(r: int, g: int, b: int) -> int:
    # NOTE: this is the exact integer formula from SSIM.js.
    # See https://github.com/obartra/ssim/blob/ca8e3c6a6ff5f4f2e232239e0c3d91806f3c97d5/src/matlab/rgb2gray.ts#L56
    return (77 * r + 150 * g + 29 * b + 128) >> 8


# Perceived color difference defined by CIE94.
# See https://en.wikipedia.org/wiki/Color_difference#CIE94
#
# The result of 1.0 is a "just-noticeable difference".
#
# Other results interpretation (taken from http://zschuessler.github.io/DeltaE/learn/):
#   < 1.0     Not perceptible by human eyes.
#   1-2        Perceptible through close observation.
#   2-10       Perceptible at a glance.
#   11-49      Colors are more similar than opposite
#   100        Colors are exact opposite
# Python: the result for a pair of colors is kept: a screenshot has few colors.
@lru_cache(maxsize=None)
def color_delta_e94(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    l1, a1, b1 = _lab(rgb1)
    l2, a2, b2 = _lab(rgb2)
    delta_l = l1 - l2
    delta_a = a1 - a2
    delta_b = b1 - b2
    c1 = math.sqrt(a1**2 + b1**2)
    c2 = math.sqrt(a2**2 + b2**2)
    delta_c = c1 - c2
    delta_h = delta_a**2 + delta_b**2 - delta_c**2
    delta_h = 0 if delta_h < 0 else math.sqrt(delta_h)
    # The k1, k2, kL, kC, kH values for "graphic arts" applications.
    # See https://en.wikipedia.org/wiki/Color_difference#CIE94
    k1 = 0.045
    k2 = 0.015
    k_l = 1
    k_c = 1
    k_h = 1

    s_c = 1.0 + k1 * c1
    s_h = 1.0 + k2 * c1
    s_l = 1

    return math.sqrt(
        (delta_l / s_l / k_l) ** 2
        + (delta_c / s_c / k_c) ** 2
        + (delta_h / s_h / k_h) ** 2
    )


@lru_cache(maxsize=None)
def _lab(rgb: Tuple[int, int, int]) -> List[float]:
    return xyz2lab(srgb2xyz(rgb))


# sRGB -> 1-normalized XYZ (i.e. Y ∈ [0, 1]) with D65 illuminant
# See https://en.wikipedia.org/wiki/SRGB#From_sRGB_to_CIE_XYZ
def srgb2xyz(rgb: Sequence[int]) -> List[float]:
    r = rgb[0] / 255
    g = rgb[1] / 255
    b = rgb[2] / 255
    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
    return [
        (r * 0.4124 + g * 0.3576 + b * 0.1805),
        (r * 0.2126 + g * 0.7152 + b * 0.0722),
        (r * 0.0193 + g * 0.1192 + b * 0.9505),
    ]


_sigma_pow2 = 6 * 6 / 29 / 29
_sigma_pow3 = 6 * 6 * 6 / 29 / 29 / 29


# 1-normalized CIE XYZ with D65 to L*a*b*
# See https://en.wikipedia.org/wiki/CIELAB_color_space#From_CIEXYZ_to_CIELAB
def xyz2lab(xyz: Sequence[float]) -> List[float]:
    x = xyz[0] / 0.950489
    y = xyz[1]
    z = xyz[2] / 1.088840

    fx = x ** (1 / 3) if x > _sigma_pow3 else x / 3 / _sigma_pow2 + 4 / 29
    fy = y ** (1 / 3) if y > _sigma_pow3 else y / 3 / _sigma_pow2 + 4 / 29
    fz = z ** (1 / 3) if z > _sigma_pow3 else z / 3 / _sigma_pow2 + 4 / 29

    l_ = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return [l_, a, b]


# imageChannel.ts


class ImageChannel:
    @staticmethod
    def into_rgb(
        width: int,
        height: int,
        data: bytes,
        padding_size: int = 0,
        padding_color_odd: Sequence[int] = (255, 0, 255),
        padding_color_even: Sequence[int] = (0, 255, 0),
    ) -> List["ImageChannel"]:
        new_width = width + 2 * padding_size
        new_height = height + 2 * padding_size
        # Python: the channels of the image come from slices of the RGBA data;
        # upstream reads them pixel by pixel. A pixel that is not opaque is
        # blended with white, as upstream; a Uint8Array keeps the integer part.
        red = list(data[0::4])
        green = list(data[1::4])
        blue = list(data[2::4])
        alphas = data[3::4]
        for offset, alpha_byte in enumerate(alphas):
            if alpha_byte == 255:
                continue
            alpha = alpha_byte / 255
            red[offset] = int(blend_with_white(red[offset], alpha))
            green[offset] = int(blend_with_white(green[offset], alpha))
            blue[offset] = int(blend_with_white(blue[offset], alpha))
        r: List[int] = []
        g: List[int] = []
        b: List[int] = []

        def padding(y: int, x: int) -> Sequence[int]:
            return padding_color_even if (y + x) % 2 == 0 else padding_color_odd

        for y in range(new_height):
            if padding_size <= y < new_height - padding_size:
                left = [padding(y, x) for x in range(padding_size)]
                right = [
                    padding(y, x) for x in range(new_width - padding_size, new_width)
                ]
                offset = (y - padding_size) * width
                end = offset + width
                for channel, source, index in (
                    (r, red, 0),
                    (g, green, 1),
                    (b, blue, 2),
                ):
                    channel.extend(color[index] for color in left)
                    channel.extend(source[offset:end])
                    channel.extend(color[index] for color in right)
            else:
                row = [padding(y, x) for x in range(new_width)]
                r.extend(color[0] for color in row)
                g.extend(color[1] for color in row)
                b.extend(color[2] for color in row)
        return [
            ImageChannel(new_width, new_height, r),
            ImageChannel(new_width, new_height, g),
            ImageChannel(new_width, new_height, b),
        ]

    def __init__(self, width: int, height: int, data: List[int]) -> None:
        self.data = data
        self.width = width
        self.height = height

    def get(self, x: int, y: int) -> int:
        return self.data[y * self.width + x]

    def bound_xy(self, x: int, y: int) -> Tuple[int, int]:
        return (
            min(max(x, 0), self.width - 1),
            min(max(y, 0), self.height - 1),
        )


# stats.ts

# Image channel has a 8-bit depth.
DYNAMIC_RANGE = 2**8 - 1


def ssim(stats: "FastStats", x1: int, y1: int, x2: int, y2: int) -> float:
    mean1 = stats.mean_c1(x1, y1, x2, y2)
    mean2 = stats.mean_c2(x1, y1, x2, y2)
    var1 = stats.variance_c1(x1, y1, x2, y2)
    var2 = stats.variance_c2(x1, y1, x2, y2)
    cov = stats.covariance(x1, y1, x2, y2)
    c1 = (0.01 * DYNAMIC_RANGE) ** 2
    c2 = (0.03 * DYNAMIC_RANGE) ** 2
    return (
        (2 * mean1 * mean2 + c1)
        * (2 * cov + c2)
        / (mean1**2 + mean2**2 + c1)
        / (var1 + var2 + c2)
    )


def _partial_sums(values: Sequence[int], width: int, height: int) -> List[int]:
    """The sums of the rectangles from (0, 0), by rows; the recalc() of upstream."""
    result: List[int] = []
    previous: List[int] = [0] * width
    for y in range(height):
        start = y * width
        end_of_row = start + width
        row = list(accumulate(values[start:end_of_row]))
        row = list(map(add, row, previous))
        result.extend(row)
        previous = row
    return result


class FastStats:
    def __init__(self, c1: ImageChannel, c2: ImageChannel) -> None:
        self.c1 = c1
        self.c2 = c2
        width, height = c1.width, c1.height

        # Python: the partial sums are computed by rows, which gives the same sums.
        self._partial_sum_c1 = _partial_sums(c1.data, width, height)
        self._partial_sum_c2 = _partial_sums(c2.data, width, height)
        self._partial_sum_sq1 = _partial_sums(
            list(map(mul, c1.data, c1.data)), width, height
        )
        self._partial_sum_sq2 = _partial_sums(
            list(map(mul, c2.data, c2.data)), width, height
        )
        self._partial_sum_mult = _partial_sums(
            list(map(mul, c1.data, c2.data)), width, height
        )

    def _sum(self, partial_sum: List[int], x1: int, y1: int, x2: int, y2: int) -> int:
        width = self.c1.width
        result = partial_sum[y2 * width + x2]
        if y1 > 0:
            result -= partial_sum[(y1 - 1) * width + x2]
        if x1 > 0:
            result -= partial_sum[y2 * width + x1 - 1]
        if x1 > 0 and y1 > 0:
            result += partial_sum[(y1 - 1) * width + x1 - 1]
        return result

    def mean_c1(self, x1: int, y1: int, x2: int, y2: int) -> float:
        n = (y2 - y1 + 1) * (x2 - x1 + 1)
        return self._sum(self._partial_sum_c1, x1, y1, x2, y2) / n

    def mean_c2(self, x1: int, y1: int, x2: int, y2: int) -> float:
        n = (y2 - y1 + 1) * (x2 - x1 + 1)
        return self._sum(self._partial_sum_c2, x1, y1, x2, y2) / n

    def variance_c1(self, x1: int, y1: int, x2: int, y2: int) -> float:
        n = (y2 - y1 + 1) * (x2 - x1 + 1)
        return (
            self._sum(self._partial_sum_sq1, x1, y1, x2, y2)
            - (self._sum(self._partial_sum_c1, x1, y1, x2, y2) ** 2) / n
        ) / n

    def variance_c2(self, x1: int, y1: int, x2: int, y2: int) -> float:
        n = (y2 - y1 + 1) * (x2 - x1 + 1)
        return (
            self._sum(self._partial_sum_sq2, x1, y1, x2, y2)
            - (self._sum(self._partial_sum_c2, x1, y1, x2, y2) ** 2) / n
        ) / n

    def covariance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        n = (y2 - y1 + 1) * (x2 - x1 + 1)
        return (
            self._sum(self._partial_sum_mult, x1, y1, x2, y2)
            - self._sum(self._partial_sum_c1, x1, y1, x2, y2)
            * self._sum(self._partial_sum_c2, x1, y1, x2, y2)
            / n
        ) / n


# compare.ts

SSIM_WINDOW_RADIUS = 15
VARIANCE_WINDOW_RADIUS = 1


def compare(
    actual: bytes,
    expected: bytes,
    width: int,
    height: int,
    max_color_delta_e94: float = 1.0,
) -> int:
    """The number of pixels that differ between two RGBA images of the size."""
    # Python: two images with the same bytes have no different pixel.
    if actual == expected:
        return 0

    padding_size = max(VARIANCE_WINDOW_RADIUS, SSIM_WINDOW_RADIUS)
    padding_color_even = [255, 0, 255]
    padding_color_odd = [0, 255, 0]
    r1, g1, b1 = ImageChannel.into_rgb(
        width,
        height,
        expected,
        padding_size=padding_size,
        padding_color_even=padding_color_even,
        padding_color_odd=padding_color_odd,
    )
    r2, g2, b2 = ImageChannel.into_rgb(
        width,
        height,
        actual,
        padding_size=padding_size,
        padding_color_even=padding_color_even,
        padding_color_odd=padding_color_odd,
    )

    fast_r: Optional[FastStats] = None
    fast_g: Optional[FastStats] = None
    fast_b: Optional[FastStats] = None

    diff_count = 0
    padded_width = r1.width
    for y in range(padding_size, r1.height - padding_size):
        # Python: a row with the same pixels in both images takes the fast path
        # of upstream for each of its pixels.
        row = slice(
            y * padded_width + padding_size, (y + 1) * padded_width - padding_size
        )
        if (
            r1.data[row] == r2.data[row]
            and g1.data[row] == g2.data[row]
            and b1.data[row] == b2.data[row]
        ):
            continue
        for x in range(padding_size, padded_width - padding_size):
            # Fast-path: equal pixels.
            index = y * padded_width + x
            if (
                r1.data[index] == r2.data[index]
                and g1.data[index] == g2.data[index]
                and b1.data[index] == b2.data[index]
            ):
                continue

            # Compare pixel colors using the dE94 color difference formulae.
            # The dE94 is normalized so that the value of 1.0 is the "just-noticeable-difference".
            # Color difference below 1.0 is not noticeable to a human eye, so we can disregard it.
            # See https://en.wikipedia.org/wiki/Color_difference
            delta = color_delta_e94(
                (r1.data[index], g1.data[index], b1.data[index]),
                (r2.data[index], g2.data[index], b2.data[index]),
            )

            if delta <= max_color_delta_e94:
                continue

            if not fast_r or not fast_g or not fast_b:
                fast_r = FastStats(r1, r2)
                fast_g = FastStats(g1, g2)
                fast_b = FastStats(b1, b2)
            var_x1, var_y1 = r1.bound_xy(
                x - VARIANCE_WINDOW_RADIUS, y - VARIANCE_WINDOW_RADIUS
            )
            var_x2, var_y2 = r1.bound_xy(
                x + VARIANCE_WINDOW_RADIUS, y + VARIANCE_WINDOW_RADIUS
            )
            var1 = (
                fast_r.variance_c1(var_x1, var_y1, var_x2, var_y2)
                + fast_g.variance_c1(var_x1, var_y1, var_x2, var_y2)
                + fast_b.variance_c1(var_x1, var_y1, var_x2, var_y2)
            )
            var2 = (
                fast_r.variance_c2(var_x1, var_y1, var_x2, var_y2)
                + fast_g.variance_c2(var_x1, var_y1, var_x2, var_y2)
                + fast_b.variance_c2(var_x1, var_y1, var_x2, var_y2)
            )
            # if this pixel is a part of a flood fill of a 3x3 square of either of the images, then it cannot be
            # anti-aliasing pixel so it must be a pixel difference.
            if var1 == 0 or var2 == 0:
                diff_count += 1
                continue

            ssim_x1, ssim_y1 = r1.bound_xy(
                x - SSIM_WINDOW_RADIUS, y - SSIM_WINDOW_RADIUS
            )
            ssim_x2, ssim_y2 = r1.bound_xy(
                x + SSIM_WINDOW_RADIUS, y + SSIM_WINDOW_RADIUS
            )
            ssim_rgb = (
                ssim(fast_r, ssim_x1, ssim_y1, ssim_x2, ssim_y2)
                + ssim(fast_g, ssim_x1, ssim_y1, ssim_x2, ssim_y2)
                + ssim(fast_b, ssim_x1, ssim_y1, ssim_x2, ssim_y2)
            ) / 3.0
            is_antialiased = ssim_rgb >= 0.99
            if not is_antialiased:
                diff_count += 1

    return diff_count


# comparators.ts


def _pad_image_to_size(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """Port of padImageToSize() in packages/isomorphic/imageUtils.ts."""
    if image.size == size:
        return image
    padded = Image.new("RGBA", size, (0, 0, 0, 0))
    padded.paste(image, (0, 0))
    return padded


def count_different_pixels(actual: bytes, expected: bytes) -> int:
    """The number of pixels that differ: compare() on two encoded images of one size."""
    actual_image = decode_image(actual)
    expected_image = decode_image(expected)
    assert actual_image.size == expected_image.size
    width, height = expected_image.size
    return compare(actual_image.tobytes(), expected_image.tobytes(), width, height)


def compare_images(
    actual: bytes, expected: bytes, max_diff_pixels: int = 0
) -> Optional[str]:
    """Port of comparePNGs(): None when the images match, else the error message.

    Like upstream, the comparison is strict: ssim-cie94 with no threshold, and
    maxDiffPixels different pixels at most.
    """
    actual_image = decode_image(actual)
    expected_image = decode_image(expected)
    size = (
        max(expected_image.width, actual_image.width),
        max(expected_image.height, actual_image.height),
    )
    sizes_mismatch_error = ""
    if expected_image.size != actual_image.size:
        sizes_mismatch_error = (
            f"Expected an image {expected_image.width}px by {expected_image.height}px,"
            f" received {actual_image.width}px by {actual_image.height}px. "
        )
        actual_image = _pad_image_to_size(actual_image, size)
        expected_image = _pad_image_to_size(expected_image, size)
    count = compare(
        actual_image.tobytes(),
        expected_image.tobytes(),
        size[0],
        size[1],
        # All ΔE* formulae are originally designed to have the difference of 1.0 stand for a "just noticeable difference" (JND).
        # See https://en.wikipedia.org/wiki/Color_difference#CIELAB_%CE%94E*
        max_color_delta_e94=1.0,
    )
    ratio = (
        math.ceil(count / (expected_image.width * expected_image.height) * 100) / 100
    )
    pixels_mismatch_error = (
        f"{count} pixels (ratio {ratio:.2f} of all image pixels) are different."
        if count > max_diff_pixels
        else ""
    )
    if pixels_mismatch_error or sizes_mismatch_error:
        return sizes_mismatch_error + pixels_mismatch_error
    return None


def assert_to_match_golden(
    browser_name: str, actual: bytes, golden_name: str, max_diff_pixels: int = 0
) -> None:
    """expect(actual).toMatchSnapshot(golden_name, { maxDiffPixels }): pixelmatch at the
    threshold 0.2, as the matcher compares when the config sets no comparator."""
    golden = (_tests_dir / f"golden-{browser_name}" / golden_name).read_bytes()
    actual_image = decode_image(actual)
    golden_image = decode_image(golden)
    assert actual_image.size == golden_image.size, (
        f"Expected an image {golden_image.width}px by {golden_image.height}px,"
        f" received {actual_image.width}px by {actual_image.height}px."
    )
    width, height = golden_image.size
    count = pixelmatch(
        from_PIL_to_raw_data(golden_image),
        from_PIL_to_raw_data(actual_image),
        width,
        height,
        threshold=0.2,
    )
    ratio = math.ceil(count / (width * height) * 100) / 100
    assert count <= max_diff_pixels, (
        f"Screenshot comparison failed for {golden_name}: {count} pixels"
        f" (ratio {ratio:.2f} of all image pixels) are different."
    )


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
