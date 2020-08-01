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
import subprocess
import zipfile

from playwright.path_utils import get_file_dirname

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

pack_wheel_drivers = [
    ("driver-linux", "manylinux1_x86_64.whl"),
    ("driver-macos", "macosx_10_13_x86_64.whl"),
    ("driver-win.exe", "win_amd64.whl"),
]

for driver, wheel in pack_wheel_drivers:
    wheel_location = without_platform + wheel
    shutil.copy(base_wheel_location, wheel_location)
    from_location = f"driver/out/{driver}"
    to_location = f"playwright/drivers/{driver}"
    with zipfile.ZipFile(wheel_location, "a") as zipf:
        zipf.write(from_location, to_location)
os.remove(base_wheel_location)
