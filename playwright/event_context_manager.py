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
from typing import Any, Callable, Generic, Optional, TypeVar, cast

from playwright.connection import ChannelOwner
from playwright.wait_helper import WaitHelper

T = TypeVar("T")


class AsyncEventInfo(Generic[T]):
    def __init__(
        self,
        channel_owner: ChannelOwner,
        event: str,
        predicate: Callable[[T], bool] = None,
        timeout: int = None,
    ) -> None:
        self._value: Optional[T] = None
        wait_helper = WaitHelper()
        wait_helper.reject_on_timeout(
            timeout or 30000, f'Timeout while waiting for event "${event}"'
        )
        self._future = asyncio.get_event_loop().create_task(
            wait_helper.wait_for_event(channel_owner, event, predicate)
        )

    @property
    async def value(self) -> T:
        if not self._value:
            self._value = await self._future
        return cast(T, self._value)


class AsyncEventContextManager(Generic[T]):
    def __init__(
        self,
        channel_owner: ChannelOwner,
        event: str,
        predicate: Callable[[T], bool] = None,
        timeout: int = None,
    ) -> None:
        self._event = AsyncEventInfo(channel_owner, event, predicate, timeout)

    async def __aenter__(self) -> AsyncEventInfo[T]:
        return self._event

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._event.value
