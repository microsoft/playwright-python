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

"""Port of packages/utils/zones.ts.

Python: AsyncLocalStorage is a ContextVar. An asyncio task copies the context when
it is created, as a promise keeps the store of the code that created it.
"""

from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, Literal, Optional, TypeVar

ZoneType = Literal["apiZone", "stepZone"]

R = TypeVar("R")

_async_local_storage: ContextVar[Optional["Zone"]] = ContextVar(
    "playwright_zone", default=None
)


class Zone:
    def __init__(self, store: Dict[ZoneType, Any]) -> None:
        self._data = store

    def with_(self, type: ZoneType, data: Any) -> "Zone":
        return Zone({**self._data, type: data})

    def without(self, type: Optional[ZoneType] = None) -> "Zone":
        data: Dict[ZoneType, Any] = dict(self._data) if type else {}
        if type:
            data.pop(type, None)
        return Zone(data)

    def run(self, func: Callable[[], R]) -> R:
        token = _async_local_storage.set(self)
        try:
            return func()
        finally:
            _async_local_storage.reset(token)

    async def run_async(self, func: Callable[[], Awaitable[R]]) -> R:
        # Python: run() of an async function. The coroutine runs when it is awaited,
        # so the zone must be current while it is awaited, not while it is created.
        token = _async_local_storage.set(self)
        try:
            return await func()
        finally:
            _async_local_storage.reset(token)

    def data(self, type: ZoneType) -> Any:
        return self._data.get(type)


empty_zone = Zone({})


def current_zone() -> Zone:
    return _async_local_storage.get() or empty_zone
