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
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, cast

from playwright.wait_helper import WaitHelper

loop = asyncio.get_event_loop()


class AsyncToSyncMapping:
    mapping: Dict[type, type] = {}

    def register(self, async_class: type, sync_class: type) -> None:
        self.mapping[async_class] = sync_class

    def from_maybe_async(self, obj: Any) -> Any:
        if not obj:
            return None
        if not obj._sync_owner:
            sync_class = self.mapping[type(obj)]
            if not sync_class:
                return None
            obj._sync_owner = sync_class(obj)
        return obj._sync_owner

    def from_async(self, obj: Any) -> Any:
        assert obj
        result = self.from_maybe_async(obj)
        assert result
        return result

    def from_async_nullable(self, obj: Any = None) -> Optional[Any]:
        return self.from_async(obj) if obj else None

    def from_async_list(self, items: List[Any]) -> List[Any]:
        return list(map(lambda a: self.from_async(a), items))

    def from_async_dict(self, map: Dict[str, Any]) -> Dict[str, Any]:
        return {name: self.from_async(value) for name, value in map.items()}


mapping = AsyncToSyncMapping()


T = TypeVar("T")


class EventInfo(Generic[T]):
    def __init__(
        self,
        sync_base: "SyncBase",
        event: str,
        predicate: Callable[[T], bool] = None,
        timeout: int = None,
    ) -> None:
        self._value: Optional[T] = None

        wait_helper = WaitHelper()
        wait_helper.reject_on_timeout(
            timeout or 30000, f'Timeout while waiting for event "${event}"'
        )
        self._future = loop.create_task(
            wait_helper.wait_for_event(sync_base._async_obj, event, predicate)
        )

    @property
    def value(self) -> T:
        if not self._value:
            value = loop.run_until_complete(self._future)
            self._value = mapping.from_async(value)
        return cast(T, self._value)


class EventContextManager(Generic[T]):
    def __init__(
        self,
        sync_base: "SyncBase",
        event: str,
        predicate: Callable[[T], bool] = None,
        timeout: int = None,
    ) -> None:
        self._event = EventInfo(sync_base, event, predicate, timeout)

    def __enter__(self) -> EventInfo[T]:
        return self._event

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._event.value


class SyncBase:
    def __init__(self, async_obj: Any) -> None:
        self._async_obj = async_obj

    def __str__(self) -> str:
        return self._async_obj.__str__()

    def _sync(self, future: asyncio.Future) -> Any:
        return loop.run_until_complete(future)

    def _wrap_handler_1(self, handler: Callable[[Any], None]) -> Callable[[Any], None]:
        return lambda arg: handler(mapping.from_maybe_async(arg))

    def _wrap_handler_2(
        self, handler: Callable[[Any, Any], None]
    ) -> Callable[[Any, Any], None]:
        return lambda arg1, arg2: handler(
            mapping.from_maybe_async(arg1), mapping.from_maybe_async(arg2)
        )

    def on(self, event_name: str, handler: Any) -> None:
        self._async_obj.on(event_name, self._wrap_handler_1(handler))

    def once(self, event_name: str, handler: Any) -> None:
        self._async_obj.once(event_name, self._wrap_handler_1(handler))

    def remove_listener(self, event_name: str, handler: Any) -> None:
        self._async_obj.remove_listener(event_name, handler)

    def expect_event(
        self, event: str, predicate: Callable[[Any], bool] = None, timeout: int = None,
    ) -> EventContextManager:
        return EventContextManager(self, event, predicate, timeout)
