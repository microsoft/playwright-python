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
import platform
import shutil
import subprocess
import sys
import zipfile
from typing import Dict

driver_version = "1.49.1"

base_wheel_bundles = [
    {
        "wheel": "macosx_10_13_x86_64.whl",
        "machine": "x86_64",
        "platform": "darwin",
        "zip_name": "mac",
    },
    {
        "wheel": "macosx_11_0_universal2.whl",
        "machine": "x86_64",
        "platform": "darwin",
        "zip_name": "mac",
    },
    {
        "wheel": "macosx_11_0_arm64.whl",
        "machine": "arm64",
        "platform": "darwin",
        "zip_name": "mac-arm64",
    },
    {
        "wheel": "manylinux1_x86_64.whl",
        "machine": "x86_64",
        "platform": "linux",
        "zip_name": "linux",
    },
    {
        "wheel": "manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
        "machine": "aarch64",
        "platform": "linux",
        "zip_name": "linux-arm64",
    },
    {
        "wheel": "win32.whl",
        "machine": "i386",
        "platform": "win32",
        "zip_name": "win32_x64",
    },
    {
        "wheel": "win_amd64.whl",
        "machine": "amd64",
        "platform": "win32",
        "zip_name": "win32_x64",
    },
]

if len(sys.argv) == 2 and sys.argv[1] == "--list-wheels":
    for bundle in base_wheel_bundles:
        print(bundle["wheel"])
    exit(0)

from setuptools import setup  # noqa: E402

try:
    from auditwheel.wheeltools import InWheel
except ImportError:
    InWheel = None
from wheel.bdist_wheel import bdist_wheel as BDistWheelCommand  # noqa: E402


def extractall(zip: zipfile.ZipFile, path: str) -> None:
    for name in zip.namelist():
        member = zip.getinfo(name)
        extracted_path = zip.extract(member, path)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(extracted_path, attr)


def download_driver(zip_name: str) -> None:
    zip_file = f"playwright-{driver_version}-{zip_name}.zip"
    if os.path.exists("driver/" + zip_file):
        return
    url = "https://playwright.azureedge.net/builds/driver/"
    if (
        "-alpha" in driver_version
        or "-beta" in driver_version
        or "-next" in driver_version
    ):
        url = url + "next/"
    url = url + zip_file
    print(f"Fetching {url}")
    # Don't replace this with urllib - Python won't have certificates to do SSL on all platforms.
    subprocess.check_call(["curl", url, "-o", "driver/" + zip_file])


class PlaywrightBDistWheelCommand(BDistWheelCommand):
    def run(self) -> None:
        super().run()
        os.makedirs("driver", exist_ok=True)
        os.makedirs("playwright/driver", exist_ok=True)
        self._download_and_extract_local_driver()

        wheel = None
        if os.getenv("PLAYWRIGHT_TARGET_WHEEL", None):
            wheel = list(
                filter(
                    lambda wheel: wheel["wheel"]
                    == os.getenv("PLAYWRIGHT_TARGET_WHEEL"),
                    base_wheel_bundles,
                )
            )[0]
        else:
            wheel = list(
                filter(
                    lambda wheel: wheel["platform"] == sys.platform
                    and wheel["machine"] == platform.machine().lower(),
                    base_wheel_bundles,
                )
            )[0]
        assert wheel
        self._build_wheel(wheel)

    def _build_wheel(
        self,
        wheel_bundle: Dict[str, str],
    ) -> None:
        assert self.dist_dir
        base_wheel_location: str = glob.glob(os.path.join(self.dist_dir, "*.whl"))[0]
        without_platform = base_wheel_location[:-7]
        download_driver(wheel_bundle["zip_name"])
        zip_file = f"driver/playwright-{driver_version}-{wheel_bundle['zip_name']}.zip"
        with zipfile.ZipFile(zip_file, "r") as zip:
            extractall(zip, f"driver/{wheel_bundle['zip_name']}")
        wheel_location = without_platform + wheel_bundle["wheel"]
        shutil.copy(base_wheel_location, wheel_location)
        with zipfile.ZipFile(
            wheel_location, mode="a", compression=zipfile.ZIP_DEFLATED
        ) as zip:
            driver_root = os.path.abspath(f"driver/{wheel_bundle['zip_name']}")
            for dir_path, _, files in os.walk(driver_root):
                for file in files:
                    from_path = os.path.join(dir_path, file)
                    to_path = os.path.relpath(from_path, driver_root)
                    zip.write(from_path, f"playwright/driver/{to_path}")
            zip.writestr(
                "playwright/driver/README.md",
                f"{wheel_bundle['wheel']} driver package",
            )
        os.remove(base_wheel_location)
        for whlfile in glob.glob(os.path.join(self.dist_dir, "*.whl")):
            os.makedirs("wheelhouse", exist_ok=True)
            if InWheel:
                wheelhouse_whl = os.path.join("wheelhouse", os.path.basename(whlfile))
                shutil.move(whlfile, wheelhouse_whl)
                with InWheel(in_wheel=wheelhouse_whl, out_wheel=whlfile):
                    print(f"Updating RECORD file of {whlfile}")
        print("Copying new wheels")
        shutil.rmtree("wheelhouse")

    def _download_and_extract_local_driver(
        self,
    ) -> None:
        zip_names_for_current_system = set(
            map(
                lambda wheel: wheel["zip_name"],
                filter(
                    lambda wheel: wheel["machine"] == platform.machine().lower()
                    and wheel["platform"] == sys.platform,
                    base_wheel_bundles,
                ),
            )
        )
        assert len(zip_names_for_current_system) == 1
        zip_name = zip_names_for_current_system.pop()
        download_driver(zip_name)
        zip_file = f"driver/playwright-{driver_version}-{zip_name}.zip"
        with zipfile.ZipFile(zip_file, "r") as zip:
            extractall(zip, "playwright/driver")


setup(
    cmdclass={"bdist_wheel": PlaywrightBDistWheelCommand},
)
