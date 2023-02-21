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
from typing import Pattern, Union


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


def escape_for_regex(text: str) -> str:
    return re.sub(r"[.*+?^>${}()|[\]\\]", "\\$&", text)


def escape_for_text_selector(
    text: Union[str, Pattern[str]], exact: bool = None, case_sensitive: bool = None
) -> str:
    if isinstance(text, Pattern):
        return f"/{text.pattern}/{escape_regex_flags(text)}"
    return json.dumps(text) + ("s" if exact else "i")


def escape_for_attribute_selector(value: str, exact: bool = None) -> str:
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
