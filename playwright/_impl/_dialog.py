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

from typing import TYPE_CHECKING, Dict, Optional

from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._errors import is_target_closed_error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page
    from playwright._impl._protocol_channels import DialogChannel


class Dialog(ChannelOwner):
    _channel: "DialogChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._page: Optional["Page"] = from_nullable_channel(initializer.get("page"))

    def __repr__(self) -> str:
        return f"<Dialog type={self.type} message={self.message} default_value={self.default_value}>"

    @property
    def type(self) -> str:
        return self._initializer["type"]

    @property
    def message(self) -> str:
        return self._initializer["message"]

    @property
    def default_value(self) -> str:
        return self._initializer["defaultValue"]

    @property
    def page(self) -> Optional["Page"]:
        return self._page

    async def accept(self, prompt_text: Optional[str]) -> None:
        await self._channel.accept(promptText=prompt_text)

    async def dismiss(self) -> None:
        try:
            await self._channel.dismiss()
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise
