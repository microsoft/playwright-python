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
from typing import TYPE_CHECKING, Any, Optional

from greenlet import GreenletExit, greenlet

from playwright._impl._errors import Error
from playwright._impl._greenlets import MainGreenlet
from playwright._impl.out_of_process import PlaywrightClient
from playwright.sync_api._generated import Playwright as SyncPlaywright

if TYPE_CHECKING:
    from asyncio.unix_events import AbstractChildWatcher


class PlaywrightContextManager:
    def __init__(self) -> None:
        self._playwright: SyncPlaywright
        self._loop: asyncio.AbstractEventLoop
        self._own_loop = False
        self._watcher: Optional[AbstractChildWatcher] = None
        self._exit_was_called = False
        self._dispatcher_fiber: MainGreenlet
        self._client: Optional[PlaywrightClient] = None

    def __enter__(self) -> SyncPlaywright:
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            self._own_loop = True
        if self._loop.is_running():
            raise Error(
                """It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead."""
            )

        g_self = greenlet.getcurrent()

        # The dispatcher fiber runs the event loop until the driver goes away. Every
        # sync call passes control to it while the call waits (wait_for_future() in
        # playwright/_impl/_greenlets.py). The client gets the fiber, so that the
        # event listeners and the user callbacks run in greenlets of their own.
        async def main() -> None:
            self._client = PlaywrightClient(dispatcher_fiber)
            self._client._playwright.add_done_callback(lambda _: g_self.switch())
            await self._client._close_promise

        def greenlet_main() -> None:
            task = self._loop.create_task(main())
            while not task.done():
                try:
                    self._loop.run_until_complete(task)
                except GreenletExit:
                    raise
                except BaseException as exc:
                    if task.done():
                        raise
                    # asyncio contains exceptions raised in tasks and callbacks.
                    # An exception that escapes the loop while the connection
                    # still runs comes from a signal handler, e.g. pytest-timeout
                    # or Ctrl+C, that fired while the loop waited for the driver.
                    # The user code is suspended in a sync call in the greenlet
                    # that created us: raise it there, and stay alive. The loop
                    # and its tasks are intact, so the next sync call resumes
                    # them.
                    g_self.throw(exc)
                    # Between sync calls the user code marks the loop as running,
                    # see wait_for_future. run_forever() refuses to start then.
                    asyncio._set_running_loop(None)

        dispatcher_fiber = self._dispatcher_fiber = MainGreenlet(greenlet_main)
        dispatcher_fiber.switch()

        assert self._client
        try:
            self._playwright = SyncPlaywright(self._client._playwright.result())
        except BaseException:
            self.__exit__()
            raise
        self._playwright.stop = self.__exit__  # type: ignore
        return self._playwright

    def start(self) -> SyncPlaywright:
        return self.__enter__()

    def __exit__(self, *args: Any) -> None:
        if self._exit_was_called:
            return
        self._exit_was_called = True
        if self._client:
            # Close the pipe, unless the driver exited on its own or did not start.
            # The dispatcher fiber runs the loop until the transport ends, then
            # exits and returns here. It may be suspended in the callback that
            # resumed this code, with the loop still running: switch to it also
            # when the transport has ended; a switch to a dead fiber returns.
            if not self._client._close_promise.done():
                self._client._transport.request_stop()
            self._dispatcher_fiber.switch()
        if self._watcher:
            self._watcher.close()
        if self._own_loop:
            tasks = asyncio.all_tasks(self._loop)
            for t in [t for t in tasks if not (t.done() or t.cancelled())]:
                t.cancel()
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
