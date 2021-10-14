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
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Optional, Union

from playwright._impl._helper import ParsedMessagePayload


# Sourced from: https://github.com/pytest-dev/pytest/blob/da01ee0a4bb0af780167ecd228ab3ad249511302/src/_pytest/faulthandler.py#L69-L77
def _get_stderr_fileno() -> Optional[int]:
    try:
        return sys.stderr.fileno()
    except (AttributeError, io.UnsupportedOperation):
        # pytest-xdist monkeypatches sys.stderr with an object that is not an actual file.
        # https://docs.python.org/3/library/faulthandler.html#issue-with-file-descriptors
        # This is potentially dangerous, but the best we can do.
        if not hasattr(sys, "__stderr__") or not sys.__stderr__:
            return None
        return sys.__stderr__.fileno()


class PipeTransport:
    def __init__(
        self, loop: asyncio.AbstractEventLoop, driver_executable: Path
    ) -> None:
        self._stopped = False
        self._driver_executable = driver_executable
        self.on_message: Callable[[ParsedMessagePayload], None] = lambda _: None
        self.on_error_future: asyncio.Future = loop.create_future()

    def request_stop(self) -> None:
        assert self._output
        self._stopped = True
        self._output.close()

    async def wait_until_stopped(self) -> None:
        await self._stopped_future
        await self._proc.wait()

    async def connect(self) -> None:
        self._stopped_future: asyncio.Future = asyncio.Future()
        # Hide the command-line window on Windows when using Pythonw.exe
        creationflags = 0
        if sys.platform == "win32" and sys.stdout is None:
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            # For pyinstaller
            env = os.environ.copy()
            if getattr(sys, "frozen", False):
                env["PLAYWRIGHT_BROWSERS_PATH"] = "0"

            self._proc = await asyncio.create_subprocess_exec(
                str(self._driver_executable),
                "run-driver",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=_get_stderr_fileno(),
                limit=32768,
                creationflags=creationflags,
                env=env,
            )
        except Exception as exc:
            self.on_error_future.set_exception(exc)
            raise exc

        self._output = self._proc.stdin

    async def run(self) -> None:
        assert self._proc.stdout
        assert self._proc.stdin
        while not self._stopped:
            try:
                buffer = await self._proc.stdout.readexactly(4)
                length = int.from_bytes(buffer, byteorder="little", signed=False)
                buffer = bytes(0)
                while length:
                    to_read = min(length, 32768)
                    data = await self._proc.stdout.readexactly(to_read)
                    length -= to_read
                    if len(buffer):
                        buffer = buffer + data
                    else:
                        buffer = data

                obj = self.deserialize_message(buffer)
                self.on_message(obj)
            except asyncio.IncompleteReadError:
                break
            await asyncio.sleep(0)
        self._stopped_future.set_result(None)

    def send(self, message: Dict) -> None:
        assert self._output
        data = self.serialize_message(message)
        self._output.write(
            len(data).to_bytes(4, byteorder="little", signed=False) + data
        )

    def serialize_message(self, message: Dict) -> bytes:
        msg = json.dumps(message)
        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[32mSEND>\x1b[0m", json.dumps(message, indent=2))
        return msg.encode()

    def deserialize_message(self, data: Union[str, bytes]) -> ParsedMessagePayload:
        obj = json.loads(data)

        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[33mRECV>\x1b[0m", json.dumps(obj, indent=2))
        return obj
