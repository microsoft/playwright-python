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
from pathlib import Path
from typing import Any, Dict, List, Set, Union

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import Error
from playwright._impl._helper import async_readfile
from playwright._impl._locator import set_test_id_attribute_name, test_id_attribute_name


class Selectors:
    def __init__(self, loop: asyncio.AbstractEventLoop, dispatcher_fiber: Any) -> None:
        self._loop = loop
        self._channels: Set[SelectorsOwner] = set()
        self._registrations: List[Dict] = []
        self._dispatcher_fiber = dispatcher_fiber

    async def register(
        self,
        name: str,
        script: str = None,
        path: Union[str, Path] = None,
        contentScript: bool = None,
    ) -> None:
        if not script and not path:
            raise Error("Either source or path should be specified")
        if path:
            script = (await async_readfile(path)).decode()
        params: Dict[str, Any] = dict(name=name, source=script)
        if contentScript:
            params["contentScript"] = True
        for channel in self._channels:
            await channel._channel.send("register", params)
        self._registrations.append(params)

    def set_test_id_attribute(self, attribute_name: str) -> None:
        set_test_id_attribute_name(attribute_name)
        for channel in self._channels:
            channel._channel.send_no_reply(
                "setTestIdAttributeName", {"testIdAttributeName": attribute_name}
            )

    def _add_channel(self, channel: "SelectorsOwner") -> None:
        self._channels.add(channel)
        for params in self._registrations:
            # This should not fail except for connection closure, but just in case we catch.
            channel._channel.send_no_reply("register", params)
            channel._channel.send_no_reply(
                "setTestIdAttributeName",
                {"testIdAttributeName": test_id_attribute_name()},
            )

    def _remove_channel(self, channel: "SelectorsOwner") -> None:
        if channel in self._channels:
            self._channels.remove(channel)


class SelectorsOwner(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
