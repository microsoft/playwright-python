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
from typing import Any

from playwright._impl._connection import Connection
from playwright._impl._driver import compute_driver_executable
from playwright._impl._transport import PipeTransport
from playwright.async_api._generated import Playwright as AsyncPlaywright


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._connection: Connection
        self._transport: PipeTransport

    async def __aenter__(self) -> AsyncPlaywright:
        loop = asyncio.get_running_loop()
        self._connection = connection = Connection(None, loop)
        self._transport = transport = PipeTransport(loop, compute_driver_executable())
        connection.on_message = transport.send
        transport.on_message = connection.dispatch

        await transport.connect()
        loop.create_task(transport.run())
        await connection.run()
        playwright_future = connection.playwright_future
        playwright = AsyncPlaywright(await playwright_future)
        playwright.stop = self.__aexit__  # type: ignore
        return playwright

    async def start(self) -> AsyncPlaywright:
        return await self.__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        self._transport.request_stop()
        await self._transport.wait_until_stopped()
