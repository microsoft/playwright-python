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

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from playwright._impl._channel import Channel
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._serializers import (
    HandleOrValue,
    parse_serialized_value,
    serialize_value,
)

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
        result = await self._channel.getProperty(name=property_name)
        return from_channel(result["handle"])

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        result = await self._channel.getPropertyList()
        return {
            prop["name"]: from_channel(prop["value"]) for prop in result["properties"]
        }

    async def json_value(self) -> Any:
        return parse_result((await self._channel.jsonValue())["value"])

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        try:
            await self._channel.dispose()
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e


# This function takes care of converting all JSHandles to their channels,
# so that generic channel serializer converts them to guids.
def serialize_argument(arg: Serializable) -> "channels.SerializedArgument":
    handles: List[Channel] = []

    def push_handle(channel: Channel) -> int:
        handles.append(channel)
        return len(handles) - 1

    def handle_serializer(value: Any) -> HandleOrValue:
        if isinstance(value, JSHandle):
            return {"h": push_handle(value._channel)}
        return {"fallThrough": value}

    value = serialize_value(arg, handle_serializer)
    return {"value": value, "handles": handles}


def parse_result(value: "channels.SerializedValue") -> Any:
    return parse_serialized_value(value, None)
