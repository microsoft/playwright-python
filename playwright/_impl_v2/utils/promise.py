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

"""Python only: the counterparts of the Promise built-ins that the client uses.

A JS promise runs whether or not someone awaits it, and nobody can cancel it. Here
a coroutine becomes a task. Cancellation is Python only: when the task that awaits
a helper is cancelled, the helper cancels the tasks that it started for its own
coroutines (so that a channel call is aborted), but never a future that it was
given, because other code may await that future too. A future whose exception the
JS code handles is not logged as "never retrieved".
"""

import asyncio
import contextvars
import inspect
import sys
import types
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    List,
    Optional,
    Sequence,
    TypeVar,
    cast,
)

T = TypeVar("T")


def _loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_event_loop()


def resolved(value: Any = None) -> "asyncio.Future[Any]":
    """Promise.resolve(value)."""
    future = _loop().create_future()
    future.set_result(value)
    return future


def rejected(error: BaseException) -> "asyncio.Future[Any]":
    """Promise.reject(error)."""
    future = _loop().create_future()
    future.set_exception(error)
    return future


def run_now(func: Callable[[], Awaitable[T]]) -> Awaitable[T]:
    """The call of a function that returns a promise: a throw rejects the promise.

    A JS async function never throws when it is called; it returns a rejected
    promise. A Python function that sends at once can raise; this turns the raise
    into a failed future.
    """
    try:
        return func()
    except Exception as error:
        return rejected(error)


def start(awaitable: Awaitable[T]) -> "asyncio.Future[T]":
    """A promise: starts a coroutine as a task, keeps a future as it is."""
    return asyncio.ensure_future(awaitable)


def start_eager(awaitable: Awaitable[T]) -> "asyncio.Future[T]":
    """The promise of a JS async function: its body runs at once, up to the first
    await, and the rest runs in a task.

    The first step runs in a copy of the current context, which the task then has,
    as an eager task (Python 3.12) has its own context from the start.
    """
    if not inspect.iscoroutine(awaitable):
        return asyncio.ensure_future(awaitable)
    coro = awaitable
    if sys.version_info >= (3, 12):
        return asyncio.Task(coro, loop=_loop(), eager_start=True)
    context = contextvars.copy_context()
    try:
        first = context.run(coro.send, None)
    except StopIteration as stop:
        return resolved(stop.value)
    except BaseException as error:
        return rejected(error)

    async def rest() -> T:
        return await cast(Awaitable[T], _resume(coro, first))

    return context.run(asyncio.ensure_future, rest())


@types.coroutine
def _resume(coro: Coroutine[Any, Any, T], first: Any) -> Generator[Any, Any, T]:
    # Drives a coroutine that has run its first step: the task waits for what the
    # coroutine waits for, and sends or throws the outcome into it.
    value = first
    while True:
        try:
            sent = yield value
        except GeneratorExit:
            coro.close()
            raise
        except BaseException as error:
            try:
                value = coro.throw(error)
            except StopIteration as stop:
                return stop.value
            continue
        try:
            value = coro.send(sent)
        except StopIteration as stop:
            return stop.value


def retrieve(future: "asyncio.Future[Any]") -> None:
    """A done callback that marks the exception of a future as retrieved."""
    if not future.cancelled():
        future.exception()


def ignore_unhandled(future: "asyncio.Future[Any]") -> None:
    """Marks the exception of a future as retrieved, as a handled rejection."""
    future.add_done_callback(retrieve)


def _settle(result: "asyncio.Future[Any]", value: Any) -> None:
    # A thenable that a reaction returns is adopted, as in JS.
    if inspect.isawaitable(value):
        source = start(value)

        def on_done(f: "asyncio.Future[Any]") -> None:
            if result.done():
                return
            if f.cancelled():
                result.cancel()
                return
            error = f.exception()
            if error is not None:
                result.set_exception(error)
            else:
                result.set_result(f.result())

        source.add_done_callback(on_done)
        return
    result.set_result(value)


def catch(
    awaitable: Awaitable[T],
    handler: Optional[Callable[[Exception], Any]] = None,
    owns_source: Optional[bool] = None,
) -> "asyncio.Future[Any]":
    """promise.catch(handler), and promise.catch(() => {}) when handler is None."""
    owned = inspect.iscoroutine(awaitable) if owns_source is None else owns_source
    future = start(awaitable)
    result = _loop().create_future()

    def on_done(f: "asyncio.Future[T]") -> None:
        if result.done():
            return
        if f.cancelled():
            result.cancel()
            return
        error = f.exception()
        if error is None:
            result.set_result(f.result())
            return
        if not isinstance(error, Exception):
            result.set_exception(error)
            return
        try:
            _settle(result, handler(error) if handler else None)
        except Exception as e:
            result.set_exception(e)

    future.add_done_callback(on_done)
    if owned:
        _propagate_cancel(result, future)
    return result


