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
import io
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional


# Sourced from: https://github.com/pytest-dev/pytest/blob/da01ee0a4bb0af780167ecd228ab3ad249511302/src/_pytest/faulthandler.py#L69-L77
def _get_stderr_fileno() -> Optional[int]:
    try:
        return sys.stderr.fileno()
    except (AttributeError, io.UnsupportedOperation):
        # pytest-xdist monkeypatches sys.stderr with an object that is not an actual file.
        # https://docs.python.org/3/library/faulthandler.html#issue-with-file-descriptors
        # This is potentially dangerous, but the best we can do.
        if not hasattr(sys, "__stderr__"):
            return None
        return sys.__stderr__.fileno()


class Transport:
    def __init__(self, driver_executable: Path) -> None:
        super().__init__()
        self.on_message = lambda _: None
        self._stopped = False
        self._driver_executable = driver_executable
        self._loop: asyncio.AbstractEventLoop

    def stop(self) -> None:
        self._stopped = True
        self._output.close()

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        driver_executable = self._driver_executable

        proc = await asyncio.create_subprocess_exec(
            str(driver_executable),
            "run-driver",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=_get_stderr_fileno(),
            limit=32768,
        )
        assert proc.stdout
        assert proc.stdin
        self._output = proc.stdin

        while not self._stopped:
            try:
                buffer = await proc.stdout.readexactly(4)
                length = int.from_bytes(buffer, byteorder="little", signed=False)
                buffer = bytes(0)
                while length:
                    to_read = min(length, 32768)
                    data = await proc.stdout.readexactly(to_read)
                    length -= to_read
                    if len(buffer):
                        buffer = buffer + data
                    else:
                        buffer = data
                obj = json.loads(buffer)

                if "DEBUGP" in os.environ:  # pragma: no cover
                    print("\x1b[33mRECV>\x1b[0m", json.dumps(obj, indent=2))
                self.on_message(obj)
            except asyncio.IncompleteReadError:
                break
            await asyncio.sleep(0)

    def send(self, message: Dict) -> None:
        msg = json.dumps(message)
        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[32mSEND>\x1b[0m", json.dumps(message, indent=2))
        data = msg.encode()
        self._output.write(
            len(data).to_bytes(4, byteorder="little", signed=False) + data
        )
