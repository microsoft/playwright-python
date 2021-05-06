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
from playwright._impl._transport import PipeTransport
from playwright.sync_api._generated import Playwright as SyncPlaywright


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._playwright: SyncPlaywright
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()

    def __enter__(self) -> SyncPlaywright:
        async def inner() -> Any:
            self._connection = Connection(
                create_remote_object, PipeTransport(compute_driver_executable())
            )
            loop = asyncio.get_running_loop()
            self._connection._loop = loop
            obj = asyncio.create_task(
                self._connection.wait_for_object_with_known_name("Playwright")
            )
            await self._connection._transport.start()
            loop.create_task(self._connection.run())
            done, _ = await asyncio.wait(
                {
                    obj,
                    self._connection._transport.on_error_future,  # type: ignore
                },
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not obj.done():
                obj.cancel()
            obj = next(iter(done)).result()
            return obj

        task = self._loop.run_until_complete(inner())
        return SyncPlaywright(task)

    def start(self) -> SyncPlaywright:
        return self.__enter__()

    def __exit__(self, *args: Any) -> None:
        self._loop.run_until_complete(self._connection.stop_async())
