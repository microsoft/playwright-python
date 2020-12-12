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
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from playwright._connection import ChannelOwner, from_channel
from playwright._helper import is_function_body
from playwright._types import Error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._element_handle import ElementHandle


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

    def __str__(self) -> str:
        return self._preview

    def _on_preview_updated(self, preview: str) -> None:
        self._preview = preview

    async def evaluate(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
    ) -> Any:
        if not is_function_body(expression):
            force_expr = True
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: Serializable = None, force_expr: bool = None
    ) -> "JSHandle":
        if not is_function_body(expression):
            force_expr = True
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def getProperty(self, propertyName: str) -> "JSHandle":
        return from_channel(
            await self._channel.send("getProperty", dict(name=propertyName))
        )

    async def getProperties(self) -> Dict[str, "JSHandle"]:
        return {
            prop["name"]: from_channel(prop["value"])
            for prop in await self._channel.send("getPropertyList")
        }

    def asElement(self) -> Optional["ElementHandle"]:
        return None

    async def dispose(self) -> None:
        await self._channel.send("dispose")

    async def jsonValue(self) -> Any:
        return parse_result(await self._channel.send("jsonValue"))


def serialize_value(value: Any, handles: List[JSHandle], depth: int) -> Any:
    if isinstance(value, JSHandle):
        h = len(handles)
        handles.append(value._channel)
        return dict(h=h)
    if depth > 100:
        raise Error("Maximum argument depth exceeded")
    if value is None:
        return dict(v="undefined")
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

    if isinstance(value, list):
        result = list(map(lambda a: serialize_value(a, handles, depth + 1), value))
        return dict(a=result)

    if isinstance(value, dict):
        result = []  # type: ignore
        for name in value:
            result.append(
                {"k": name, "v": serialize_value(value[name], handles, depth + 1)}
            )
        return dict(o=result)
    return dict(v="undefined")


def serialize_argument(arg: Serializable = None) -> Any:
    handles: List[JSHandle] = []
    value = serialize_value(arg, handles, 0)
    return dict(value=value, handles=handles)


def parse_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
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
            return list(map(lambda e: parse_value(e), value["a"]))

        if "d" in value:
            return datetime.fromisoformat(value["d"][:-1])

        if "o" in value:
            o = value["o"]
            return {e["k"]: parse_value(e["v"]) for e in o}

        if "n" in value:
            return value["n"]

        if "s" in value:
            return value["s"]

        if "b" in value:
            return value["b"]
    return value


def parse_result(result: Any) -> Any:
    return parse_value(result)
