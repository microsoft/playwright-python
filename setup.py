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
from pathlib import Path
from typing import Dict

# The driver is assembled by scripts/build_driver.py from published artifacts:
# the playwright-core npm package (version pinned in DRIVER_VERSION) and the
# official Node.js binaries (pinned in NODE_VERSION). DRIVER_VERSION is the
# single source of truth (also read by CI) and is baked into the staged bundle
# filenames, so it doubles as the build cache key: a roll changes DRIVER_VERSION,
# which changes the filenames.
driver_version = (Path(__file__).parent / "DRIVER_VERSION").read_text().strip()

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
    {
        "wheel": "win_arm64.whl",
        "machine": "arm64",
        "platform": "win32",
        "zip_name": "win32_arm64",
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


def ensure_driver_bundle(zip_name: str) -> None:
    destination_path = f"driver/playwright-{driver_version}-{zip_name}.zip"
    if os.path.exists(destination_path):
        return
    # Assemble this platform's bundle by downloading the playwright-core npm
    # package and the matching Node.js binary. Only the requested platform is
    # built, so a wheel build downloads just the one Node.js binary it needs.
    build_script = os.path.join(os.path.dirname(__file__), "scripts", "build_driver.py")
    subprocess.check_call([sys.executable, build_script, zip_name])
    if not os.path.exists(destination_path):
        raise RuntimeError(
            f"Driver bundle {destination_path} was not produced by scripts/build_driver.py."
        )


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
        ensure_driver_bundle(wheel_bundle["zip_name"])
        # Although the build produces every platform's bundle, only this wheel's
        # target platform driver is extracted and packed below, so the wheel
        # stays single-platform.
        zip_file = f"driver/playwright-{driver_version}-{wheel_bundle['zip_name']}.zip"
        extract_dir = f"driver/{wheel_bundle['zip_name']}"
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        with zipfile.ZipFile(zip_file, "r") as zip:
            extractall(zip, extract_dir)
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
                with InWheel(in_wheel=Path(wheelhouse_whl), out_wheel=Path(whlfile)):
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
        ensure_driver_bundle(zip_name)
        zip_file = f"driver/playwright-{driver_version}-{zip_name}.zip"
        if os.path.exists("playwright/driver"):
            shutil.rmtree("playwright/driver")
        with zipfile.ZipFile(zip_file, "r") as zip:
            extractall(zip, "playwright/driver")


setup(
    cmdclass={"bdist_wheel": PlaywrightBDistWheelCommand},
)
