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

import asyncio
import gc
import inspect
import json
import os
import subprocess
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, cast

import greenlet
import pytest
import pytest_timeout
from _pytest.capture import CaptureManager
from _pytest.terminal import TerminalReporter

import playwright
from playwright._impl._protocol_check import take_violations

from .helpers.image_compare import assert_to_match_golden
from .server import Server, test_server

_dirname = Path(__file__).parent.absolute()

# Check each message that the client sends against the protocol spec.
os.environ.setdefault("PW_CHECK_PROTOCOL", "1")
# Run the driver as upstream runs it in its tests (for example, pages get window.builtins).
os.environ.setdefault("PWTEST_UNDER_TEST", "1")
# Keep the registry of bound browsers (browser.bind()) out of the user's cache folder.
os.environ.setdefault(
    "PWTEST_SERVER_REGISTRY", tempfile.mkdtemp(prefix="playwright-server-registry-")
)


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("CI"):
        config.option.reruns = 3


def pytest_collection_modifyitems(
    config: pytest.Config, items: List[pytest.Item]
) -> None:
    # A slow test gets three times the timeout, as test.slow() gives upstream.
    timeout = float(config.getini("timeout"))
    for item in items:
        if item.get_closest_marker("slow"):
            item.add_marker(pytest.mark.timeout(timeout * 3))


_TIMEOUT_TIMER = pytest.StashKey[threading.Timer]()


@pytest.hookimpl(tryfirst=True)
def pytest_timeout_set_timer(
    item: pytest.Item, settings: pytest_timeout.Settings
) -> Optional[bool]:
    """The timer of the thread method, with the stacks on the standard error.

    pytest-timeout writes the stacks of a test that hangs to the terminal of the
    test, and an xdist worker has no terminal: its stdout goes nowhere. The
    standard error of a worker is that of the run, so the stacks reach the log.
    The dump also has what the stacks of the threads do not show: the greenlets
    that wait for the event loop under the sync API, and the pending tasks of the
    event loop under both APIs.
    """
    if settings.method != "thread":
        return None
    if not settings.disable_debugger_detection and pytest_timeout.is_debugging():
        return True
    pytest_timeout_cancel_timer(item)
    timer = threading.Timer(settings.timeout, _dump_stacks_and_exit, (item, settings))
    timer.name = f"timeout {item.nodeid}"
    timer.daemon = True
    item.stash[_TIMEOUT_TIMER] = timer
    timer.start()
    return True


@pytest.hookimpl(tryfirst=True)
def pytest_timeout_cancel_timer(item: pytest.Item) -> Optional[bool]:
    timer = item.stash.get(_TIMEOUT_TIMER, None)
    if timer is None:
        return None
    del item.stash[_TIMEOUT_TIMER]
    timer.cancel()
    return True


def _dump_stacks_and_exit(item: pytest.Item, settings: pytest_timeout.Settings) -> None:
    """Writes the stacks of the process to its standard error and ends the
    process, as the thread method of pytest-timeout does; xdist replaces the
    worker."""
    try:
        capman = cast(
            Optional[CaptureManager],
            item.config.pluginmanager.getplugin("capturemanager"),
        )
        captured_stdout = captured_stderr = ""
        if capman:
            capman.suspend_global_capture(in_=True)
            captured_stdout, captured_stderr = capman.read_global_capture()
        # After the capture is suspended, this is the standard error of the run.
        stderr = sys.stderr

        def title(text: str, sep: str = "~") -> None:
            stderr.write(f"\n{sep * 10} {text} {sep * 10}\n")

        title(f"Timeout ({settings.timeout}s): {item.nodeid}", "+")
        if captured_stdout:
            title("Captured stdout")
            stderr.write(captured_stdout)
        if captured_stderr:
            title("Captured stderr")
            stderr.write(captured_stderr)
        current_ident = threading.current_thread().ident
        for thread_ident, frame in sys._current_frames().items():
            if thread_ident == current_ident:
                continue
            thread_name = next(
                (t.name for t in threading.enumerate() if t.ident == thread_ident),
                "<unknown>",
            )
            title(f"Stack of {thread_name} ({thread_ident})")
            stderr.write("".join(traceback.format_stack(frame)))
        for obj in gc.get_objects():
            if isinstance(obj, greenlet.greenlet) and obj.gr_frame is not None:
                title(f"Stack of {obj!r}, switched away")
                stderr.write("".join(traceback.format_stack(obj.gr_frame)))
            elif isinstance(obj, asyncio.Task) and not obj.done():
                title(f"Stack of {obj!r}")
                obj.print_stack(file=stderr)
        title("Timeout", "+")
    except Exception:
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo
) -> Generator[None, None, None]:
    # pytest-timeout cancels its timer after the report of a failure is built. The
    # report looks up the source of every frame, which takes long enough for the
    # timer of a test that failed just before its deadline (the 30-second timeout
    # of the client, for example) to fire inside pytest, which kills the xdist
    # worker. Cancel the timer before the report; the teardown gets its own below.
    if call.when == "call" and call.excinfo is not None:
        item.config.pluginmanager.hook.pytest_timeout_cancel_timer(item=item)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> Generator[None, None, None]:
    # The teardown runs with a timer of its own: the timer of a test that failed
    # is cancelled above, and by pytest-timeout once the failure is reported. The
    # timer of a test that passed is cancelled first, so that it does not fire
    # during the teardown.
    settings = pytest_timeout._get_item_settings(item)
    if settings.timeout:
        hooks = item.config.pluginmanager.hook
        hooks.pytest_timeout_cancel_timer(item=item)
        hooks.pytest_timeout_set_timer(item=item, settings=settings)
    yield


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
    args: Dict = {
        "headless": headless,
    }
    if pytestconfig.getoption("--browser-channel"):
        args["channel"] = pytestconfig.getoption("--browser-channel")
    return args


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


