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

from playwright._impl._api_structures import ScreencastFrame
from playwright._impl._artifact import Artifact
from playwright._impl._connection import from_nullable_channel
from playwright._impl._errors import Error
from playwright._impl._helper import locals_to_params

if TYPE_CHECKING:  # pragma: no cover
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


class Screencast:
    def __init__(self, page: "Page") -> None:
        self._page = page
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._started = False
        self._save_path: Optional[Union[str, Path]] = None
        self._on_frame: Optional[ScreencastFrameCallback] = None
        self._artifact: Optional[Artifact] = None
        page._channel.on("screencastFrame", lambda params: self._dispatch_frame(params))

    def _dispatch_frame(self, params: dict) -> None:
        if not self._on_frame:
            return
        data = params["data"]
        if isinstance(data, str):
            data = base64.b64decode(data)
        result = self._on_frame({"data": data})
        if hasattr(result, "__await__"):
            self._page._loop.create_task(result)

    async def start(
        self,
        onFrame: ScreencastFrameCallback = None,
        path: Union[str, Path] = None,
        quality: int = None,
    ) -> None:
        if self._started:
            raise Error("Screencast is already started")
        self._started = True
        self._on_frame = onFrame
        result = await self._page._channel.send_return_as_dict(
            "screencastStart",
            None,
            {
                "quality": quality,
                "sendFrames": bool(onFrame),
                "record": bool(path),
            },
        )
        artifact_channel = (result or {}).get("artifact")
        if artifact_channel:
            self._artifact = from_nullable_channel(artifact_channel)
            self._save_path = path

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
        position: ScreencastPosition = None,
        fontSize: int = None,
    ) -> None:
        await self._page._channel.send(
            "screencastShowActions", None, locals_to_params(locals())
        )

    async def hide_actions(self) -> None:
        await self._page._channel.send("screencastHideActions", None)

    async def show_overlay(self, html: str, duration: float = None) -> None:
        await self._page._channel.send(
            "screencastShowOverlay", None, locals_to_params(locals())
        )

    async def show_chapter(
        self,
        title: str,
        description: str = None,
        duration: float = None,
    ) -> None:
        await self._page._channel.send(
            "screencastChapter", None, locals_to_params(locals())
        )

    async def show_overlays(self) -> None:
        await self._page._channel.send(
            "screencastSetOverlayVisible", None, {"visible": True}
        )

    async def hide_overlays(self) -> None:
        await self._page._channel.send(
            "screencastSetOverlayVisible", None, {"visible": False}
        )
