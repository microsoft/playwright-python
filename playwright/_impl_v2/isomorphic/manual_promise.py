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

"""Port of packages/isomorphic/manualPromise.ts.

Python: a ManualPromise is an asyncio.Future. signalToPromise() is not ported:
Python has no AbortSignal.
"""

import asyncio
import traceback
from typing import (
    Any,
    Awaitable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
)

from playwright._impl._errors import Error
from playwright._impl_v2.utils.tasks import race

T = TypeVar("T")


class ManualPromise(asyncio.Future, Generic[T]):
    def __init__(self) -> None:
        super().__init__(loop=asyncio.get_event_loop())
        self._is_done = False

    def __await__(self) -> Any:
        # Python: a task that is cancelled cancels the future it awaits. A promise
        # can not be cancelled, and several tasks may await this one.
        if self.done():
            return super().__await__()
        return asyncio.shield(self).__await__()

    def is_done(self) -> bool:
        return self._is_done

    def resolve(self, t: Optional[T] = None) -> None:
        self._is_done = True
        # Python: a promise ignores a second resolve; a future raises.
        if not self.done():
            self.set_result(t)

    def reject(self, e: BaseException) -> None:
        self._is_done = True
        if not self.done():
            self.set_exception(e)


class LongStandingScope:
    def __init__(self) -> None:
        self._terminate_error: Optional[Exception] = None
        self._close_error: Optional[Exception] = None
        self._terminate_promises: Dict[ManualPromise, "_Frames"] = {}
        self._is_closed = False

    def reject(self, error: Exception) -> None:
        self._is_closed = True
        self._terminate_error = error
        for p in list(self._terminate_promises.keys()):
            p.resolve(error)

    def close(self, error: Exception) -> None:
        self._is_closed = True
        self._close_error = error
        for p, frames in list(self._terminate_promises.items()):
            p.resolve(clone_error(error, frames))

    def is_closed(self) -> bool:
        return self._is_closed

    @staticmethod
    async def race_multiple(
        scopes: Sequence["LongStandingScope"], promise: Awaitable[T]
    ) -> T:
        future = asyncio.ensure_future(promise)
        return await race([s.race(future) for s in scopes])

    async def race(self, promise: Union[Awaitable[T], Sequence[Awaitable[T]]]) -> T:
        promises: List[Awaitable[Any]] = []
        if isinstance(promise, (list, tuple)):
            promises.extend(promise)
        else:
            promises.append(cast(Awaitable[Any], promise))
        return await self._race(promises, False)

    async def safe_race(self, promise: Awaitable[T], default_value: Any = None) -> Any:
        return await self._race([promise], True, default_value)

    async def _race(
        self, promises: List[Awaitable[Any]], safe: bool, default_value: Any = None
    ) -> Any:
        terminate_promise: ManualPromise[Exception] = ManualPromise()
        # Python: the frames are formatted only when an error is cloned; reading the
        # source lines on every race would be slow.
        frames = _Frames(
            traceback.StackSummary.extract(
                traceback.walk_stack(None), lookup_lines=False
            )
        )
        if self._terminate_error:
            terminate_promise.resolve(self._terminate_error)
        if self._close_error:
            terminate_promise.resolve(clone_error(self._close_error, frames))
        self._terminate_promises[terminate_promise] = frames

        async def terminated() -> Any:
            e = await terminate_promise
            if safe:
                return default_value
            raise e

        # Python: the task that waits for the termination ends with the race; a
        # promise that never settles costs nothing in JS.
        terminated_task = asyncio.ensure_future(terminated())
        try:
            return await race([terminated_task, *promises])
        finally:
            self._terminate_promises.pop(terminate_promise, None)
            terminated_task.cancel()


class _Frames:
    def __init__(self, summary: traceback.StackSummary) -> None:
        self._summary = summary

    def lines(self) -> List[str]:
        return [line.rstrip() for line in self._summary.format()]


def clone_error(error: Exception, frames: _Frames) -> Exception:
    # Python: like `new Error()`, the clone is a plain Error with the name and the
    # message of the error.
    name = error.name if isinstance(error, Error) else type(error).__name__
    message = error.message if isinstance(error, Error) else str(error)
    clone = Error(message)
    clone._name = name
    clone._stack = "\n".join([name + ":" + message, *frames.lines()])
    return clone
