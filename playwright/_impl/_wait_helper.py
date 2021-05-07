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
import uuid
from asyncio.tasks import Task
from typing import Any, Callable, List, Tuple

from pyee import EventEmitter

from playwright._impl._api_types import Error, TimeoutError
from playwright._impl._connection import ChannelOwner


class WaitHelper:
    def __init__(self, channel_owner: ChannelOwner, api_name: str) -> None:
        self._result: asyncio.Future = asyncio.Future()
        self._wait_id = uuid.uuid4().hex
        self._loop = channel_owner._loop
        self._pending_tasks: List[Task] = []
        self._channel_owner = channel_owner
        self._registered_listeners: List[Tuple[EventEmitter, str, Callable]] = []
        channel_owner._wait_for_event_info_before(self._wait_id, api_name)

    def reject_on_event(
        self,
        emitter: EventEmitter,
        event: str,
        error: Error,
        predicate: Callable = None,
    ) -> None:
        def listener(event_data: Any = None) -> None:
            if not predicate or predicate(event_data):
                self._reject(error)

        emitter.on(event, listener)
        self._registered_listeners.append((emitter, event, listener))

    def reject_on_timeout(self, timeout: float, message: str) -> None:
        if timeout == 0:
            return

        async def reject() -> None:
            await asyncio.sleep(timeout / 1000)
            self._reject(TimeoutError(message))

        self._pending_tasks.append(self._loop.create_task(reject()))

    def _cleanup(self) -> None:
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        for listener in self._registered_listeners:
            listener[0].remove_listener(listener[1], listener[2])

    def _fulfill(self, result: Any) -> None:
        self._cleanup()
        if not self._result.done():
            self._result.set_result(result)
        self._channel_owner._wait_for_event_info_after(self._wait_id)

    def _reject(self, exception: Exception) -> None:
        self._cleanup()
        if not self._result.done():
            self._result.set_exception(exception)
        self._channel_owner._wait_for_event_info_after(self._wait_id, exception)

    def wait_for_event(
        self,
        emitter: EventEmitter,
        event: str,
        predicate: Callable = None,
    ) -> None:
        def listener(event_data: Any = None) -> None:
            if not predicate or predicate(event_data):
                self._fulfill(event_data)

        emitter.on(event, listener)
        self._registered_listeners.append((emitter, event, listener))

    def result(self) -> asyncio.Future:
        return self._result


def throw_on_timeout(timeout: float, exception: Exception) -> asyncio.Task:
    async def throw() -> None:
        await asyncio.sleep(timeout / 1000)
        raise exception

    return asyncio.create_task(throw())
