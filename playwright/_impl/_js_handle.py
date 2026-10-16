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

"""Port of packages/playwright-core/src/client/jsHandle.ts."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from playwright._impl._channel import Channel
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._serializers import parse_value, serialize_value

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._element_handle import ElementHandle
    from playwright._impl._protocol_channels import JSHandleChannel


Serializable = Any


class JSHandle(ChannelOwner):
    _channel: "JSHandleChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._preview = self._initializer["preview"]
        self._channel.onPreviewUpdated(self._on_preview_updated)

    def __repr__(self) -> str:
        return f"<JSHandle preview={self._preview}>"

    def __str__(self) -> str:
        return self._preview

    def _on_preview_updated(
        self, event: "channels.JSHandlePreviewUpdatedEvent"
    ) -> None:
        self._preview = event["preview"]

    async def evaluate(self, expression: str, arg: Serializable) -> Any:
        result = await self._channel.evaluateExpression(
            expression=expression, isFunction=None, arg=serialize_argument(arg)
        )
        return parse_result(result["value"])

    async def evaluate_handle(self, expression: str, arg: Serializable) -> "JSHandle":
        result = await self._channel.evaluateExpressionHandle(
            expression=expression, isFunction=None, arg=serialize_argument(arg)
        )
        return from_channel(result["handle"])

    async def get_property(self, property_name: str) -> "JSHandle":
        return from_channel(
            (await self._channel.getProperty(name=property_name))["handle"]
        )

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        result = await self._channel.getPropertyList()
        return {
            prop["name"]: from_channel(prop["value"]) for prop in result["properties"]
        }

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        try:
            await self._channel.dispose()
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    async def json_value(self) -> Any:
        return parse_result((await self._channel.jsonValue())["value"])


def serialize_argument(arg: Serializable = None) -> Any:
    handles: List[Channel] = []

    def serialize_handle(value: Any) -> Optional[Dict[str, Any]]:
        if isinstance(value, JSHandle):
            handles.append(value._channel)
            return {"h": len(handles) - 1}
        return None

    value = serialize_value(arg, serialize_handle)
    return dict(value=value, handles=handles)


def parse_result(result: Any) -> Any:
    return parse_value(result)


def add_source_url_to_script(source: str, path: Union[str, Path]) -> str:
    return source + "\n//# sourceURL=" + str(path).replace("\n", "")
