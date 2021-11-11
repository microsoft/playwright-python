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
import sys
import zipfile
from pathlib import Path

from setuptools import find_packages, setup

try:
    from auditwheel.wheeltools import InWheel
except ImportError:
    InWheel = None
from wheel.bdist_wheel import bdist_wheel as BDistWheelCommand

driver_version = "1.18.0-next-1636539685000"


def extractall(zip: zipfile.ZipFile, path: str) -> None:
    for name in zip.namelist():
        member = zip.getinfo(name)
        extracted_path = zip.extract(member, path)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(extracted_path, attr)


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
        if self.all:
            # If building for all platforms
            platform_map = {
                "darwin": [
                    {
                        "zip_name": "mac",
                        "wheels": [
                            "macosx_10_13_x86_64.whl",
                            "macosx_11_0_universal2.whl",
                        ],
                    },
                    {
                        "zip_name": "mac-arm64",
                        "wheels": [
                            "macosx_11_0_arm64.whl",
                        ],
                    },
                ],
                "linux": [
                    {"zip_name": "linux", "wheels": ["manylinux1_x86_64.whl"]},
                    {
                        "zip_name": "linux-arm64",
                        "wheels": ["manylinux_2_17_aarch64.manylinux2014_aarch64.whl"],
                    },
                ],
                "win32": [
                    {
                        "zip_name": "win32_x64",
                        "wheels": ["win32.whl", "win_amd64.whl"],
                    }
                ],
            }
            platforms = [*platform_map.values()]
        else:
            # If building for only current platform
            platform_map = {
                "darwin": [
                    {
                        "zip_name": "mac",
                        "wheels": ["macosx_10_13_x86_64.whl"],
                    },
                ],
                "linux": [{"zip_name": "linux", "wheels": ["manylinux1_x86_64.whl"]}],
                "win32": [
                    {
                        "zip_name": "win32_x64",
                        "wheels": ["win_amd64.whl"],
                    }
                ],
            }
            platforms = [platform_map[sys.platform]]
        for platform in platforms:
            for arch in platform:
                zip_file = f"playwright-{driver_version}-{arch['zip_name']}.zip"
                if not os.path.exists("driver/" + zip_file):
                    url = f"https://playwright.azureedge.net/builds/driver/next/{zip_file}"
                    print(f"Fetching {url}")
                    # Don't replace this with urllib - Python won't have certificates to do SSL on all platforms.
                    subprocess.check_call(["curl", url, "-o", "driver/" + zip_file])
        base_wheel_location = glob.glob(os.path.join(self.dist_dir, "*.whl"))[0]
        without_platform = base_wheel_location[:-7]

        for platform in platforms:
            for arch in platform:
                zip_file = f"driver/playwright-{driver_version}-{arch['zip_name']}.zip"
                with zipfile.ZipFile(zip_file, "r") as zip:
                    extractall(zip, f"driver/{arch['zip_name']}")
                if platform_map[sys.platform][0] in platform:
                    with zipfile.ZipFile(zip_file, "r") as zip:
                        extractall(zip, "playwright/driver")
                for wheel in arch["wheels"]:
                    wheel_location = without_platform + wheel
                    shutil.copy(base_wheel_location, wheel_location)
                    with zipfile.ZipFile(wheel_location, "a") as zip:
                        driver_root = os.path.abspath(f"driver/{arch['zip_name']}")
                        for dir_path, _, files in os.walk(driver_root):
                            for file in files:
                                from_path = os.path.join(dir_path, file)
                                to_path = os.path.relpath(from_path, driver_root)
                                zip.write(from_path, f"playwright/driver/{to_path}")
                        zip.writestr(
                            "playwright/driver/README.md", f"{wheel} driver package"
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


setup(
    name="playwright",
    author="Microsoft Corporation",
    author_email="",
    description="A high-level API to automate web browsers",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/Microsoft/playwright-python",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=[
        "websockets>=8.1",
        "greenlet>=1.0.0",
        "pyee>=8.0.1",
        "typing-extensions;python_version<='3.8'",
    ],
    classifiers=[
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    cmdclass={"bdist_wheel": PlaywrightBDistWheelCommand},
    use_scm_version={
        "version_scheme": "post-release",
        "write_to": "playwright/_repo_version.py",
        "write_to_template": 'version = "{version}"\n',
    },
    setup_requires=["setuptools-scm==6.3.2", "wheel==0.37.0"],
    entry_points={
        "console_scripts": [
            "playwright=playwright.__main__:main",
        ],
        "pyinstaller40": ["hook-dirs=playwright._impl.__pyinstaller:get_hook_dirs"],
    },
)
