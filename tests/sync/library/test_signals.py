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

"""Port of tests/library/signals.spec.ts.

Upstream runs a Node.js client in a child process and sends signals to it. Here the
child process runs a Python script that uses the sync API of the Python client
(tests/helpers/client_process_impl.py); the async tests run one that uses the async API.
As upstream's process.kill(pid, signal), the tests send the signals to the Python
process only. The driver closes the browser when the Python process goes away.
"""

import os
import platform as platform_module
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List

import pytest

from tests.helpers.client_process import ClientProcess
from tests.server import Server

FLAVOR = "sync"

skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32", reason="signals do not work on Windows"
)


@pytest.fixture
def start_client_process(
    browser_name: str, launch_arguments: Dict, tmp_path: Path
) -> Generator[Callable[..., ClientProcess], None, None]:
    """Port of the startRemoteServer('launchServer') fixture, for the Python client."""
    processes: List[ClientProcess] = []

    def start(**options: Any) -> ClientProcess:
        process = ClientProcess(
            FLAVOR,
            browser_name,
            launch_arguments,
            tmp_path / f"client-{len(processes)}",
            **options,
        )
        processes.append(process)
        return process

    yield start
    for process in processes:
        process.close()


def test_SI_001_should_close_the_browser_when_the_node_process_closes(
    start_client_process: Callable[..., ClientProcess], server: Server, is_win: bool
) -> None:
    client = start_client_process(url=server.EMPTY_PAGE)
    if is_win:
        subprocess.run(
            ["taskkill", "/pid", str(client.child_pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    else:
        client.kill(signal.SIGTERM)
    # Node.js handles SIGTERM and exits with 0. Python does not handle SIGTERM, so the
    # signal ends the process.
    assert client.child_exit_code() == (1 if is_win else -signal.SIGTERM)
    if not is_win:
        # Upstream does not check the browser: the Node.js process may exit before it
        # reports. The driver outlives the Python process and closes the browser.
        assert client.out("exitCode") == "0"


def test_SI_002_should_remove_temp_dir_on_process_exit(
    start_client_process: Callable[..., ClientProcess],
    server: Server,
    platform: str,
    tmp_path: Path,
) -> None:
    if platform == "win32":
        pytest.skip("Removing user data dir synchronously is blocked on Windows")

    file = tmp_path / "exit.file"
    client = start_client_process(url=server.EMPTY_PAGE, exit_on_file=file)
    temp_dir = client.out("tempDir")
    before = os.path.exists(temp_dir)
    file.write_text("data", encoding="utf-8")
    assert client.child_exit_code() == 42
    after = os.path.exists(temp_dir)
    assert before is True
    assert after is False


@skip_on_windows
def test_SI_003_signals_should_report_browser_close_signal_2(
    start_client_process: Callable[..., ClientProcess],
    server: Server,
    is_mac: bool,
    mac_version: int,
    browser_name: str,
) -> None:
    client = start_client_process(url=server.EMPTY_PAGE)
    pid = int(client.out("pid"))
    os.killpg(pid, signal.SIGKILL)
    if (
        is_mac
        and browser_name == "webkit"
        and mac_version > 13
        and platform_module.machine() == "arm64"
    ):
        # WebKit on newer macOS exits sometimes with exit code, sometimes with signal.
        assert re.search(
            r"exitCode:137|signal:SIGKILL",
            "exitCode:" + client.out("exitCode") + "signal:" + client.out("signal"),
        )
    else:
        assert client.out("exitCode") == "null"
        assert client.out("signal") == "SIGKILL"
    client.kill(signal.SIGTERM)
    client.child_exit_code()


@skip_on_windows
def test_SI_004_signals_should_close_the_browser_on_sigint(
    start_client_process: Callable[..., ClientProcess], server: Server
) -> None:
    client = start_client_process(url=server.EMPTY_PAGE)
    client.kill(signal.SIGINT)
    assert client.out("exitCode") == "0"
    assert client.out("signal") == "null"
    # 130 in a shell: Python exits on KeyboardInterrupt by the SIGINT signal.
    assert client.child_exit_code() == -signal.SIGINT


@skip_on_windows
def test_SI_005_signals_should_close_the_browser_on_sigterm(
    start_client_process: Callable[..., ClientProcess], server: Server
) -> None:
    client = start_client_process(url=server.EMPTY_PAGE)
    client.kill(signal.SIGTERM)
    assert client.out("exitCode") == "0"
    assert client.out("signal") == "null"
    # Node.js handles SIGTERM and exits with 0. Python does not handle SIGTERM, so the
    # signal ends the process.
    assert client.child_exit_code() == -signal.SIGTERM


@skip_on_windows
def test_SI_006_signals_should_close_the_browser_on_sighup(
    start_client_process: Callable[..., ClientProcess], server: Server
) -> None:
    client = start_client_process(url=server.EMPTY_PAGE)
    client.kill(signal.SIGHUP)
    assert client.out("exitCode") == "0"
    assert client.out("signal") == "null"
    # Node.js handles SIGHUP and exits with 0. Python does not handle SIGHUP, so the
    # signal ends the process.
    assert client.child_exit_code() == -signal.SIGHUP


@skip_on_windows
def test_SI_010_signals_should_not_prevent_default_sigterm_handling_after_browser_close(
    start_client_process: Callable[..., ClientProcess],
) -> None:
    client = start_client_process(start_stop_and_run_http=True)
    assert client.out("closed") == "success"
    client.kill(signal.SIGTERM)
    # Upstream: exit code null and signal SIGTERM.
    assert client.child_exit_code() == -signal.SIGTERM
