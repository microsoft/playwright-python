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

"""Port of packages/isomorphic/urlMatch.ts.

Glob and URL matching. It has no asyncio, greenlet or I/O, so every
implementation of the API can use it.
"""

import json
import re
from typing import TYPE_CHECKING, Callable, Dict, Optional, Pattern, Tuple, Union

from playwright._impl._errors import Error
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._whatwg_url import parse_url

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels

URLMatch = Union[str, Pattern[str], Callable[[str], bool]]

#  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions#escaping
escaped_chars = {"$", "^", "+", ".", "*", "(", ")", "|", "\\", "?", "{", "}", "[", "]"}


def glob_to_regex_pattern(glob: str) -> str:
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
            char_before = glob[i - 1] if i > 0 else None
            star_count = 1
            while i + 1 < len(glob) and glob[i + 1] == "*":
                star_count += 1
                i += 1
            if star_count > 1:
                char_after = glob[i + 1] if i + 1 < len(glob) else None
                # Match either /..something../ or /.
                if char_after == "/":
                    if char_before == "/":
                        tokens.append("((.+/)|)")
                    else:
                        tokens.append("(.*/)")
                    i += 1
                else:
                    tokens.append("(.*)")
            else:
                tokens.append("([^/]*)")
        else:
            if c == "{":
                if in_group:
                    raise Error(
                        f"Invalid glob pattern {_json_stringify(glob)}: nested '{{' is not supported"
                    )
                in_group = True
                tokens.append("(")
            elif c == "}":
                if not in_group:
                    raise Error(
                        f"Invalid glob pattern {_json_stringify(glob)}: unmatched '}}'"
                    )
                in_group = False
                tokens.append(")")
            elif c == ",":
                if in_group:
                    tokens.append("|")
                else:
                    tokens.append("\\" + c)
            else:
                tokens.append("\\" + c if c in escaped_chars else c)
        i += 1

    if in_group:
        raise Error(f"Invalid glob pattern {_json_stringify(glob)}: unmatched '{{'")
    tokens.append("$")
    return "".join(tokens)


def _json_stringify(value: str) -> str:
    # JSON.stringify() of a string.
    return json.dumps(value, ensure_ascii=False)


def url_matches(
    base_url: Optional[str],
    url_string: str,
    match: Optional[URLMatch],
    websocket_url: bool = None,
) -> bool:
    if match is None or match == "":
        return True
    if isinstance(match, str):
        match = re.compile(
            resolve_glob_to_regex_pattern(base_url, match, websocket_url)
        )
    if isinstance(match, Pattern):
        return bool(match.search(url_string))
    if parse_url(url_string) is None:
        return False
    if not callable(match):
        raise Error("url parameter should be string, RegExp or function")
    return match(url_string)


def resolve_glob_to_regex_pattern(
    base_url: Optional[str], glob: str, websocket_url: bool = None
) -> str:
    if websocket_url:
        base_url = to_websocket_base_url(base_url)
    glob = resolve_glob_base(base_url, glob)
    return glob_to_regex_pattern(glob)


def to_websocket_base_url(base_url: Optional[str]) -> Optional[str]:
    # Allow http(s) base_url to match ws(s) urls. Schemes are case-insensitive,
    # same as elsewhere in this file, so 'HTTP://...' should be rewritten too.
    if base_url and re.match(r"^https?://", base_url, re.IGNORECASE):
        base_url = re.sub(
            r"^https?",
            lambda m: "wss" if m.group(0).lower() == "https" else "ws",
            base_url,
            count=1,
            flags=re.IGNORECASE,
        )
    return base_url


def resolve_glob_base(base_url: Optional[str], match: str) -> str:
    if match.startswith("*"):
        return match

    token_map: Dict[str, str] = {}

    def map_token(original: str, replacement: str) -> str:
        if len(original) == 0:
            return ""
        token_map[replacement] = original
        return replacement

    # Escaped `\\?` behaves the same as `?` in our glob patterns.
    match = match.replace(r"\\?", "?")
    # Special case about: URLs as they are not relative to base_url
    if (
        match.startswith("about:")
        or match.startswith("data:")
        or match.startswith("chrome:")
        or match.startswith("edge:")
        or match.startswith("file:")
    ):
        return match
    # Glob symbols may be escaped in the URL and some of them such as ? affect resolution,
    # so we replace them with safe components first.
    processed_parts = []
    for index, token in enumerate(match.split("/")):
        if token in (".", "..", ""):
            processed_parts.append(token)
            continue
        # Handle special case of http*://, note that the new schema has to be
        # a web schema so that slashes are properly inserted after domain.
        if index == 0 and token.endswith(":"):
            # Replace any pattern with http:
            if "*" in token or "{" in token:
                processed_parts.append(map_token(token, "http:"))
            else:
                # Preserve explicit schema as is as it may affect trailing slashes after domain.
                processed_parts.append(token)
            continue
        # Components without glob metacharacters are literal, so let them round-trip
        # through the URL parser to preserve normalization (default ports such as :80/:443,
        # percent-encoding, IDN hosts). Only opaque tokens defeat that normalization.
        if not re.search(r"[*?{}\\]", token):
            processed_parts.append(token)
            continue
        question_index = token.find("?")
        if question_index == -1:
            processed_parts.append(map_token(token, f"$_{index}_$"))
        else:
            new_prefix = map_token(token[:question_index], f"$_{index}_$")
            new_suffix = map_token(token[question_index:], f"?$_{index}_$")
            processed_parts.append(new_prefix + new_suffix)

    relative_path = "/".join(processed_parts)
    resolved, case_insensitive_part = resolve_base_url(base_url, relative_path)

    for token, original in token_map.items():
        normalize = case_insensitive_part is not None and token in case_insensitive_part
        resolved = resolved.replace(
            token, original.lower() if normalize else original, 1
        )

    return resolved


def resolve_base_url(
    base_url: Optional[str], given_url: str
) -> Tuple[str, Optional[str]]:
    # new URL(givenURL, baseURL); None where it throws.
    url = parse_url(given_url, base_url)
    if url is None:
        return given_url, None
    # Schema and domain are case-insensitive.
    return url.href, url.origin


def url_matches_equal(match1: URLMatch, match2: URLMatch) -> bool:
    if isinstance(match1, Pattern) and isinstance(match2, Pattern):
        return match1.pattern == match2.pattern and match1.flags == match2.flags
    return match1 == match2


def serialize_url_match(
    match: URLMatch,
) -> Optional["channels.BrowserContextSetNetworkInterceptionPatternsParamsPatterns"]:
    if isinstance(match, str):
        return {"glob": match}
    if isinstance(match, Pattern):
        return {"regexSource": match.pattern, "regexFlags": escape_regex_flags(match)}
    # Functions cannot be serialized
    return None
