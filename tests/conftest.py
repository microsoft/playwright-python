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

import inspect
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, cast

import pytest
from PIL import Image
from pixelmatch import pixelmatch
from pixelmatch.contrib.PIL import from_PIL_to_raw_data

import playwright
from playwright._impl._path_utils import get_file_dirname

from .server import Server, test_server

_dirname = get_file_dirname()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "browser_name" in metafunc.fixturenames:
        browsers = metafunc.config.option.browser or ["chromium", "firefox", "webkit"]
        metafunc.parametrize("browser_name", browsers, scope="session")


@pytest.fixture(scope="session")
def assetdir() -> Path:
    return _dirname / "assets"


@pytest.fixture(scope="session")
def headless(pytestconfig: pytest.Config) -> bool:
    return not (pytestconfig.getoption("--headed") or os.getenv("HEADFUL", False))


@pytest.fixture(scope="session")
def launch_arguments(pytestconfig: pytest.Config, headless: bool) -> Dict:
    return {
        "headless": headless,
        "channel": pytestconfig.getoption("--browser-channel"),
    }


@pytest.fixture
def server() -> Generator[Server, None, None]:
    yield test_server.server


@pytest.fixture
def https_server() -> Generator[Server, None, None]:
    yield test_server.https_server


@pytest.fixture(autouse=True, scope="session")
def start_server() -> Generator[None, None, None]:
    test_server.start()
    yield
    test_server.stop()


@pytest.fixture(autouse=True)
def after_each_hook() -> Generator[None, None, None]:
    yield
    test_server.reset()


@pytest.fixture(scope="session")
def browser_name(pytestconfig: pytest.Config) -> str:
    return cast(str, pytestconfig.getoption("browser"))


@pytest.fixture(scope="session")
def browser_channel(pytestconfig: pytest.Config) -> Optional[str]:
    return cast(Optional[str], pytestconfig.getoption("--browser-channel"))


@pytest.fixture(scope="session")
def is_headless_shell(browser_name: str, browser_channel: str, headless: bool) -> bool:
    return browser_name == "chromium" and (
        browser_channel == "chromium-headless-shell"
        or (not browser_channel and headless)
    )


@pytest.fixture(scope="session")
def is_webkit(browser_name: str) -> bool:
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name: str) -> bool:
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name: str) -> bool:
    return browser_name == "chromium"


@pytest.fixture(scope="session")
def is_win() -> bool:
    return sys.platform == "win32"


@pytest.fixture(scope="session")
def is_linux() -> bool:
    return sys.platform == "linux"


@pytest.fixture(scope="session")
def is_mac() -> bool:
    return sys.platform == "darwin"


def _get_skiplist(
    request: pytest.FixtureRequest, values: List[str], value_name: str
) -> List[str]:
    skipped_values = []
    # Allowlist
    only_marker = request.node.get_closest_marker(f"only_{value_name}")
    if only_marker:
        skipped_values = values
        skipped_values.remove(only_marker.args[0])

    # Denylist
    skip_marker = request.node.get_closest_marker(f"skip_{value_name}")
    if skip_marker:
        skipped_values.append(skip_marker.args[0])

    return skipped_values


@pytest.fixture(autouse=True)
def skip_by_browser(request: pytest.FixtureRequest, browser_name: str) -> None:
    skip_browsers_names = _get_skiplist(
        request, ["chromium", "firefox", "webkit"], "browser"
    )

    if browser_name in skip_browsers_names:
        pytest.skip(f"skipped for this browser: {browser_name}")


@pytest.fixture(autouse=True)
def skip_by_platform(request: pytest.FixtureRequest) -> None:
    skip_platform_names = _get_skiplist(
        request, ["win32", "linux", "darwin"], "platform"
    )

    if sys.platform in skip_platform_names:
        pytest.skip(f"skipped on this platform: {sys.platform}")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browsers which should be used. By default on all the browsers.",
    )
    group.addoption(
        "--browser-channel",
        action="store",
        default=None,
        help="Browser channel to be used.",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run tests in headed mode.",
    )


@pytest.fixture(scope="session")
def assert_to_be_golden(browser_name: str) -> Callable[[bytes, str], None]:
    def compare(received_raw: bytes, golden_name: str) -> None:
        golden_file_path = _dirname / f"golden-{browser_name}" / golden_name
        try:
            golden_file = golden_file_path.read_bytes()
            received_image = Image.open(io.BytesIO(received_raw))
            golden_image = Image.open(io.BytesIO(golden_file))

            if golden_image.size != received_image.size:
                pytest.fail("Image size differs to golden image")
                return
            diff_pixels = pixelmatch(
                from_PIL_to_raw_data(received_image),
                from_PIL_to_raw_data(golden_image),
                golden_image.size[0],
                golden_image.size[1],
                threshold=0.2,
            )
            assert diff_pixels == 0
        except Exception:
            if os.getenv("PW_WRITE_SCREENSHOT"):
                golden_file_path.parent.mkdir(parents=True, exist_ok=True)
                golden_file_path.write_bytes(received_raw)
                print(f"Wrote {golden_file_path}")
            raise

    return compare


class RemoteServer:
    def __init__(
        self, browser_name: str, launch_server_options: Dict, tmpfile: Path
    ) -> None:
        driver_dir = Path(inspect.getfile(playwright)).parent / "driver"
        if sys.platform == "win32":
            node_executable = driver_dir / "node.exe"
        else:
            node_executable = driver_dir / "node"
        cli_js = driver_dir / "package" / "cli.js"
        tmpfile.write_text(json.dumps(launch_server_options))
        self.process = subprocess.Popen(
            [
                str(node_executable),
                str(cli_js),
                "launch-server",
                "--browser",
                browser_name,
                "--config",
                str(tmpfile),
            ],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            cwd=driver_dir,
        )
        assert self.process.stdout
        self.ws_endpoint = self.process.stdout.readline().decode().strip()
        self.process.stdout.close()

    def kill(self) -> None:
        # Send the signal to all the process groups
        if self.process.poll() is not None:
            return
        self.process.kill()
        self.process.wait()


@pytest.fixture
def launch_server(
    browser_name: str, launch_arguments: Dict, tmp_path: Path
) -> Generator[Callable[..., RemoteServer], None, None]:
    remotes: List[RemoteServer] = []

    def _launch_server(**kwargs: Dict[str, Any]) -> RemoteServer:
        remote = RemoteServer(
            browser_name,
            {
                **launch_arguments,
                **kwargs,
            },
            tmp_path / f"settings-{len(remotes)}.json",
        )
        remotes.append(remote)
        return remote

    yield _launch_server

    for remote in remotes:
        remote.kill()
