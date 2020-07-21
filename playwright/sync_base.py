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
from typing import Any, Callable, Union

from playwright.wait_helper import WaitHelper

loop = asyncio.get_event_loop()


class Event:
    def __init__(
        self,
        sync_base: "SyncBase",
        event: str,
        predicate: Callable[[Any], bool] = None,
        timeout: int = None,
    ) -> None:
        self._value: Any = None

        wait_helper = WaitHelper()
        wait_helper.reject_on_timeout(
            timeout or 30000, f'Timeout while waiting for event "${event}"'
        )
        self._future = asyncio.ensure_future(
            wait_helper.wait_for_event(sync_base._async_obj, event, predicate)
        )

    @property
    def value(self) -> Any:
        if not self._value:
            self._value = loop.run_until_complete(self._future)
        return self._value


class EventContextManager:
    def __init__(
        self,
        sync_base: "SyncBase",
        event: str,
        predicate: Callable[[Any], bool] = None,
        timeout: int = None,
    ) -> None:
        self._event = Event(sync_base, event, predicate, timeout)

    def __enter__(self) -> Event:
        return self._event

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._event.value


class SyncBase:
    def __init__(self, async_obj: Any) -> None:
        self._async_obj = async_obj

    def _sync(self, future: asyncio.Future) -> Any:
        return loop.run_until_complete(future)

    def on(self, event_name: str, handler: Any) -> None:
        self._async_obj.on(event_name, handler)

    def remove_listener(self, event_name: str, handler: Any) -> None:
        self._async_obj.remove_listener(event_name, handler)

    def expect_event(
        self,
        event: str,
        predicate: Union[Callable[[Any], bool]] = None,
        timeout: int = None,
    ) -> EventContextManager:
        return EventContextManager(self, event, predicate, timeout)
