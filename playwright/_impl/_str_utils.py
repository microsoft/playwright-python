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

import json
import re
from typing import Pattern


def escape_with_quotes(text: str, char: str = "'") -> str:
    stringified = json.dumps(text, ensure_ascii=False)
    escaped_text = stringified[1:-1].replace('\\"', '"')
    if char == "'":
        return char + escaped_text.replace("'", "\\'") + char
    if char == '"':
        return char + escaped_text.replace('"', '\\"') + char
    if char == "`":
        return char + escaped_text.replace("`", "\\`") + char
    raise ValueError("Invalid escape char")


def escape_regex_flags(pattern: Pattern) -> str:
    flags = ""
    if pattern.flags != 0:
        flags = ""
    if (pattern.flags & int(re.IGNORECASE)) != 0:
        flags += "i"
    if (pattern.flags & int(re.DOTALL)) != 0:
        flags += "s"
    if (pattern.flags & int(re.MULTILINE)) != 0:
        flags += "m"
    assert (
        pattern.flags
        & ~(int(re.MULTILINE) | int(re.IGNORECASE) | int(re.DOTALL) | int(re.UNICODE))
        == 0
    ), "Unexpected re.Pattern flag, only MULTILINE, IGNORECASE and DOTALL are supported."
    return flags
