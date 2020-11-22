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

import glob
import os
import shutil
import stat
import subprocess
import sys
import zipfile

from playwright.path_utils import get_file_dirname

driver_version = "0.170.0-next.1605573954344"


if not os.path.exists("driver"):
    os.makedirs("driver")
if not os.path.exists("playwright/driver"):
    os.makedirs("playwright/driver")

for platform in ["mac", "linux", "win32", "win32_x64"]:
    zip_file = f"playwright-cli-{driver_version}-{platform}.zip"
    if not os.path.exists("driver/" + zip_file):
        url = "https://playwright.azureedge.net/builds/cli/next/" + zip_file
        print("Fetching ", url)
        subprocess.check_call(["curl", "--http1.1", url, "-o", "driver/" + zip_file])

_dirname = get_file_dirname()
_build_dir = _dirname / "build"
if _build_dir.exists():
    shutil.rmtree(_build_dir)
_dist_dir = _dirname / "dist"
if _dist_dir.exists():
    shutil.rmtree(_dist_dir)
_egg_dir = _dirname / "playwright.egg-info"
if _egg_dir.exists():
    shutil.rmtree(_egg_dir)

subprocess.check_call("python setup.py sdist bdist_wheel", shell=True)

base_wheel_location = glob.glob("dist/*.whl")[0]
without_platform = base_wheel_location[:-7]

platform_map = {
    "darwin": "mac",
    "linux": "linux",
    "win32": "win32_x64" if sys.maxsize > 2 ** 32 else "win32",
}

for platform in ["mac", "linux", "win32", "win32_x64"]:
    zip_file = f"driver/playwright-cli-{driver_version}-{platform}.zip"
    with zipfile.ZipFile(zip_file, "r") as zip:
        zip.extractall(f"driver/{platform}")
    if platform_map[sys.platform] == platform:
        with zipfile.ZipFile(zip_file, "r") as zip:
            zip.extractall("playwright/driver")
        for file in os.listdir("playwright/driver"):
            if file == "playwright-cli" or file.startswith("ffmpeg"):
                print(f"playwright/driver/{file}")
                os.chmod(
                    f"playwright/driver/{file}",
                    os.stat(f"playwright/driver/{file}").st_mode | stat.S_IEXEC,
                )

    wheel = ""
    if platform == "mac":
        wheel = "macosx_10_13_x86_64.whl"
    if platform == "linux":
        wheel = "manylinux1_x86_64.whl"
    if platform == "win32":
        wheel = "win32.whl"
    if platform == "win32_x64":
        wheel = "win_amd64.whl"
    wheel_location = without_platform + wheel
    shutil.copy(base_wheel_location, wheel_location)
    with zipfile.ZipFile(wheel_location, "a") as zip:
        for file in os.listdir(f"driver/{platform}"):
            from_location = f"driver/{platform}/{file}"
            to_location = f"playwright/driver/{file}"
            if file == "playwright-cli" or file.startswith("ffmpeg"):
                os.chmod(from_location, os.stat(from_location).st_mode | stat.S_IEXEC)
            zip.write(from_location, to_location)

os.remove(base_wheel_location)
