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
import re

#  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions#escaping
escaped_chars = {"$", "^", "+", ".", "*", "(", ")", "|", "\\", "?", "{", "}", "[", "]"}


def glob_to_regex(glob: str) -> "re.Pattern[str]":
    tokens = ["^"]
    in_group = False

    i = 0
    while i < len(glob):
        c = glob[i]
        if c == "\\" and i + 1 < len(glob):
            char = glob[i + 1]
            tokens.append("\\" + char if char in escaped_chars else char)
            i += 1
        elif c == "*":
            before_deep = glob[i - 1] if i > 0 else None
            star_count = 1
            while i + 1 < len(glob) and glob[i + 1] == "*":
                star_count += 1
                i += 1
            after_deep = glob[i + 1] if i + 1 < len(glob) else None
            is_deep = (
                star_count > 1
                and (before_deep == "/" or before_deep is None)
                and (after_deep == "/" or after_deep is None)
            )
            if is_deep:
                tokens.append("((?:[^/]*(?:/|$))*)")
                i += 1
            else:
                tokens.append("([^/]*)")
        else:
            if c == "?":
                tokens.append(".")
            elif c == "[":
                tokens.append("[")
            elif c == "]":
                tokens.append("]")
            elif c == "{":
                in_group = True
                tokens.append("(")
            elif c == "}":
                in_group = False
                tokens.append(")")
            elif c == "," and in_group:
                tokens.append("|")
            else:
                tokens.append("\\" + c if c in escaped_chars else c)
        i += 1

    tokens.append("$")
    return re.compile("".join(tokens))