@pytest.fixture(autouse=True)
def check_protocol(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    yield
    violations = take_violations()
    # The test sends an invalid message on purpose, to test the driver's error.
    if request.node.get_closest_marker("skip_protocol_check"):
        return
    assert not violations, "Protocol violations:\n" + "\n".join(violations)


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
def platform() -> str:
    """Like Node.js process.platform: "linux", "darwin" or "win32"."""
    return "linux" if sys.platform.startswith("linux") else sys.platform


@pytest.fixture(scope="session")
def mac_version() -> int:
    """The major macOS version, 0 elsewhere. Port of macVersion() in platformFixtures.ts."""
    if sys.platform != "darwin":
        return 0
    darwin_major = int(os.uname().release.split(".")[0])
    # Apple jumped from macOS 15 to macOS 26, so Darwin 25 is macOS 26.
    return darwin_major + 1 if darwin_major >= 25 else darwin_major - 9


@pytest.fixture(scope="session")
def is_frozen_webkit(browser_name: str, mac_version: int) -> bool:
    """WebKit builds that no longer get updates. Port of isFrozenWebkit in browserTest.ts."""
    if browser_name != "webkit":
        return False
    if sys.platform == "darwin":
        return mac_version < 15
    try:
        os_release = Path("/etc/os-release").read_text()
    except OSError:
        return False
    return ("ID=debian" in os_release and 'VERSION_ID="11"' in os_release) or (
        "ID=ubuntu" in os_release and 'VERSION_ID="20.04"' in os_release
    )


@pytest.fixture(scope="session")
def allows_third_party(browser_name: str) -> bool:
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def default_same_site_cookie_value(browser_name: str, is_linux: bool) -> str:
    if browser_name == "chromium":
        return "Lax"
    if browser_name == "firefox":
        return "None"
    if browser_name == "webkit" and is_linux:
        return "Lax"
    if browser_name == "webkit" and not is_linux:
        return "None"
    raise Exception(f"Invalid browser_name: {browser_name}")


@pytest.fixture
def create_user_data_dir(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[], Path]:
    """Returns a function that makes a new empty user data directory."""
    return lambda: tmp_path_factory.mktemp("user-data-dir")


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
    """expect(buffer).toMatchSnapshot(name) against tests/golden-<browser>/<name>.

    With PW_WRITE_SCREENSHOT set, a screenshot that does not match is written
    over the golden file.
    """

    def compare(received_raw: bytes, golden_name: str) -> None:
        try:
            assert_to_match_golden(browser_name, received_raw, golden_name)
        except Exception:
            if os.getenv("PW_WRITE_SCREENSHOT"):
                golden_file_path = _dirname / f"golden-{browser_name}" / golden_name
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


_failed_node_ids: List[str] = []


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.failed and report.when in ("setup", "call"):
        if report.nodeid not in _failed_node_ids:
            _failed_node_ids.append(report.nodeid)


def pytest_terminal_summary(
    terminalreporter: TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    if not _failed_node_ids:
        return
    terminalreporter.write_sep("=", "Failed tests", red=True, bold=True)
    for index, nodeid in enumerate(_failed_node_ids, 1):
        terminalreporter.write_line(f"  {index}) {nodeid}", red=True)


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
