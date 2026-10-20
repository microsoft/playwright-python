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

"""Port of packages/playwright-core/src/client/screencast.ts.

Python: Screencast is not a ChannelOwner; it keeps the event loop of its page for
the generated API. The frame data is base64 on the channel; the on_frame callback
gets bytes, as it gets a Buffer upstream. The 'screencastFrame' listener is an async
function, so it runs in a task (see event_emitter.py).
"""

import base64
import inspect
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Literal,
    Optional,
    TypeVar,
    Union,
)

from playwright._impl._api_structures import (
    ScreencastActionStyle,
    ScreencastFrame,
    ScreencastSize,
)
from playwright._impl._errors import Error
from playwright._impl_v2.artifact import Artifact
from playwright._impl_v2.channel_owner import ApiCallOptions, api_call
from playwright._impl_v2.disposable import DisposableStub
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.tasks import fire_and_forget

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.channel_owner import ApiZone
    from playwright._impl_v2.page import Page

R = TypeVar("R")


class Screencast:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._started = False
        self._save_path: Optional[Union[str, Path]] = None
        self._on_frame: Optional[Callable[[ScreencastFrame], Any]] = None
        self._artifact: Optional[Artifact] = None
        # Python: the generated API reads the event loop of each object.
        self._loop = page._loop

        # Python: a sync listener that calls on_frame at once, as the JS async
        # listener does before its first await; the rest runs in a task.
        def on_screencast_frame(event: "channels.PageScreencastFrameEvent") -> Any:
            def ack() -> None:
                fire_and_forget(
                    self._page._channel.screencastFrameAck(
                        frameId=event["frameId"], timeout=NO_TIMEOUT
                    )
                )

            try:
                result = (
                    self._on_frame(
                        {
                            # Python: the channel has base64; the callback gets bytes.
                            "data": base64.b64decode(event["data"]),
                            "timestamp": event["timestamp"],
                            "viewportWidth": event["viewportWidth"],
                            "viewportHeight": event["viewportHeight"],
                        }
                    )
                    if self._on_frame
                    else None
                )
            except BaseException:
                ack()
                raise
            if not inspect.isawaitable(result):
                ack()
                return None
            awaitable = result

            async def rest() -> None:
                try:
                    await awaitable
                finally:
                    ack()

            return rest()

        self._page._channel.onScreencastFrame(on_screencast_frame)

    def _wrap_api_call(
        self,
        func: Callable[["ApiZone"], Awaitable[R]],
        options: Optional[ApiCallOptions] = None,
    ) -> Awaitable[R]:
        # Python: not an async def, as ChannelOwner._wrap_api_call().
        return self._page._wrap_api_call(func, options)

    async def start(
        self,
        on_frame: Optional[Callable[[ScreencastFrame], Any]],
        path: Optional[Union[str, Path]],
        size: Optional[ScreencastSize],
        quality: Optional[int],
        fps: Optional[int],
    ) -> DisposableStub:
        if self._started:
            raise Error("Screencast is already started")
        self._started = True
        if on_frame:
            self._on_frame = on_frame
        result = await self._page._channel.screencastStart(
            size=size,
            quality=quality,
            fps=fps,
            sendFrames=bool(on_frame),
            record=bool(path),
            timeout=NO_TIMEOUT,
        )
        if result["artifact"]:
            self._artifact = Artifact.from_(result["artifact"])
            self._save_path = path
        return DisposableStub(lambda: self.stop())

    @api_call()
    async def stop(self) -> None:
        self._started = False
        self._on_frame = None
        await self._page._channel.screencastStop(timeout=NO_TIMEOUT)
        if self._save_path:
            if self._artifact:
                await self._artifact.save_as(self._save_path)
        self._artifact = None
        self._save_path = None

    async def show_actions(
        self,
        duration: Optional[float],
        position: Optional[
            Literal[
                "top-left", "top", "top-right", "bottom-left", "bottom", "bottom-right"
            ]
        ],
        font_size: Optional[int],
        cursor: Optional[Literal["none", "pointer"]],
        style: Optional[ScreencastActionStyle],
    ) -> DisposableStub:
        await self._page._channel.screencastShowActions(
            duration=duration,
            position=position,
            fontSize=font_size,
            cursor=cursor,
            style=style,
            timeout=NO_TIMEOUT,
        )
        return DisposableStub(
            lambda: self._page._channel.screencastHideActions(timeout=NO_TIMEOUT)
        )

    async def hide_actions(self) -> None:
        await self._page._channel.screencastHideActions(timeout=NO_TIMEOUT)

    async def show_overlay(
        self, html: str, duration: Optional[float]
    ) -> DisposableStub:
        id = (
            await self._page._channel.screencastShowOverlay(
                html=html, duration=duration, timeout=NO_TIMEOUT
            )
        )["id"]
        return DisposableStub(
            lambda: self._page._channel.screencastRemoveOverlay(
                id=id, timeout=NO_TIMEOUT
            )
        )

    async def show_chapter(
        self, title: str, description: Optional[str], duration: Optional[float]
    ) -> None:
        await self._page._channel.screencastChapter(
            title=title, description=description, duration=duration, timeout=NO_TIMEOUT
        )

    async def show_overlays(self) -> None:
        await self._page._channel.screencastSetOverlayVisible(
            visible=True, timeout=NO_TIMEOUT
        )

    async def hide_overlays(self) -> None:
        await self._page._channel.screencastSetOverlayVisible(
            visible=False, timeout=NO_TIMEOUT
        )
