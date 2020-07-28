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
import json
import os
from typing import Dict


class Transport:
    def __init__(
        self,
        input: asyncio.StreamReader,
        output: asyncio.StreamWriter,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__()
        self._input: asyncio.StreamReader = input
        self._output: asyncio.StreamWriter = output
        self.loop: asyncio.AbstractEventLoop = loop
        self.on_message = lambda _: None
        self._stopped = False

    def run_sync(self) -> None:
        self.loop.run_until_complete(self._run())

    def run_async(self) -> None:
        self.loop.create_task(self._run())

    def stop(self) -> None:
        self._stopped = True
        self._output.close()

    async def _run(self) -> None:
        while not self._stopped:
            try:
                buffer = await self._input.readexactly(4)
                length = int.from_bytes(buffer, byteorder="little", signed=False)
                buffer = bytes(0)
                while length:
                    to_read = min(length, 32768)
                    data = await self._input.readexactly(to_read)
                    length -= to_read
                    if len(buffer):
                        buffer = b"".join([buffer, data])
                    else:
                        buffer = data
                msg = buffer.decode("utf-8")
                obj = json.loads(msg)

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
        data = bytes(msg, "utf-8")
        self._output.write(len(data).to_bytes(4, byteorder="little", signed=False))
        self._output.write(data)
