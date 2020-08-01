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

import os
import re
import shutil
import subprocess

from playwright.path_utils import get_file_dirname

_dirname = get_file_dirname()

driver_path = _dirname / "driver"
package_path = _dirname / "playwright"
drivers_path = package_path / "drivers"

if (driver_path / "package-lock.json").exists():
    os.remove(driver_path / "package-lock.json")
if (driver_path / "node_modules").exists():
    shutil.rmtree(driver_path / "node_modules")
if (driver_path / "out").exists():
    shutil.rmtree(driver_path / "out")

subprocess.check_call("npm i", cwd=driver_path, shell=True)
subprocess.check_call("npm run bake", cwd=driver_path, shell=True)

# for local development
drivers = (driver_path / "out").glob("**/*")
for driver in drivers:
    shutil.copy(driver, drivers_path)

node_modules_playwright = driver_path / "node_modules" / "playwright"

shutil.copyfile(
    node_modules_playwright / "browsers.json", drivers_path / "browsers.json",
)

upstream_readme = (node_modules_playwright / "README.md").read_text()
pw_python_readme = (_dirname / "README.md").read_text()

matches = re.findall(r"<!-- GEN:(.*?) -->(.*?)<!-- GEN:stop -->", upstream_readme)

for key, value in matches:
    pw_python_readme = re.sub(
        rf"(<!-- GEN:{key} -->).*?(<!-- GEN:stop -->)",
        f"<!-- GEN:{key} -->{value}<!-- GEN:stop -->",
        pw_python_readme,
    )

(_dirname / "README.md").write_text(pw_python_readme)
