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
import os
from typing import Tuple

import greenlet

from playwright._impl._errors import TargetClosedError


def _greenlet_trace_callback(
    event: str, args: Tuple[greenlet.greenlet, greenlet.greenlet]
) -> None:
    if event in ("switch", "throw"):
        origin, target = args
        print(f"Transfer from {origin} to {target} with {event}")


if os.environ.get("INTERNAL_PW_GREENLET_DEBUG"):
    greenlet.settrace(_greenlet_trace_callback)


class MainGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<MainGreenlet>"


class RouteGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<RouteGreenlet>"


class LocatorHandlerGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<LocatorHandlerGreenlet>"


class EventGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<EventGreenlet>"


def connection_closed_error() -> TargetClosedError:
    return TargetClosedError("Playwright connection closed")


def wait_for_future(
    loop: asyncio.AbstractEventLoop,
    dispatcher_fiber: greenlet.greenlet,
    future: "asyncio.Future",
) -> None:
    __tracebackhide__ = True
    g_self = greenlet.getcurrent()

    def resume(_: "asyncio.Future") -> None:
        g_self.switch()

    # The wait owns the callback that resumes this greenlet, so that it can
    # remove it again when the wait is abandoned. A callback left behind would
    # resume this greenlet at an arbitrary later point.
    future.add_done_callback(resume)
    try:
        while not future.done():
            # The dispatcher fiber exits once the connection to the driver ends,
            # e.g. when the driver process dies. Nothing can settle the future
            # after that, and switching to a dead greenlet returns right away,
            # so we would spin.
            if dispatcher_fiber.dead:
                raise connection_closed_error()
            # Raises when a signal handler interrupted the event loop while it
            # waited for the driver, see greenlet_main in _context_manager.py.
            dispatcher_fiber.switch()
    except BaseException:
        future.remove_done_callback(resume)
        future.cancel()
        raise
    finally:
        # The loop is only running for as long as the dispatcher fiber is alive.
        # Also after a signal handler interrupted it: run_forever() cleared this
        # on its way out, but the dispatcher is going to run the loop again.
        if not dispatcher_fiber.dead:
            asyncio._set_running_loop(loop)
