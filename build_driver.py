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

import gzip
import os
import re
import shutil
import subprocess
from pathlib import Path

_dirname = Path(os.path.dirname(os.path.abspath(__file__)))

driver_path = _dirname / "driver"
package_path = _dirname / "playwright"
drivers_path = package_path / "drivers"

if (driver_path / "package-lock.json").exists():
    os.remove(driver_path / "package-lock.json")
if (driver_path / "node_modules").exists():
    shutil.rmtree(driver_path / "node_modules")
if (driver_path / "out").exists():
    shutil.rmtree(driver_path / "out")

subprocess.run("npm i", cwd=driver_path, shell=True)
subprocess.run("npm run bake", cwd=driver_path, shell=True)

for driver in ["driver-linux", "driver-macos", "driver-win.exe"]:
    if (package_path / driver).exists():
        os.remove((package_path / driver))

    in_path = driver_path / "out" / driver
    out_path = drivers_path / (driver + ".gz")
    with open(in_path, "rb") as f_in, gzip.open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

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
