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
from playwright._impl._object_factory import create_remote_object
from playwright.async_api._generated import Playwright as AsyncPlaywright


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._connection: Connection

    async def __aenter__(self) -> AsyncPlaywright:
        self._connection = Connection(
            None, create_remote_object, compute_driver_executable()
        )
        loop = asyncio.get_running_loop()
        self._connection._loop = loop
        loop.create_task(self._connection.run())
        playwright = AsyncPlaywright(
            await self._connection.wait_for_object_with_known_name("Playwright")
        )
        playwright.stop = self.__aexit__  # type: ignore
        return playwright

    async def start(self) -> AsyncPlaywright:
        return await self.__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        await self._connection.stop_async()
