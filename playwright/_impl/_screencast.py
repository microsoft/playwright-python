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
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Literal,
    Optional,
    Union,
)

from playwright._impl._api_structures import ScreencastFrame
from playwright._impl._artifact import Artifact
from playwright._impl._connection import from_channel
from playwright._impl._disposable import DisposableStub

if TYPE_CHECKING:
    from playwright._impl._page import Page


class Screencast:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._started = False
        self._save_path: Optional[Union[str, Path]] = None
        self._on_frame: Optional[Callable[[ScreencastFrame], None]] = None
        self._artifact: Optional[Artifact] = None
        self._page._channel.on("screencastFrame", self._handle_frame)

    def _handle_frame(self, params: Dict) -> None:
        if self._on_frame:
            self._on_frame({"data": base64.b64decode(params["data"])})

    async def start(
        self,
        path: Union[str, Path] = None,
        quality: int = None,
        onFrame: Callable[[ScreencastFrame], None] = None,
    ) -> DisposableStub:
        if self._started:
            raise Exception("Screencast is already started")
        self._started = True
        if onFrame:
            self._on_frame = onFrame
        result = await self._page._channel.send(
            "screencastStart",
            None,
            {
                "quality": quality,
                "sendFrames": onFrame is not None,
                "record": path is not None,
            },
        )
        if result:
            self._artifact = from_channel(result)
            self._save_path = path

        return DisposableStub(lambda: self.stop(), self._loop, self._dispatcher_fiber)

    async def stop(self) -> None:
        self._started = False
        self._on_frame = None
        await self._page._channel.send("screencastStop", None)
        if self._save_path and self._artifact:
            await self._artifact.save_as(self._save_path)
        self._artifact = None
        self._save_path = None

    async def show_actions(
        self,
        duration: float = None,
        position: Literal[
            "bottom", "bottom-left", "bottom-right", "top", "top-left", "top-right"
        ] = None,
        fontSize: int = None,
    ) -> DisposableStub:
        await self._page._channel.send(
            "screencastShowActions",
            None,
            {"duration": duration, "position": position, "fontSize": fontSize},
        )
        return DisposableStub(
            lambda: self.hide_actions(), self._loop, self._dispatcher_fiber
        )

    async def hide_actions(self) -> None:
        await self._page._channel.send("screencastHideActions", None)

    async def show_overlay(self, html: str, duration: float = None) -> DisposableStub:
        overlay_id = await self._page._channel.send(
            "screencastShowOverlay",
            None,
            {"html": html, "duration": duration},
        )

        return DisposableStub(
            lambda: self._page._channel.send(
                "screencastRemoveOverlay",
                None,
                {"id": overlay_id},
            ),
            self._loop,
            self._dispatcher_fiber,
        )

    async def show_chapter(
        self,
        title: str,
        description: str = None,
        duration: float = None,
    ) -> None:
        await self._page._channel.send(
            "screencastChapter",
            None,
            {"title": title, "description": description, "duration": duration},
        )

    async def show_overlays(self) -> None:
        await self._page._channel.send(
            "screencastSetOverlayVisible",
            None,
            {"visible": True},
        )

    async def hide_overlays(self) -> None:
        await self._page._channel.send(
            "screencastSetOverlayVisible",
            None,
            {"visible": False},
        )
