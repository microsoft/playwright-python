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

"""Python only: the asyncio counterparts of the Promise built-ins that the client
uses. See transform.md, section 1.

JS cannot cancel a promise; Python can cancel a task. The rules here:
- race() cancels the tasks that it started for the coroutines it was given, and
  never a future or a task that it was given.
- fire_and_forget() keeps a reference to its task until the task is done.
"""

import asyncio
from typing import Any, Awaitable, Callable, List, Sequence, Set, TypeVar

T = TypeVar("T")

# The tasks of fire_and_forget(): the event loop keeps only weak references.
_tasks: Set["asyncio.Future[Any]"] = set()


def _handled(future: "asyncio.Future[Any]") -> None:
    # Reads the exception, so that asyncio does not log it as never retrieved.
    if not future.cancelled():
        future.exception()


def fire_and_forget(awaitable: Awaitable[Any]) -> None:
    """`promise.catch(() => {})` and `void promise`: runs an awaitable that nobody
    awaits. A coroutine runs as a task. The error of the awaitable is dropped."""
    future = asyncio.ensure_future(awaitable)
    _tasks.add(future)

    def done(f: "asyncio.Future[Any]") -> None:
        _tasks.discard(f)
        _handled(f)

    future.add_done_callback(done)


# The most turns of the event loop that wait_for_next_task() waits.
_MAX_TURNS = 100


async def wait_for_next_task() -> None:
    """Waits until the next task would start in JS: until every reaction to the
    current task has run. See transform.md, 1.17.

    JS calls a macrotask a task: a message from the driver, a timer, an I/O
    callback. All the promise reactions (microtasks) run before the next task.
    asyncio has one queue: the callback of a future, then each task that it wakes
    up, is a turn of its own, and the depth of a chain of reactions is not bounded
    (a wait, an expect_*() task, a gather, ...). So this yields until the queue is
    empty. The queue is not public API; on a loop that does not have it, this
    yields twice, the depth of a wait.
    """
    ready = getattr(asyncio.get_running_loop(), "_ready", None)
    if ready is None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return
    for _ in range(_MAX_TURNS):
        await asyncio.sleep(0)
        if not ready:
            return


def call_in_next_task(callback: Callable[[], Any]) -> None:
    """`setTimeout(callback, 0)`: the callback runs in the next task, after the
    reactions to the events that the current code emits; see wait_for_next_task()."""

    async def run() -> None:
        await wait_for_next_task()
        callback()

    fire_and_forget(run())


def completed(value: Any = None) -> "asyncio.Future[Any]":
    """`Promise.resolve(value)`."""
    future: "asyncio.Future[Any]" = asyncio.get_running_loop().create_future()
    future.set_result(value)
    return future


def failed(error: BaseException) -> "asyncio.Future[Any]":
    """`Promise.reject(error)`."""
    future: "asyncio.Future[Any]" = asyncio.get_running_loop().create_future()
    future.set_exception(error)
    return future


async def race(awaitables: Sequence[Awaitable[Any]]) -> Any:
    """`Promise.race(awaitables)`: the result, or the error, of the first awaitable
    that settles. When several have settled, the first in the list wins.

    The coroutines in the list run as tasks, which are cancelled when the race ends.
    A future or a task in the list runs on, as in JS. The errors of the losers are
    marked as handled, as Promise.race() handles them.
    """
    futures: List["asyncio.Future[Any]"] = []
    owned: List["asyncio.Future[Any]"] = []
    for awaitable in awaitables:
        if asyncio.isfuture(awaitable):
            futures.append(awaitable)
        else:
            task: "asyncio.Future[Any]" = asyncio.ensure_future(awaitable)
            futures.append(task)
            owned.append(task)
    for future in futures:
        future.add_done_callback(_handled)
    try:
        await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)
    finally:
        winner = next((f for f in futures if f.done()), None)
        for task in owned:
            if task is not winner:
                task.cancel()
    assert winner is not None
    return winner.result()
