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

"""Port of packages/protocol/src/serializers.ts.

Converts values to and from the protocol's SerializedValue. It has no asyncio,
greenlet or I/O, so every implementation of the API can use it.

systemErrorCode() and systemErrorMessage() are not ported: they read the fields
of Node.js system errors.
"""

import base64
import collections.abc
import datetime
import math
import re
import struct
import traceback
from typing import Any, Callable, Dict, List, Optional, Pattern, Union
from urllib.parse import ParseResult, urlparse, urlunparse

from playwright._impl._errors import Error
from playwright._impl._map import Map
from playwright._impl._str_utils import (
    escape_regex_flags,
    js_string,
    parse_regex_flags,
)


def parse_serialized_value(value: Any, handles: Optional[List[Any]]) -> Any:
    return _inner_parse_serialized_value(value, handles, {}, [])


def _inner_parse_serialized_value(
    value: Any,
    handles: Optional[List[Any]],
    refs: Dict[int, Any],
    access_chain: List[Union[str, int]],
) -> Any:
    if "ref" in value:
        return refs.get(value["ref"])
    if "n" in value:
        return value["n"]
    if "s" in value:
        return value["s"]
    if "b" in value:
        return value["b"]
    if "v" in value:
        # Python has no undefined: it is None, as null is.
        if value["v"] == "undefined":
            return None
        if value["v"] == "null":
            return None
        if value["v"] == "NaN":
            return math.nan
        if value["v"] == "Infinity":
            return math.inf
        if value["v"] == "-Infinity":
            return -math.inf
        if value["v"] == "-0":
            return -0.0
    if "d" in value:
        if value["d"] is None:
            # An invalid Date serializes as null, and new Date(null) is the epoch.
            return datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
        # Node.js Date objects are always in UTC.
        return datetime.datetime.strptime(value["d"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=datetime.timezone.utc
        )
    if "u" in value:
        return urlparse(value["u"])
    if "bi" in value:
        return int(value["bi"])
    if "e" in value:
        error = Error(value["e"]["m"])
        error._name = value["e"]["n"]
        error._stack = value["e"]["s"]
        return error
    if "r" in value:
        try:
            return re.compile(value["r"]["p"], parse_regex_flags(value["r"]["f"]))
        except re.error:
            # JavaScript-only syntax, e.g. /(?<name>x)/, has no re equivalent.
            return value
    if "ta" in value:
        # Python has no typed arrays: a typed array is a list of its items.
        item_format = "<" + _typed_array_kind_to_format[value["ta"]["k"]]
        return [
            item
            for (item,) in struct.iter_unpack(
                item_format, base64.b64decode(value["ta"]["b"])
            )
        ]

    if "a" in value:
        a: List[Any] = []
        refs[value["id"]] = a
        for i, item in enumerate(value["a"]):
            a.append(
                _inner_parse_serialized_value(item, handles, refs, [*access_chain, i])
            )
        return a
    if "o" in value:
        o: Dict[str, Any] = {}
        refs[value["id"]] = o
        for entry in value["o"]:
            o[entry["k"]] = _inner_parse_serialized_value(
                entry["v"], handles, refs, [*access_chain, entry["k"]]
            )
        return o
    if "h" in value:
        if handles is None:
            raise Error("Unexpected handle")
        return handles[value["h"]]
    if "fn" in value:

        def dummy() -> None:
            pass

        dummy.__name__ = value["fn"]
        return dummy
    raise Error(
        f"Attempting to deserialize unexpected value{_access_chain_to_display_string(access_chain)}: {value}"
    )


# What a handle serializer returns: {"h": index} or {"fn": name} for a value
# that it serializes, {"fallThrough": value} for a value that it does not.
HandleOrValue = Dict[str, Any]


class VisitorInfo:
    def __init__(self) -> None:
        self.visited: Map[Any, int] = Map()
        self.last_id = 0


def serialize_value(
    value: Any, handle_serializer: Callable[[Any], HandleOrValue]
) -> Any:
    return _inner_serialize_value(value, handle_serializer, VisitorInfo(), [])


def _inner_serialize_value(
    value: Any,
    handle_serializer: Callable[[Any], HandleOrValue],
    visitor_info: VisitorInfo,
    access_chain: List[Union[str, int]],
) -> Any:
    handle = handle_serializer(value)
    if "fallThrough" in handle:
        value = handle["fallThrough"]
    else:
        return handle

    # Python has no undefined and no symbols: None is null.
    if value is None:
        return {"v": "null"}
    if isinstance(value, float):
        if math.isnan(value):
            return {"v": "NaN"}
        if value == math.inf:
            return {"v": "Infinity"}
        if value == -math.inf:
            return {"v": "-Infinity"}
        if value == 0 and math.copysign(1.0, value) == -1.0:
            return {"v": "-0"}
    if isinstance(value, bool):
        return {"b": value}
    # A Python int is a number, not a BigInt.
    if isinstance(value, (int, float)):
        return {"n": value}
    if isinstance(value, str):
        return {"s": value}
    if isinstance(value, Exception):
        # Only an Error of this module has a name and a stack: other exceptions
        # use the class name and the traceback.
        name = value.name if isinstance(value, Error) else None
        stack = value.stack if isinstance(value, Error) else None
        return {
            "e": {
                "n": name or value.__class__.__name__,
                "m": str(value),
                "s": stack
                or "".join(
                    traceback.format_exception(
                        type(value), value=value, tb=value.__traceback__
                    )
                ),
            }
        }
    if isinstance(value, datetime.datetime):
        # Node.js Date objects are always in UTC.
        return {
            "d": datetime.datetime.strftime(
                value.astimezone(datetime.timezone.utc), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        }
    if isinstance(value, ParseResult):
        return {"u": urlunparse(value)}
    if isinstance(value, Pattern):
        if not isinstance(value.pattern, str):
            raise Error("Only str patterns are supported.")
        return {"r": {"p": value.pattern, "f": escape_regex_flags(value)}}
    if isinstance(value, (bytes, bytearray, memoryview)):
        # The typed array that bytes correspond to is a Uint8Array.
        return {"ta": {"b": base64.b64encode(bytes(value)).decode(), "k": "ui8"}}

    if value in visitor_info.visited:
        return {"ref": visitor_info.visited[value]}

    if isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
        a = []
        visitor_info.last_id += 1
        id = visitor_info.last_id
        visitor_info.visited[value] = id
        for i, item in enumerate(value):
            a.append(
                _inner_serialize_value(
                    item, handle_serializer, visitor_info, [*access_chain, i]
                )
            )
        return {"a": a, "id": id}
    if isinstance(value, dict):
        o = []
        visitor_info.last_id += 1
        id = visitor_info.last_id
        visitor_info.visited[value] = id
        for name in value:
            o.append(
                {
                    # Object keys are strings in JavaScript.
                    "k": name if isinstance(name, str) else js_string(name),
                    "v": _inner_serialize_value(
                        value[name],
                        handle_serializer,
                        visitor_info,
                        [*access_chain, name],
                    ),
                }
            )
        return {"o": o, "id": id}
    # Functions, and other values that have no protocol form, reach here.
    raise Error(
        f"Attempting to serialize unexpected value{_access_chain_to_display_string(access_chain)}: {value}"
    )


def _access_chain_to_display_string(access_chain: List[Union[str, int]]) -> str:
    chain_string = "".join(
        (
            (f".{accessor}" if i else accessor)
            if isinstance(accessor, str)
            else f"[{accessor}]"
        )
        for i, accessor in enumerate(access_chain)
    )
    return f' at position "{chain_string}"' if chain_string else ""


# typedArrayKindToConstructor in serializers.ts, as the struct format of an item.
_typed_array_kind_to_format: Dict[str, str] = {
    "i8": "b",
    "ui8": "B",
    "ui8c": "B",
    "i16": "h",
    "ui16": "H",
    "i32": "i",
    "ui32": "I",
    "f32": "f",
    "f64": "d",
    "bi64": "q",
    "bui64": "Q",
}
