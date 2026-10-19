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

"""Remote Playwright servers for the connect tests, in both flavors.

Port of RemoteServer and RunServer in tests/config/remoteServer.ts, of the
startRemoteServer fixture in tests/config/browserTest.ts and of TestChildProcess in
tests/config/commonFixtures.ts.

RemoteServer is the "launchServer" kind: it runs remote_server_impl.js (a port of
tests/config/remote-server-impl.js), which calls browserType.launchServer() in the
driver's playwright-core. RunServer is the "run-server" kind: it runs the driver's
`run-server` command. The tests/conftest.py launch_server fixture runs the driver's
`launch-server` command, which takes launch options only; the connect tests also
need the run-server kind, the remote-server-impl.js options and a graceful close().
"""

import atexit
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from playwright._impl._driver import compute_driver_executable

KIND_LAUNCH_SERVER = "launchServer"
KIND_RUN_SERVER = "run-server"

_IMPL_SCRIPT = Path(__file__).parent / "remote_server_impl.js"
_OUTPUT_TIMEOUT = 60.0
_live_processes: List["ChildProcess"] = []


@atexit.register
def _kill_live_processes() -> None:
    # Like upstream's process.on('exit', killProcessGroup): no server outlives the tests.
    for process in list(_live_processes):
        process.send_signal(signal.SIGKILL if sys.platform != "win32" else 9)


