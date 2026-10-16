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
from typing import TYPE_CHECKING, Dict, Optional, cast

from pyee.asyncio import AsyncIOEventEmitter

from playwright._impl._errors import Error, TargetClosedError
from playwright._impl._helper import ParsedMessagePayload
from playwright._impl._transport import Transport

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._protocol_channels import JsonPipeChannel


class JsonPipeTransport(AsyncIOEventEmitter, Transport):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        pipe_channel: "JsonPipeChannel",
    ) -> None:
        super().__init__(loop)
        Transport.__init__(self, loop)
        self._stop_requested = False
        self._pipe_channel = pipe_channel

    def request_stop(self) -> None:
        self._stop_requested = True
        self._pipe_channel.send_no_reply("close")

    def dispose(self) -> None:
        self.on_error_future.cancel()
        self._stopped_future.cancel()

    async def wait_until_stopped(self) -> None:
        await self._stopped_future

    async def connect(self) -> None:
        self._stopped_future: asyncio.Future = asyncio.Future()

        def handle_message(message: Dict) -> None:
            if self._stop_requested:
                return
            self.on_message(cast(ParsedMessagePayload, message))

        def handle_closed(reason: Optional[str]) -> None:
            self.emit("close", reason)
            if reason:
                self.on_error_future.set_exception(TargetClosedError(reason))
            self._stopped_future.set_result(None)

        self._pipe_channel.onMessage(lambda event: handle_message(event["message"]))
        self._pipe_channel.onClosed(lambda event: handle_closed(event["reason"]))

    async def run(self) -> None:
        await self._stopped_future

    def send(self, message: Dict) -> None:
        if self._stop_requested:
            raise Error("Playwright connection closed")
        # The transport sends synchronously, so this does not wait for the reply.
        self._pipe_channel.send_no_reply("send", {"message": message})
