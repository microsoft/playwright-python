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
from playwright._impl._str_utils import escape_regex_flags, parse_regex_flags

# Returns the serialized form of a handle, for example {"h": 0}, or None if the
# value is not a handle. Upstream passes the same callback to serializeValue().
HandleSerializer = Callable[[Any], Optional[Dict[str, Any]]]


class VisitorInfo:
    visited: Map[Any, int]
    last_id: int

    def __init__(self) -> None:
        self.visited = Map()
        self.last_id = 0

    def visit(self, obj: Any) -> int:
        assert obj not in self.visited
        self.last_id += 1
        self.visited[obj] = self.last_id
        return self.last_id


def serialize_value(value: Any, handle_serializer: HandleSerializer) -> Any:
    return _inner_serialize_value(value, handle_serializer, VisitorInfo(), [])


def _inner_serialize_value(
    value: Any,
    handle_serializer: HandleSerializer,
    visitor_info: VisitorInfo,
    access_chain: List[Union[str, int]],
) -> Any:
    handle = handle_serializer(value)
    if handle is not None:
        return handle
    if value is None:
        return dict(v="null")
    if isinstance(value, float):
        if value == float("inf"):
            return dict(v="Infinity")
        if value == float("-inf"):
            return dict(v="-Infinity")
        if value == 0 and math.copysign(1.0, value) == -1.0:
            return dict(v="-0")
        if math.isnan(value):
            return dict(v="NaN")
    if isinstance(value, datetime.datetime):
        # Node.js Date objects are always in UTC.
        return {
            "d": datetime.datetime.strftime(
                value.astimezone(datetime.timezone.utc), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        }
    if isinstance(value, Exception):
        return {
            "e": {
                "m": str(value),
                "n": (
                    (value.name or "")
                    if isinstance(value, Error)
                    else value.__class__.__name__
                ),
                "s": (
                    (value.stack or "")
                    if isinstance(value, Error)
                    else "".join(
                        traceback.format_exception(
                            type(value), value=value, tb=value.__traceback__
                        )
                    )
                ),
            }
        }
    if isinstance(value, bool):
        return {"b": value}
    if isinstance(value, (int, float)):
        return {"n": value}
    if isinstance(value, str):
        return {"s": value}
    if isinstance(value, ParseResult):
        return {"u": urlunparse(value)}
    if isinstance(value, Pattern):
        if not isinstance(value.pattern, str):
            raise Error("Only str patterns are supported.")
        return {"r": {"p": value.pattern, "f": escape_regex_flags(value)}}

    if value in visitor_info.visited:
        return dict(ref=visitor_info.visited[value])

    if isinstance(value, collections.abc.Sequence) and not isinstance(value, str):
        id = visitor_info.visit(value)
        a = []
        for i, e in enumerate(value):
            a.append(
                _inner_serialize_value(
                    e, handle_serializer, visitor_info, [*access_chain, i]
                )
            )
        return dict(a=a, id=id)

    if isinstance(value, dict):
        id = visitor_info.visit(value)
        o = []
        for name in value:
            o.append(
                {
                    "k": name,
                    "v": _inner_serialize_value(
                        value[name],
                        handle_serializer,
                        visitor_info,
                        [*access_chain, name],
                    ),
                }
            )
        return dict(o=o, id=id)
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


def parse_value(value: Any, refs: Optional[Dict[int, Any]] = None) -> Any:
    if refs is None:
        refs = {}
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

        if "a" in value:
            a: List = []
            refs[value["id"]] = a
            for e in value["a"]:
                a.append(parse_value(e, refs))
            return a

        if "d" in value:
            # Node.js Date objects are always in UTC.
            return datetime.datetime.strptime(
                value["d"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=datetime.timezone.utc)

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

        if "ta" in value:
            encoded_bytes = value["ta"]["b"]
            decoded_bytes = base64.b64decode(encoded_bytes)
            array_type = value["ta"]["k"]
            if array_type == "i8":
                word_size = 1
                fmt = "b"
            elif array_type == "ui8" or array_type == "ui8c":
                word_size = 1
                fmt = "B"
            elif array_type == "i16":
                word_size = 2
                fmt = "h"
            elif array_type == "ui16":
                word_size = 2
                fmt = "H"
            elif array_type == "i32":
                word_size = 4
                fmt = "i"
            elif array_type == "ui32":
                word_size = 4
                fmt = "I"
            elif array_type == "f32":
                word_size = 4
                fmt = "f"
            elif array_type == "f64":
                word_size = 8
                fmt = "d"
            elif array_type == "bi64":
                word_size = 8
                fmt = "q"
            elif array_type == "bui64":
                word_size = 8
                fmt = "Q"
            else:
                raise ValueError(f"Unsupported array type: {array_type}")

            byte_len = len(decoded_bytes)
            if byte_len % word_size != 0:
                raise ValueError(
                    f"Decoded bytes length {byte_len} is not a multiple of word size {word_size}"
                )

            if byte_len == 0:
                return []
            array_len = byte_len // word_size
            # "<" denotes little-endian
            format_string = f"<{array_len}{fmt}"
            return list(struct.unpack(format_string, decoded_bytes))
    return value