def then(
    awaitable: Awaitable[T],
    on_fulfilled: Callable[[T], Any],
    owns_source: Optional[bool] = None,
) -> "asyncio.Future[Any]":
    """promise.then(onFulfilled): a rejection passes through.

    owns_source: whether the source was made for this chain only, so that a
    cancel of the result may cancel it; by default, when it is a coroutine.
    """
    owned = inspect.iscoroutine(awaitable) if owns_source is None else owns_source
    future = start(awaitable)
    result = _loop().create_future()

    def on_done(f: "asyncio.Future[T]") -> None:
        if result.done():
            return
        if f.cancelled():
            result.cancel()
            return
        error = f.exception()
        if error is not None:
            result.set_exception(error)
            return
        try:
            _settle(result, on_fulfilled(f.result()))
        except BaseException as e:
            result.set_exception(e)

    future.add_done_callback(on_done)
    if owned:
        _propagate_cancel(result, future)
    else:
        ignore_unhandled(future)
    return result


def _propagate_cancel(
    result: "asyncio.Future[Any]", source: "asyncio.Future[Any]"
) -> None:
    def on_done(f: "asyncio.Future[Any]") -> None:
        if f.cancelled() and not source.done():
            source.cancel()

    result.add_done_callback(on_done)


def _start_all(
    awaitables: Sequence[Awaitable[Any]],
) -> List["asyncio.Future[Any]"]:
    futures: List["asyncio.Future[Any]"] = []
    for awaitable in awaitables:
        future = start(awaitable)
        setattr(future, "_pw_owned", inspect.iscoroutine(awaitable))
        ignore_unhandled(future)
        futures.append(future)
    return futures


def _cancel_owned(futures: Sequence["asyncio.Future[Any]"]) -> None:
    for future in futures:
        if getattr(future, "_pw_owned", False) and not future.done():
            future.cancel()


async def race(awaitables: Sequence[Awaitable[Any]]) -> Any:
    """Promise.race(awaitables).

    The first one to settle wins; when several have settled, the first in the list
    wins, as their reactions run in that order. The others go on, as in JS.
    """
    futures = _start_all(awaitables)
    try:
        while True:
            for future in futures:
                if future.done():
                    return future.result()
            await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        _cancel_owned(futures)
        raise


async def all_(awaitables: Sequence[Awaitable[Any]]) -> List[Any]:
    """Promise.all(awaitables): the first rejection rejects; nothing is cancelled."""
    futures = _start_all(awaitables)
    try:
        pending = set(futures)
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_EXCEPTION
            )
            for future in futures:
                if future in done and not future.cancelled():
                    error = future.exception()
                    if error is not None:
                        raise error
        return [future.result() for future in futures]
    except asyncio.CancelledError:
        _cancel_owned(futures)
        raise


_MAX_IDLE_YIELDS = 100


async def when_idle() -> None:
    """Waits until the event loop has no other callback ready to run.

    In JS, the reactions of the promises (microtasks) all run before the next timer
    or I/O callback (macrotask). asyncio has one queue: a future reaction, then each
    task step that it resumes, is a callback of its own. So a macrotask waits until
    no callback is ready, as the transport does after each message.
    """
    ready = getattr(asyncio.get_running_loop(), "_ready", None)
    for _ in range(_MAX_IDLE_YIELDS):
        await asyncio.sleep(0)
        if not ready:
            return


class Timer:
    """The handle that setTimeout() returns."""

    def __init__(self, callback: Callable[[], Any], timeout: float) -> None:
        self._callback = callback
        self._task: Optional["asyncio.Future[None]"] = None
        self._handle: Optional[asyncio.TimerHandle] = _loop().call_later(
            timeout / 1000, self._fire
        )

    def _fire(self) -> None:
        self._handle = None

        async def run() -> None:
            await when_idle()
            self._task = None
            self._callback()

        self._task = asyncio.ensure_future(run())

    def cancel(self) -> None:
        if self._handle:
            self._handle.cancel()
            self._handle = None
        if self._task:
            self._task.cancel()
            self._task = None


def set_timeout(callback: Callable[[], Any], timeout: float) -> Timer:
    """setTimeout(callback, timeout): timeout in milliseconds, run as a macrotask."""
    return Timer(callback, timeout)


def clear_timeout(handle: Optional[Timer]) -> None:
    if handle:
        handle.cancel()