class ChildProcess:
    """A child process in its own process group, with its output collected.

    Port of TestChildProcess in tests/config/commonFixtures.ts.
    """

    def __init__(
        self,
        command: List[str],
        env: Optional[Dict[str, Optional[str]]] = None,
        cwd: Optional[Union[str, Path]] = None,
    ) -> None:
        full_env = dict(os.environ)
        for name, value in (env or {}).items():
            if value is None:
                full_env.pop(name, None)
            else:
                full_env[name] = value
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=full_env,
            cwd=cwd,
            # Like upstream's `detached: true`: the child leads a new process group, so
            # kill() reaches the whole tree.
            start_new_session=sys.platform != "win32",
        )
        self._output = ""
        self._condition = threading.Condition()
        self._reader_done = False
        self._reader = threading.Thread(target=self._read_output, daemon=True)
        self._reader.start()
        _live_processes.append(self)

    @property
    def pid(self) -> int:
        return self.process.pid

    @property
    def output(self) -> str:
        with self._condition:
            return self._output

    def _read_output(self) -> None:
        assert self.process.stdout
        while True:
            chunk = os.read(self.process.stdout.fileno(), 65536)
            with self._condition:
                if not chunk:
                    self._reader_done = True
                    self._condition.notify_all()
                    return
                self._output += chunk.decode(errors="replace")
                self._condition.notify_all()

    def wait_for_output(
        self, substring: str, count: int = 1, timeout: float = _OUTPUT_TIMEOUT
    ) -> None:
        """Waits until the output has the substring count times."""
        self._wait(lambda output: output.count(substring) >= count, timeout)

    def _wait(self, predicate: Any, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            while not predicate(self._output):
                remaining = deadline - time.monotonic()
                if self._reader_done or remaining <= 0:
                    raise Exception(
                        f"Child process did not print what the test waits for. Output:\n{self._output}"
                    )
                self._condition.wait(remaining)

    def send_signal(self, sig: int) -> None:
        """Sends the signal to the process group. Port of _killProcessTree()."""
        if self.process.poll() is not None:
            return
        if sys.platform == "win32":
            # Like upstream, Windows always uses taskkill, whatever the signal.
            subprocess.run(
                ["taskkill", "/pid", str(self.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        try:
            os.killpg(self.pid, sig)
        except ProcessLookupError:
            pass

    def kill(self, sig: int = signal.SIGKILL if sys.platform != "win32" else 9) -> int:
        """Sends the signal to the process group and waits for the exit."""
        self.send_signal(sig)
        return self.exit_code()

    def exit_code(self, timeout: Optional[float] = None) -> int:
        code = self.process.wait(timeout)
        if self in _live_processes:
            _live_processes.remove(self)
        self._reader.join()
        if self.process.stdin:
            self.process.stdin.close()
        if self.process.stdout:
            self.process.stdout.close()
        return code


class RunServer:
    """The `playwright run-server` command. Port of RunServer in remoteServer.ts."""

    def __init__(
        self,
        mode: Optional[str] = None,
        env: Optional[Dict[str, Optional[str]]] = None,
        artifacts_dir: Optional[Union[str, Path]] = None,
        unsafe: bool = False,
    ) -> None:
        node, cli = compute_driver_executable()
        command = [node, cli, "run-server"]
        if mode == "extension":
            command.append("--mode=extension")
        if artifacts_dir:
            command.append(f"--artifacts-dir={artifacts_dir}")
        if unsafe:
            command.append("--unsafe")
        self._process = ChildProcess(command, env=env)
        prefix = "Listening on "
        self._process.wait_for_output(prefix)
        line = self._process.output.split(prefix, 1)[1]
        self.ws_endpoint = line.splitlines()[0].strip()

    def close(self) -> None:
        self._process.kill(signal.SIGINT)


class RemoteServer:
    """A browserType.launchServer() server. Port of RemoteServer in remoteServer.ts."""

    def __init__(
        self,
        browser_name: str,
        launch_arguments: Dict[str, Any],
        stall_on_close: bool = False,
        disconnect_on_sighup: bool = False,
        exit_on_file: Optional[Union[str, Path]] = None,
        exit_on_warning: bool = False,
        in_cluster: bool = False,
        start_stop_and_run_http: bool = False,
        shared_browser: bool = False,
        artifacts_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        node, cli = compute_driver_executable()
        launch_options: Dict[str, Any] = {
            **launch_arguments,
            "handleSIGINT": True,
            "handleSIGTERM": True,
            "handleSIGHUP": True,
        }
        if shared_browser:
            launch_options["_sharedBrowser"] = True
        if artifacts_dir:
            launch_options["artifactsDir"] = str(artifacts_dir)
        options = {
            "playwrightPath": str(Path(cli).parent),
            "browserTypeName": browser_name,
            "launchOptions": launch_options,
            "stallOnClose": stall_on_close,
            "disconnectOnSIGHUP": disconnect_on_sighup,
            "exitOnFile": str(exit_on_file) if exit_on_file else None,
            "exitOnWarning": exit_on_warning,
            "inCluster": in_cluster,
            "startStopAndRunHttp": start_stop_and_run_http,
        }
        self._process = ChildProcess(
            [node, str(_IMPL_SCRIPT), json.dumps(options)],
            env={"NODE_OPTIONS": os.environ.get("NODE_OPTIONS")},
        )
        self.ws_endpoint = self.out("wsEndpoint")

    def _outputs(self, output: str) -> Dict[str, str]:
        return {
            match.group(1): match.group(2)
            for match in re.finditer(r"\(([^()]+)=>([^()]+)\)", output)
        }

    def out(self, key: str, timeout: float = _OUTPUT_TIMEOUT) -> str:
        """Waits until the server prints "(key=>value)" and returns the value."""
        self._process._wait(lambda output: key in self._outputs(output), timeout)
        return self._outputs(self._process.output)[key]

    @property
    def child_pid(self) -> int:
        return self._process.pid

    def child_exit_code(self) -> int:
        return self._process.exit_code()

    def close(self) -> None:
        self._process.send_signal(signal.SIGINT)
        try:
            self._process.exit_code(timeout=30)
        except subprocess.TimeoutExpired:
            self._process.kill()


PlaywrightServer = Union[RemoteServer, RunServer]


class RemoteServerStarter:
    """Starts one remote server for a test. Port of the startRemoteServer fixture."""

    def __init__(self, browser_name: str, launch_arguments: Dict[str, Any]) -> None:
        self._browser_name = browser_name
        self._launch_arguments = launch_arguments
        self._server: Optional[PlaywrightServer] = None

    def __call__(
        self,
        kind: str,
        artifacts_dir: Optional[Union[str, Path]] = None,
        unsafe: bool = False,
        env: Optional[Dict[str, Optional[str]]] = None,
        launch_options: Optional[Dict[str, Any]] = None,
        **options: Any,
    ) -> Any:
        """Starts the server of the kind.

        launch_options override the run's launch arguments of the launchServer kind,
        as a test that changes upstream's _defaultLaunchOptions does. The run-server
        kind gets the launch options from the client that connects.
        """
        if self._server:
            raise Exception("can only start one remote server")
        if kind == KIND_LAUNCH_SERVER:
            self._server = RemoteServer(
                self._browser_name,
                {**self._launch_arguments, **(launch_options or {})},
                artifacts_dir=artifacts_dir,
                **options,
            )
        else:
            self._server = RunServer(
                artifacts_dir=artifacts_dir, unsafe=unsafe, env=env
            )
        return self._server

    def close(self) -> None:
        if self._server:
            self._server.close()
            # Give any connected browsers a chance to disconnect to avoid
            # poisoning next test with quasy-alive browsers.
            time.sleep(1)


@contextmanager
def redirect_port_forwarding_for_test(
    browser_type: Any, port: Optional[int]
) -> Iterator[None]:
    """Port of the __testHookRedirectPortForwarding option of browserType.connect().

    While active, browser_type.connect() asks the driver to send the requests that the
    remote browser makes through the client's SOCKS proxy to this port. Works with the
    BrowserType of either flavor.
    """
    if not port:
        yield
        return
    channel = browser_type._impl_obj._connection.local_utils._channel
    original = channel.connect

    async def connect(**kwargs: Any) -> Any:
        return await original(**{**kwargs, "socksProxyRedirectPortForTest": port})

    setattr(channel, "connect", connect)
    try:
        yield
    finally:
        delattr(channel, "connect")
