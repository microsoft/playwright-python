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

"""Port of packages/isomorphic/stringUtils.ts."""

import json
import math
import re
from typing import Any, Pattern, Union

from playwright._impl_v2.errors import Error


def escape_regex_flags(pattern: Pattern) -> str:
    flags = ""
    if (pattern.flags & int(re.IGNORECASE)) != 0:
        flags += "i"
    if (pattern.flags & int(re.DOTALL)) != 0:
        flags += "s"
    if (pattern.flags & int(re.MULTILINE)) != 0:
        flags += "m"
    if (
        pattern.flags
        & ~(int(re.MULTILINE) | int(re.IGNORECASE) | int(re.DOTALL) | int(re.UNICODE))
        != 0
    ):
        raise Error(
            "Unexpected re.Pattern flag, only MULTILINE, IGNORECASE and DOTALL are supported."
        )
    return flags


def parse_regex_flags(flags: str) -> int:
    result = 0
    if "i" in flags:
        result |= re.IGNORECASE
    if "s" in flags:
        result |= re.DOTALL
    if "m" in flags:
        result |= re.MULTILINE
    # The remaining JavaScript flags (d, g, u, v, y) have no re equivalent.
    return result


def escape_regex_for_selector(text: Pattern) -> str:
    # Even number of backslashes followed by the quote -> insert a backslash.
    return (
        "/"
        + re.sub(r'(^|[^\\])(\\\\)*(["\'`])', r"\1\2\\\3", text.pattern).replace(
            ">>", "\\>\\>"
        )
        + "/"
        + escape_regex_flags(text)
    )


def escape_for_text_selector(text: Union[str, Pattern[str]], exact: bool) -> str:
    if isinstance(text, Pattern):
        return escape_regex_for_selector(text)
    # JSON.stringify() does not escape non-ASCII characters.
    return json.dumps(text, ensure_ascii=False) + ("s" if exact else "i")


def escape_for_attribute_selector(value: Union[str, Pattern], exact: bool) -> str:
    if isinstance(value, Pattern):
        return escape_regex_for_selector(value)
    # TODO: this should actually be
    #   cssEscape(value).replace(/\\ /g, ' ')
    # However, our attribute selectors do not conform to CSS parsing spec,
    # so we escape them differently.
    return (
        '"'
        + value.replace("\\", "\\\\").replace('"', '\\"')
        + '"'
        + ("s" if exact else "i")
    )


# Port of trimString() in packages/isomorphic/stringUtils.ts.
def trim_string(input: str, cap: int, suffix: str = "") -> str:
    if len(input) <= cap:
        return input
    return input[: cap - len(suffix)] + suffix


# Port of trimStringWithEllipsis() in packages/isomorphic/stringUtils.ts.
def trim_string_with_ellipsis(input: str, cap: int) -> str:
    return trim_string(input, cap, "…")


def js_string(value: Any) -> str:
    """String(value) in JavaScript, for the values that the API takes."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value.is_integer() and abs(value) < 1e21:
            return str(int(value))
    return str(value)


# toSnakeCase() in packages/isomorphic/stringUtils.ts.
to_snake_case_regex = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_snake_case(name: str) -> str:
    return to_snake_case_regex.sub(r"_\1", name).lower()
