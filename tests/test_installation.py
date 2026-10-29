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
import shutil
import subprocess
import sys
from pathlib import Path
from venv import EnvBuilder

import pytest

ROOT = Path(__file__).parent.parent.resolve()


def _create_venv(env_dir: Path) -> str:
    env = EnvBuilder(with_pip=True)
    env.create(env_dir=env_dir)
    return env.ensure_directories(env_dir).env_exe


def _run_client(python: str, tmp_path: Path, browser_name: str, environ: dict) -> None:
    # cwd=tmp_path: from the repository root, "-m playwright" imports the checkout
    # instead of the installed package.
    subprocess.check_output(
        [python, "-m", "playwright", "install", browser_name],
        cwd=tmp_path,
        env=environ,
    )
    shutil.copyfile(ROOT / "tests" / "assets" / "client.py", tmp_path / "main.py")
    subprocess.check_output(
        [python, str(tmp_path / "main.py"), browser_name], cwd=tmp_path, env=environ
    )
    assert (tmp_path / f"{browser_name}.png").exists()


# A venv, a pip install of the wheel and a browser download: minutes, not the 30 s
# of a test.
@pytest.mark.timeout(900)
def test_install(tmp_path: Path, browser_name: str) -> None:
    python = _create_venv(tmp_path / "env")
    if sys.platform == "win32":
        wheelpath = list((ROOT / "dist").glob("playwright*win_amd64*.whl"))[0]
    elif sys.platform == "linux":
        wheelpath = list((ROOT / "dist").glob("playwright*manylinux1*.whl"))[0]
    elif sys.platform == "darwin":
        wheelpath = list((ROOT / "dist").glob("playwright*macosx_*.whl"))[0]
    subprocess.check_output([python, "-m", "pip", "install", str(wheelpath)])
    environ = os.environ.copy()
    environ["PLAYWRIGHT_BROWSERS_PATH"] = str(tmp_path)
    _run_client(python, tmp_path, browser_name, environ)


# The sdist (python -m build --sdist) has the driver without Node.js: it runs with
# the Node.js of PLAYWRIGHT_NODEJS_PATH, and says so when the variable is missing.
@pytest.mark.timeout(900)
def test_install_sdist(tmp_path: Path, browser_name: str) -> None:
    node = shutil.which("node")
    assert node, "node must be in PATH"
    python = _create_venv(tmp_path / "env")
    sdist = list((ROOT / "dist").glob("playwright-*.tar.gz"))[0]
    # No wheels at all, as poetry's installer.no-binary=:all: in the report: the
    # dependencies come from source too. The isolated build environment still
    # takes wheels: pip does not pass the policy on to it, and neither does poetry.
    subprocess.check_output(
        [python, "-m", "pip", "install", "--no-binary", ":all:", str(sdist)]
    )
    driver_dir = Path(
        subprocess.check_output(
            [
                python,
                "-c",
                "import playwright, pathlib; print(pathlib.Path(playwright.__file__).parent / 'driver')",
            ],
            cwd=tmp_path,
            text=True,
        ).strip()
    )
    assert (driver_dir / "package" / "cli.js").exists()
    assert not (driver_dir / "node").exists()
    assert not (driver_dir / "node.exe").exists()

    environ = os.environ.copy()
    environ["PLAYWRIGHT_BROWSERS_PATH"] = str(tmp_path)
    environ.pop("PLAYWRIGHT_NODEJS_PATH", None)
    result = subprocess.run(
        [python, "-m", "playwright", "--version"],
        cwd=tmp_path,
        env=environ,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Set PLAYWRIGHT_NODEJS_PATH" in result.stderr

    environ["PLAYWRIGHT_NODEJS_PATH"] = str(tmp_path / "no-such-node")
    result = subprocess.run(
        [python, "-m", "playwright", "--version"],
        cwd=tmp_path,
        env=environ,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Cannot launch Node.js executable at" in result.stderr
    assert "no-such-node" in result.stderr

    environ["PLAYWRIGHT_NODEJS_PATH"] = node
    _run_client(python, tmp_path, browser_name, environ)
