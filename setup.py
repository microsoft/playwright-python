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
import typing
import zipfile

import setuptools
from wheel.bdist_wheel import bdist_wheel as BDistWheelCommand

driver_version = "1.9.0-next-1612400196000"


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

NoneType = type(None)


def extractall(zip: typing.Any, path: str) -> NoneType:
    for name in zip.namelist():
        member = zip.getinfo(name)
        extracted_path = zip._extract_member(member, path, None)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(extracted_path, attr)


class PlaywrightBDistWheelCommand(BDistWheelCommand):
    def run(self) -> None:
        if os.path.exists("build"):
            shutil.rmtree("build")
        if os.path.exists("dist"):
            shutil.rmtree("dist")
        if os.path.exists("playwright.egg-info"):
            shutil.rmtree("playwright.egg-info")
        super().run()
        os.makedirs("driver", exist_ok=True)
        os.makedirs("playwright/driver", exist_ok=True)
        for platform in ["mac", "linux", "win32", "win32_x64"]:
            zip_file = f"playwright-{driver_version}-{platform}.zip"
            if not os.path.exists("driver/" + zip_file):
                url = "https://playwright.azureedge.net/builds/driver/"
                if "-next" in driver_version:
                    url = url + "next/"
                url = url + zip_file
                print("Fetching ", url)
                subprocess.check_call(
                    ["curl", "--http1.1", url, "-o", "driver/" + zip_file]
                )
        base_wheel_location = glob.glob("dist/*.whl")[0]
        without_platform = base_wheel_location[:-7]
        platform_map = {
            "darwin": "mac",
            "linux": "linux",
            "win32": "win32_x64" if sys.maxsize > 2 ** 32 else "win32",
        }
        for platform in ["mac", "linux", "win32", "win32_x64"]:
            zip_file = f"driver/playwright-{driver_version}-{platform}.zip"
            with zipfile.ZipFile(zip_file, "r") as zip:
                extractall(zip, f"driver/{platform}")
            if platform_map[sys.platform] == platform:
                with zipfile.ZipFile(zip_file, "r") as zip:
                    extractall(zip, "playwright/driver")
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
                driver_root = os.path.abspath(f"driver/{platform}")
                for dir_path, dirs, files in os.walk(driver_root):
                    for file in files:
                        from_path = os.path.join(dir_path, file)
                        to_path = os.path.relpath(from_path, driver_root)
                        zip.write(from_path, f"playwright/driver/{to_path}")
            if platform == "mac":
                # Ship mac both as 10_13 as and 11_0 universal to work across Macs.
                universal_location = without_platform + "macosx_11_0_universal2.whl"
                shutil.copyfile(wheel_location, universal_location)
                with zipfile.ZipFile(universal_location, "a") as zip:
                    zip.writestr("playwright/driver/README.md", "Universal Mac package")

        os.remove(base_wheel_location)


setuptools.setup(
    name="playwright",
    author="Microsoft Corporation",
    author_email="",
    description="A high-level API to automate web browsers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Microsoft/playwright-python",
    packages=["playwright"],
    include_package_data=True,
    install_requires=["greenlet==1.0.0", "pyee>=8.0.1", "typing-extensions"],
    classifiers=[
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
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
    setup_requires=["setuptools_scm"],
    entry_points={
        "console_scripts": [
            "playwright=playwright.__main__:main",
        ],
    },
)
