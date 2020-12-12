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
from typing import Any, Callable, List

from pyee import EventEmitter

from playwright._types import Error, TimeoutError


class WaitHelper:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._failures: List[asyncio.Future] = []
        self._loop = loop

    def reject_on_event(
        self,
        emitter: EventEmitter,
        event: str,
        error: Error,
        predicate: Callable[[Any], bool] = None,
    ) -> None:
        self.reject_on(wait_for_event_future(emitter, event, predicate), error)

    def reject_on_timeout(self, timeout: int, message: str) -> None:
        if timeout == 0:
            return
        self.reject_on(
            self._loop.create_task(asyncio.sleep(timeout / 1000)), TimeoutError(message)
        )

    def reject_on(self, future: asyncio.Future, error: Error) -> None:
        async def future_wrapper() -> Error:
            await future
            return error

        result = self._loop.create_task(future_wrapper())
        result.add_done_callback(lambda f: future.cancel())
        self._failures.append(result)

    async def wait_for_event(
        self,
        emitter: EventEmitter,
        event: str,
        predicate: Callable[[Any], bool] = None,
    ) -> Any:
        future = wait_for_event_future(emitter, event, predicate)
        return await self.wait_for_future(future)

    async def wait_for_future(self, future: asyncio.Future) -> Any:
        done, _ = await asyncio.wait(
            set([future, *self._failures]), return_when=asyncio.FIRST_COMPLETED
        )
        if future not in done:
            future.cancel()
        for failure in self._failures:
            if failure not in done:
                failure.cancel()
        for failure in self._failures:
            if failure in done:
                raise failure.result()
        return future.result()


def wait_for_event_future(
    emitter: EventEmitter, event: str, predicate: Callable[[Any], bool] = None
) -> asyncio.Future:
    future: asyncio.Future = asyncio.Future()

    def listener(event_data: Any = None) -> None:
        if not predicate or predicate(event_data):
            future.set_result(event_data)

    emitter.on(event, listener)

    future.add_done_callback(lambda f: emitter.remove_listener(event, listener))
    return future
