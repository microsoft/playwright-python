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

from typing import Any, Optional

from playwright._impl.out_of_process import PlaywrightClient, start
from playwright.async_api._generated import Playwright as AsyncPlaywright


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._client: Optional[PlaywrightClient] = None
        self._exit_was_called = False

    async def __aenter__(self) -> AsyncPlaywright:
        impl, self._client = await start()
        playwright = AsyncPlaywright(impl)
        playwright.stop = self.__aexit__  # type: ignore
        return playwright

    async def start(self) -> AsyncPlaywright:
        return await self.__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        if self._exit_was_called:
            return
        self._exit_was_called = True
        if self._client:
            await self._client.stop()
