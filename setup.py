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
from typing import Dict, List

from setuptools import setup

try:
    from auditwheel.wheeltools import InWheel
except ImportError:
    InWheel = None
from wheel.bdist_wheel import bdist_wheel as BDistWheelCommand

driver_version = "1.39.0"


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
    user_options = BDistWheelCommand.user_options + [
        ("all", "a", "create wheels for all platforms")
    ]
    boolean_options = BDistWheelCommand.boolean_options + ["all"]

    def initialize_options(self) -> None:
        super().initialize_options()
        self.all = False

    def run(self) -> None:
        shutil.rmtree("build", ignore_errors=True)
        shutil.rmtree("dist", ignore_errors=True)
        shutil.rmtree("playwright.egg-info", ignore_errors=True)
        super().run()
        os.makedirs("driver", exist_ok=True)
        os.makedirs("playwright/driver", exist_ok=True)
        base_wheel_bundles: List[Dict[str, str]] = [
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
        self._download_and_extract_local_driver(base_wheel_bundles)

        wheels = base_wheel_bundles
        if not self.all:
            # Limit to 1, since for MacOS e.g. we have multiple wheels for the same platform and architecture and Conda expects 1.
            wheels = list(
                filter(
                    lambda wheel: wheel["platform"] == sys.platform
                    and wheel["machine"] == platform.machine().lower(),
                    base_wheel_bundles,
                )
            )[:1]
        self._build_wheels(wheels)

    def _build_wheels(
        self,
        wheels: List[Dict[str, str]],
    ) -> None:
        base_wheel_location: str = glob.glob(os.path.join(self.dist_dir, "*.whl"))[0]
        without_platform = base_wheel_location[:-7]
        for wheel_bundle in wheels:
            download_driver(wheel_bundle["zip_name"])
            zip_file = (
                f"driver/playwright-{driver_version}-{wheel_bundle['zip_name']}.zip"
            )
            with zipfile.ZipFile(zip_file, "r") as zip:
                extractall(zip, f"driver/{wheel_bundle['zip_name']}")
            wheel_location = without_platform + wheel_bundle["wheel"]
            shutil.copy(base_wheel_location, wheel_location)
            with zipfile.ZipFile(wheel_location, "a") as zip:
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
        if InWheel:
            for whlfile in glob.glob(os.path.join(self.dist_dir, "*.whl")):
                os.makedirs("wheelhouse", exist_ok=True)
                with InWheel(
                    in_wheel=whlfile,
                    out_wheel=os.path.join("wheelhouse", os.path.basename(whlfile)),
                ):
                    print(f"Updating RECORD file of {whlfile}")
            shutil.rmtree(self.dist_dir)
            print("Copying new wheels")
            shutil.move("wheelhouse", self.dist_dir)
        else:
            print("auditwheel not installed, not updating RECORD file")

    def _download_and_extract_local_driver(
        self,
        wheels: List[Dict[str, str]],
    ) -> None:
        zip_names_for_current_system = set(
            map(
                lambda wheel: wheel["zip_name"],
                filter(
                    lambda wheel: wheel["machine"] == platform.machine().lower()
                    and wheel["platform"] == sys.platform,
                    wheels,
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
    name="playwright",
    author="Microsoft Corporation",
    author_email="",
    description="A high-level API to automate web browsers",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license="Apache-2.0",
    url="https://github.com/Microsoft/playwright-python",
    project_urls={
        "Release notes": "https://github.com/microsoft/playwright-python/releases",
    },
    packages=[
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
        "playwright._impl",
        "playwright._impl.__pyinstaller",
    ],
    include_package_data=True,
    install_requires=[
        "greenlet==3.0.0",
        "pyee==11.0.1",
        "typing-extensions;python_version<='3.8'",
    ],
    # TODO: Can be removed once we migrate to pypa/build or pypa/installer.
    setup_requires=["setuptools-scm==8.0.4", "wheel==0.41.2"],
    classifiers=[
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    cmdclass={"bdist_wheel": PlaywrightBDistWheelCommand},
    entry_points={
        "console_scripts": [
            "playwright=playwright.__main__:main",
        ],
        "pyinstaller40": ["hook-dirs=playwright._impl.__pyinstaller:get_hook_dirs"],
    },
)
