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

from playwright._impl._connection import Channel, ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._serializers import parse_value, serialize_value

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._element_handle import ElementHandle


Serializable = Any


class JSHandle(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._preview = self._initializer["preview"]
        self._channel.on(
            "previewUpdated", lambda params: self._on_preview_updated(params["preview"])
        )

    def __repr__(self) -> str:
        return f"<JSHandle preview={self._preview}>"

    def __str__(self) -> str:
        return self._preview

    def _on_preview_updated(self, preview: str) -> None:
        self._preview = preview

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                None,
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> "JSHandle":
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                None,
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def get_property(self, propertyName: str) -> "JSHandle":
        return from_channel(
            await self._channel.send("getProperty", None, dict(name=propertyName))
        )

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        return {
            prop["name"]: from_channel(prop["value"])
            for prop in await self._channel.send(
                "getPropertyList",
                None,
            )
        }

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        try:
            await self._channel.send(
                "dispose",
                None,
            )
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    async def json_value(self) -> Any:
        return parse_result(
            await self._channel.send(
                "jsonValue",
                None,
            )
        )


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
