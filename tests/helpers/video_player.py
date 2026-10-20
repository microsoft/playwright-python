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

"""Decodes recorded videos, for the video and screencast tests in both flavors.

VideoPlayer is a port of tests/library/videoPlayer.ts: it runs the ffmpeg that
Playwright installs (found through the driver's registry) and reads the frames with PIL.
The pixel helpers are ports of the helpers in tests/library/video.spec.ts and
tests/library/screencast.spec.ts.
"""

import functools
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from PIL import Image

from playwright._impl._driver import compute_driver_executable

_FIND_FFMPEG_SCRIPT = """
const { registry } = require(process.argv[1]);
process.stdout.write(registry.registry.findExecutable('ffmpeg').executablePathOrDie('python'));
"""

Pixel = Tuple[int, int, int, int]
PixelPredicate = Callable[[Pixel], bool]
Offset = Tuple[int, int]


@functools.lru_cache(maxsize=None)
def ffmpeg_executable() -> str:
    node, cli = compute_driver_executable()
    core_bundle = Path(cli).parent / "lib" / "coreBundle.js"
    result = subprocess.run(
        [node, "-e", _FIND_FFMPEG_SCRIPT, str(core_bundle)],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode()


class VideoPlayer:
    """Port of VideoPlayer in tests/library/videoPlayer.ts."""

    def __init__(self, file_name: Union[str, Path]) -> None:
        self.file_name = str(file_name)
        self._cache: Dict[int, Image.Image] = {}
        # Force output frame rate to 25 fps as otherwise it would produce one image per
        # timebase unit which is 1 / (25 * 1000).
        self.output = subprocess.run(
            [
                ffmpeg_executable(),
                "-i",
                self.file_name,
                "-r",
                "25",
                f"{self.file_name}-%04d.png",
            ],
            capture_output=True,
        ).stderr.decode(errors="replace")

        lines = self.output.split("\n")
        frames_line = next((line for line in lines if line.startswith("frame=")), None)
        if not frames_line:
            raise Exception(f"No frame data in the output:\n{self.output}")
        last_frame_index = frames_line.rfind("frame=")
        frames_line = frames_line[last_frame_index:]
        frames_match = re.search(r"frame=\s+(\d+)", frames_line)
        stream_line = next(
            line for line in lines if line.strip().startswith("Stream #0:0")
        )
        resolution_match = re.search(r", (\d+)x(\d+),", stream_line)
        fps_match = re.search(r", ([\d.]+) fps,", stream_line)
        duration_line = next(
            line for line in lines if line.strip().startswith("Duration")
        )
        duration_match = re.search(r"Duration: (\d+):(\d\d):(\d\d.\d\d)", duration_line)
        assert frames_match and resolution_match and fps_match and duration_match
        self.duration = (
            (int(duration_match[1]) * 60 + int(duration_match[2])) * 60
            + float(duration_match[3])
        ) * 1000
        self.frames = int(frames_match[1])
        self.video_width = int(resolution_match[1])
        self.video_height = int(resolution_match[2])
        self.fps = float(fps_match[1])

    def find_frame(
        self,
        frame_predicate: Callable[[bytes], bool],
        offset: Optional[Offset] = None,
    ) -> Optional[bytes]:
        for f in range(1, self.frames + 1):
            frame = self.frame(f, offset)
            if frame_predicate(frame):
                return frame
        return None

    def seek_last_frame(self, offset: Optional[Offset] = None) -> bytes:
        return self.frame(self.frames, offset)

    def frame(self, frame: int, offset: Optional[Offset] = None) -> bytes:
        """Returns the RGBA pixels of the 10x10 square at offset (x, y) of the frame."""
        x, y = offset or (10, 10)
        if frame not in self._cache:
            with Image.open(f"{self.file_name}-{frame:04d}.png") as image:
                self._cache[frame] = image.convert("RGBA")
        return self._cache[frame].crop((x, y, x + 10, y + 10)).tobytes()


def is_almost_red(pixel: Pixel) -> bool:
    r, g, b, alpha = pixel
    return r > 185 and g < 70 and b < 70 and alpha == 255


def is_almost_black(pixel: Pixel) -> bool:
    r, g, b, alpha = pixel
    return r < 70 and g < 70 and b < 70 and alpha == 255


def is_almost_white(pixel: Pixel) -> bool:
    r, g, b, alpha = pixel
    return r > 185 and g > 185 and b > 185 and alpha == 255


def is_almost_gray(pixel: Pixel) -> bool:
    r, g, b, alpha = pixel
    return 70 < r < 185 and 70 < g < 185 and 70 < b < 185 and alpha == 255


def find_pixel(pixels: bytes, pixel_predicate: PixelPredicate) -> Optional[Pixel]:
    for i in range(0, len(pixels), 4):
        pixel = (pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3])
        if pixel_predicate(pixel):
            return pixel
    return None


def every_pixel(pixels: bytes, pixel_predicate: PixelPredicate) -> bool:
    return not find_pixel(pixels, lambda pixel: not pixel_predicate(pixel))


def expect_all(pixels: bytes, pixel_predicate: PixelPredicate) -> None:
    bad_pixel = find_pixel(pixels, lambda pixel: not pixel_predicate(pixel))
    if not bad_pixel:
        return
    rgba = ", ".join(str(v) for v in bad_pixel)
    raise AssertionError(
        f"Expected all pixels to satisfy {pixel_predicate.__name__}, found bad pixel ({rgba})\n"
        f"Actual pixels=[{','.join(str(v) for v in pixels)}]"
    )


def expect_frames(
    video_file: Union[str, Path],
    size: Mapping[str, Any],
    pixel_predicate: PixelPredicate,
) -> None:
    video_player = VideoPlayer(video_file)
    assert video_player.duration > 0

    assert video_player.video_width == size["width"]
    assert video_player.video_height == size["height"]

    expect_all(video_player.seek_last_frame(), pixel_predicate)
    expect_all(video_player.seek_last_frame((size["width"] - 20, 10)), pixel_predicate)


def expect_red_frames(video_file: Union[str, Path], size: Mapping[str, Any]) -> None:
    expect_frames(video_file, size, is_almost_red)


def find_videos(video_dir: Union[str, Path]) -> List[Path]:
    return [
        Path(video_dir) / file
        for file in sorted(p.name for p in Path(video_dir).iterdir())
        if file.endswith("webm")
    ]
