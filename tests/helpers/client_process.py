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

"""A Python client in a child process, for the signals tests, in both flavors.

Port of the startRemoteServer('launchServer') fixture of tests/library/signals.spec.ts
for the Python client. Upstream's RemoteServer (tests/config/remoteServer.ts) runs a
Node.js process that launches the browser and sends it signals. ClientProcess runs
client_process_impl.py instead: a Python script that launches the browser with the
sync or async API. The Python process starts the driver, and the driver launches the
browser.

out(key) returns what the child reported, like RemoteServer.out(). The script prints
tempDir, ready and closed. The rest comes from the driver's pw:browser
log (the child runs with DEBUG=pw:browser): pid of the browser process, and exitCode
and signal of its exit, which upstream gets from the 'close' event of BrowserServer.
"""

import json
import os
import re
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from tests.helpers.remote_server import ChildProcess

_IMPL_SCRIPT = Path(__file__).parent / "client_process_impl.py"
_OUTPUT_TIMEOUT = 60.0

# What the driver logs with DEBUG=pw:browser, see packages/utils/processLauncher.ts.
_DRIVER_LOG = {
    "pid": (r"<launched> pid=", r"<launched> pid=(\d+)"),
    "exitCode": (
        "<process did exit: ",
        r"<process did exit: exitCode=([^,]+), signal=[^>]+>",
    ),
    "signal": (
        "<process did exit: ",
        r"<process did exit: exitCode=[^,]+, signal=([^>]+)>",
    ),
}


class ClientProcess:
    def __init__(
        self,
        flavor: str,
        browser_name: str,
        launch_arguments: Dict[str, Any],
        work_dir: Path,
        url: Optional[str] = None,
        exit_on_file: Optional[Union[str, Path]] = None,
        start_stop_and_run_http: bool = False,
    ) -> None:
        # A short path, not one under tmp_path: the user data dir of the browser
        # goes there, and the socket of Chrome's ProcessSingleton inside it has at
        # most 104 characters.
        self._temp_dir = temp_dir = Path(tempfile.mkdtemp(prefix="pw-"))
        options = {
            "flavor": flavor,
            "browserTypeName": browser_name,
            "launchOptions": {
                **launch_arguments,
                "handle_sigint": True,
                "handle_sigterm": True,
                "handle_sighup": True,
            },
            "url": url,
            "exitOnFile": str(exit_on_file) if exit_on_file else None,
            "startStopAndRunHttp": start_stop_and_run_http,
        }
        # -I: the script's directory (tests/helpers) must not shadow any module.
        self._process = ChildProcess(
            [sys.executable, "-I", str(_IMPL_SCRIPT), json.dumps(options)],
            env={"DEBUG": "pw:browser", "TMPDIR": str(temp_dir)},
        )
        if not start_stop_and_run_http:
            # Upstream waits until the page of `url` is open in the browser.
            self.out("ready")

    @property
    def child_pid(self) -> int:
        return self._process.pid

    def out(self, key: str, timeout: float = _OUTPUT_TIMEOUT) -> str:
        """Waits until the child reports the key and returns the value."""
        marker, pattern = _DRIVER_LOG.get(
            key, (f"({key}=>", r"\(" + re.escape(key) + r"=>([^()]+)\)")
        )
        deadline = time.monotonic() + timeout
        self._process.wait_for_output(marker, timeout=timeout)
        while True:
            # The line that has the marker may have arrived in parts.
            match = re.search(pattern, self._process.output)
            if match:
                return match.group(1)
            if time.monotonic() > deadline:
                raise Exception(
                    f"Child process did not report {key}. Output:\n{self._process.output}"
                )
            time.sleep(0.05)

    def kill(self, sig: int) -> None:
        """Sends the signal to the Python process only, like process.kill(pid, sig)."""
        os.kill(self.child_pid, sig)

    def child_exit_code(self) -> int:
        """Waits until the Python process exits and the driver closes its output.

        Like Popen.returncode: -N when the signal N ended the process (128 + N in a
        shell, which upstream's Node.js reports as an exit code).
        """
        return self._process.exit_code()

    def close(self) -> None:
        """Kills what is left: the Python process and the driver."""
        try:
            if sys.platform == "win32":
                self._process.kill()
                return
            try:
                os.killpg(self.child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._process.exit_code()
        finally:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
