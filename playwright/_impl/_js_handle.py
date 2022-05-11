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

import math
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._map import Map

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._element_handle import ElementHandle


Serializable = Any


@dataclass
class VisitorInfo:
    visited: Map[Any, int] = Map()
    last_id: int = 0

    def visit(self, obj: Any) -> int:
        assert obj not in self.visited
        self.last_id += 1
        self.visited[obj] = self.last_id
        return self.last_id


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
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def get_property(self, propertyName: str) -> "JSHandle":
        return from_channel(
            await self._channel.send("getProperty", dict(name=propertyName))
        )

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        return {
            prop["name"]: from_channel(prop["value"])
            for prop in await self._channel.send("getPropertyList")
        }

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        await self._channel.send("dispose")

    async def json_value(self) -> Any:
        return parse_result(await self._channel.send("jsonValue"))


def serialize_value(
    value: Any, handles: List[JSHandle], visitor_info: VisitorInfo = VisitorInfo()
) -> Any:
    if isinstance(value, JSHandle):
        h = len(handles)
        handles.append(value._channel)
        return dict(h=h)
    if value is None:
        return dict(v="null")
    if isinstance(value, float):
        if value == float("inf"):
            return dict(v="Infinity")
        if value == float("-inf"):
            return dict(v="-Infinity")
        if value == float("-0"):
            return dict(v="-0")
        if math.isnan(value):
            return dict(v="NaN")
    if isinstance(value, datetime):
        return dict(d=value.isoformat() + "Z")
    if isinstance(value, bool):
        return {"b": value}
    if isinstance(value, (int, float)):
        return {"n": value}
    if isinstance(value, str):
        return {"s": value}

    if value in visitor_info.visited:
        return dict(ref=visitor_info.visited[value])

    if isinstance(value, list):
        id = visitor_info.visit(value)
        a = []
        for e in value:
            a.append(serialize_value(e, handles, visitor_info))
        return dict(a=a, id=id)

    if isinstance(value, dict):
        id = visitor_info.visit(value)
        o = []
        for name in value:
            o.append(
                {"k": name, "v": serialize_value(value[name], handles, visitor_info)}
            )
        return dict(o=o, id=id)
    return dict(v="undefined")


def serialize_argument(arg: Serializable = None) -> Any:
    handles: List[JSHandle] = []
    value = serialize_value(arg, handles)
    return dict(value=value, handles=handles)


def parse_value(value: Any, refs: Dict[int, Any] = {}) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        if "ref" in value:
            return refs[value["ref"]]

        if "v" in value:
            v = value["v"]
            if v == "Infinity":
                return float("inf")
            if v == "-Infinity":
                return float("-inf")
            if v == "-0":
                return float("-0")
            if v == "NaN":
                return float("nan")
            if v == "undefined":
                return None
            if v == "null":
                return None
            return v

        if "a" in value:
            a: List = []
            refs[value["id"]] = a
            for e in value["a"]:
                a.append(parse_value(e, refs))
            return a

        if "d" in value:
            return datetime.fromisoformat(value["d"][:-1])

        if "o" in value:
            o: Dict = {}
            refs[value["id"]] = o
            for e in value["o"]:
                o[e["k"]] = parse_value(e["v"], refs)
            return o

        if "n" in value:
            return value["n"]

        if "s" in value:
            return value["s"]

        if "b" in value:
            return value["b"]
    return value


def parse_result(result: Any) -> Any:
    return parse_value(result)
