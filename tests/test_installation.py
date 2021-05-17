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
from venv import EnvBuilder


def test_install(tmp_path: Path):
    env = EnvBuilder(with_pip=True)
    env.create(env_dir=tmp_path)
    context = env.ensure_directories(tmp_path)
    root = Path(__file__).parent.parent.resolve()
    if sys.platform == "win32":
        wheelpath = list((root / "dist").glob("playwright*win_amd64*.whl"))[0]
    elif sys.platform == "linux":
        wheelpath = list((root / "dist").glob("playwright*manylinux1*.whl"))[0]
    elif sys.platform == "darwin":
        wheelpath = list((root / "dist").glob("playwright*macosx_10_*.whl"))[0]
    subprocess.check_output(
        [
            context.env_exe,
            "-m",
            "pip",
            "install",
            str(wheelpath),
        ]
    )
    environ = os.environ.copy()
    environ["PLAYWRIGHT_BROWSERS_PATH"] = str(tmp_path)
    subprocess.check_output(
        [context.env_exe, "-m", "playwright", "install"], env=environ
    )
    shutil.copyfile(root / "tests" / "assets" / "client.py", tmp_path / "main.py")
    subprocess.check_output([context.env_exe, str(tmp_path / "main.py")], env=environ)
    assert (tmp_path / "chromium.png").exists()
    assert (tmp_path / "firefox.png").exists()
    assert (tmp_path / "webkit.png").exists()
