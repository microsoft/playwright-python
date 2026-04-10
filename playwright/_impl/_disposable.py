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

from typing import Awaitable, Callable, Dict

from playwright._impl._connection import ChannelOwner
from playwright._impl._errors import is_target_closed_error


class Disposable(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def dispose(self) -> None:
        try:
            await self._channel.send(
                "dispose",
                None,
            )
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    def __repr__(self) -> str:
        return "<Disposable>"


class DisposableStub:
    def __init__(self, dispose_fn: Callable[[], Awaitable[None]]) -> None:
        self._dispose_fn = dispose_fn

    async def dispose(self) -> None:
        await self._dispose_fn()

    def __repr__(self) -> str:
        return "<Disposable>"
