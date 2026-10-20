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

"""Port of packages/playwright-core/src/client/dialog.ts.

Python: page, type, message and default_value are properties, as the generated API
reads them.
"""

from typing import TYPE_CHECKING, Optional

from playwright._impl_v2.channel_owner import ChannelOwner, from_channel
from playwright._impl_v2.errors import is_target_closed_error
from playwright._impl_v2.page import Page
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.protocol_channels import DialogChannel


class Dialog(ChannelOwner):
    _channel: "DialogChannel"

    @staticmethod
    def from_(dialog: "DialogChannel") -> "Dialog":
        return from_channel(dialog)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.DialogInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Note: dialogs that open early during page initialization block it.
        # Therefore, we must report the dialog without a page to be able to handle it.
        self._page: Optional[Page] = Page.from_nullable(initializer.get("page"))

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def type(self) -> str:
        return self._initializer["type"]

    @property
    def message(self) -> str:
        return self._initializer["message"]

    @property
    def default_value(self) -> str:
        return self._initializer["defaultValue"]

    async def accept(self, prompt_text: Optional[str]) -> None:
        await self._channel.accept(promptText=prompt_text, timeout=NO_TIMEOUT)

    async def dismiss(self) -> None:
        try:
            await self._channel.dismiss(timeout=NO_TIMEOUT)
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Dialog type={self.type} message={self.message} default_value={self.default_value}>"
