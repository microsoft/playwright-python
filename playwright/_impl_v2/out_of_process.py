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

"""Port of packages/playwright-core/src/outofprocess.ts.

Python: the driver is the bundled Node.js driver, run by the PipeTransport of
playwright/_impl_v2/transport.py. The transport reads the messages in a task and
waits for the next task after each one, as Node.js dispatches each message in its
own macrotask.
"""

import asyncio
from typing import Any, Tuple

from playwright._impl_v2.connection import Connection
from playwright._impl_v2.playwright import Playwright
from playwright._impl_v2.transport import PipeTransport


async def start() -> Tuple[Playwright, "PlaywrightClient"]:
    client = PlaywrightClient()
    playwright = await client._playwright
    return playwright, client


class PlaywrightClient:
    def __init__(self, dispatcher_fiber: Any = None) -> None:
        # Python: the sync API passes the greenlet that runs the loop, see
        # playwright/sync_api/_context_manager.py.
        loop = asyncio.get_running_loop()
        self._close_promise: "asyncio.Future[None]" = loop.create_future()
        connection = Connection(loop, dispatcher_fiber=dispatcher_fiber)
        self._transport = transport = PipeTransport(loop)
        self._connection = connection
        connection.onmessage = lambda message: transport.send(message)

        def on_message(message: Any) -> None:
            # Python: an exception in a listener crashes Node.js; here the next API
            # call raises it, and the transport goes on.
            try:
                connection.dispatch(message)
            except Exception as error:
                connection._on_event_listener_error(error)

        transport.on_message = on_message
        self._playwright = asyncio.ensure_future(self._run(connection))

    async def _run(self, connection: Connection) -> Playwright:
        try:
            await self._transport.connect()
        except Exception:
            # Python: the driver did not start, so stop() has nothing to wait for.
            self._close_promise.set_result(None)
            raise
        reader = asyncio.ensure_future(self._transport.run())

        def on_close(reader: "asyncio.Future[None]") -> None:
            # Python: reads the error of the reader, so that asyncio does not log it
            # as never retrieved.
            if not reader.cancelled():
                reader.exception()
            if not self._close_promise.done():
                self._close_promise.set_result(None)
            # Python: the calls in flight fail when the driver goes away; upstream
            # leaves them pending.
            connection.close()

        reader.add_done_callback(on_close)
        initialize = asyncio.ensure_future(connection.initialize_playwright())
        done, _ = await asyncio.wait(
            {initialize, self._transport.on_error_future},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if initialize not in done:
            initialize.cancel()
        return next(iter(done)).result()

    async def stop(self) -> None:
        if not self._close_promise.done():
            self._transport.request_stop()
        await self._close_promise
