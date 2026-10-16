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

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional, Union

from playwright._impl._api_structures import (
    ScreencastActionStyle,
    ScreencastFrame,
    ScreencastSize,
)
from playwright._impl._artifact import Artifact
from playwright._impl._connection import from_nullable_channel
from playwright._impl._disposable import DisposableStub
from playwright._impl._errors import Error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._page import Page


ScreencastFrameCallback = Callable[[ScreencastFrame], Any]
ScreencastPosition = Literal[
    "bottom",
    "bottom-left",
    "bottom-right",
    "top",
    "top-left",
    "top-right",
]
ScreencastCursor = Literal[
    "none",
    "pointer",
]


class Screencast:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._started = False
        self._save_path: Optional[Union[str, Path]] = None
        self._on_frame: Optional[ScreencastFrameCallback] = None
        self._artifact: Optional[Artifact] = None
        page._channel.onScreencastFrame(self._dispatch_frame)

    def _ack_frame(self, frame_id: int) -> None:
        try:
            self._page._channel.send_no_reply(
                "screencastFrameAck", {"frameId": frame_id}
            )
        except (Error, OSError):
            pass

    async def _await_callback_and_ack(self, result: Any, frame_id: int) -> None:
        try:
            await result
        finally:
            self._ack_frame(frame_id)

    def _dispatch_frame(self, event: "channels.PageScreencastFrameEvent") -> Any:
        result = None
        task = None
        try:
            if not self._on_frame:
                return
            result = self._on_frame(
                {
                    "data": base64.b64decode(event["data"]),
                    "timestamp": event["timestamp"],
                    "viewportWidth": event["viewportWidth"],
                    "viewportHeight": event["viewportHeight"],
                }
            )
        finally:
            if hasattr(result, "__await__"):
                task = self._loop.create_task(
                    self._await_callback_and_ack(result, event["frameId"])
                )
            else:
                self._ack_frame(event["frameId"])
        return task

    async def start(
        self,
        on_frame: Optional[ScreencastFrameCallback],
        path: Optional[Union[str, Path]],
        quality: Optional[int],
        size: Optional[ScreencastSize],
        fps: Optional[int],
    ) -> DisposableStub:
        if self._started:
            raise Error("Screencast is already started")
        self._started = True
        self._on_frame = on_frame
        result = await self._page._channel.screencastStart(
            size=size,
            quality=quality,
            fps=fps,
            sendFrames=bool(on_frame),
            record=bool(path),
        )
        if result["artifact"]:
            self._artifact = from_nullable_channel(result["artifact"])
            self._save_path = path
        return DisposableStub(lambda: self.stop(), self._page)

    async def stop(self) -> None:
        self._started = False
        self._on_frame = None
        await self._page._channel.screencastStop()
        if self._save_path and self._artifact:
            await self._artifact.save_as(self._save_path)
        self._artifact = None
        self._save_path = None

    async def show_actions(
        self,
        duration: Optional[float],
        position: Optional[ScreencastPosition],
        font_size: Optional[int],
        cursor: Optional[ScreencastCursor],
        style: Optional[ScreencastActionStyle],
    ) -> DisposableStub:
        await self._page._channel.screencastShowActions(
            duration=duration,
            position=position,
            fontSize=font_size,
            cursor=cursor,
            style=style,
        )
        return DisposableStub(lambda: self.hide_actions(), self._page)

    async def hide_actions(self) -> None:
        await self._page._channel.screencastHideActions()

    async def show_overlay(
        self, html: str, duration: Optional[float]
    ) -> DisposableStub:
        result = await self._page._channel.screencastShowOverlay(
            html=html, duration=duration
        )
        overlay_id = result["id"]
        return DisposableStub(
            lambda: self._page._channel.screencastRemoveOverlay(id=overlay_id),
            self._page,
        )

    async def show_chapter(
        self,
        title: str,
        description: Optional[str],
        duration: Optional[float],
    ) -> None:
        await self._page._channel.screencastChapter(
            title=title, description=description, duration=duration
        )

    async def show_overlays(self) -> None:
        await self._page._channel.screencastSetOverlayVisible(visible=True)

    async def hide_overlays(self) -> None:
        await self._page._channel.screencastSetOverlayVisible(visible=False)
