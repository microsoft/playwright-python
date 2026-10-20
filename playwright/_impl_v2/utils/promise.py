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
import inspect
from typing import Any, Awaitable, Callable, List, Optional, Sequence, TypeVar

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


def set_timeout(callback: Callable[[], Any], timeout: float) -> asyncio.TimerHandle:
    """setTimeout(callback, timeout): timeout in milliseconds."""
    return _loop().call_later(timeout / 1000, callback)


def clear_timeout(handle: Optional[asyncio.TimerHandle]) -> None:
    if handle:
        handle.cancel()
