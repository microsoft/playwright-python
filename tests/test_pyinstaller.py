# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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
import shutil
import subprocess
import sys
from pathlib import Path


def test_pyinstaller(tmp_path: Path) -> None:
    root = Path(__file__).parent.parent.resolve()
    environ = os.environ.copy()
    environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    subprocess.check_output(
        [sys.executable, "-m", "playwright", "install"], env=environ
    )
    shutil.copyfile(root / "tests" / "assets" / "client.py", tmp_path / "main.py")
    subprocess.check_output(
        [sys.executable, "-m", "PyInstaller", "-F", "main.py"],
        cwd=tmp_path,
    )
    subprocess.check_output([str(tmp_path / "dist" / "main"), str(tmp_path)])
    assert (tmp_path / "chromium.png").exists()
    assert (tmp_path / "firefox.png").exists()
    assert (tmp_path / "webkit.png").exists()
