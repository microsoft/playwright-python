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
from typing import Callable, Dict, Optional, Pattern, Tuple, Union
from urllib.parse import ParseResult, urljoin, urlparse, urlunparse

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
                in_group = True
                tokens.append("(")
            elif c == "}":
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

    tokens.append("$")
    return "".join(tokens)


def url_matches(
    base_url: Optional[str],
    url_string: str,
    match: Optional[URLMatch],
    websocket_url: bool = None,
) -> bool:
    if not match:
        return True
    if isinstance(match, str):
        match = re.compile(
            resolve_glob_to_regex_pattern(base_url, match, websocket_url)
        )
    if isinstance(match, Pattern):
        return bool(match.search(url_string))
    return match(url_string)


def resolve_glob_to_regex_pattern(
    base_url: Optional[str], glob: str, websocket_url: bool = None
) -> str:
    if websocket_url:
        base_url = to_websocket_base_url(base_url)
    glob = resolve_glob_base(base_url, glob)
    return glob_to_regex_pattern(glob)


def to_websocket_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url is not None and re.match(r"^https?://", base_url):
        base_url = re.sub(r"^http", "ws", base_url)
    return base_url


def resolve_glob_base(base_url: Optional[str], match: str) -> str:
    if match[0] == "*":
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
        # about: and data: URLs are not relative to base_url, so we return them as is.
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
        normalize = case_insensitive_part and token in case_insensitive_part
        resolved = resolved.replace(
            token, original.lower() if normalize else original, 1
        )

    return resolved


def resolve_base_url(
    base_url: Optional[str], given_url: str
) -> Tuple[str, Optional[str]]:
    try:
        url = nodelike_urlparse(
            urljoin(base_url if base_url is not None else "", given_url)
        )
        resolved = urlunparse(url)
        # Schema and domain are case-insensitive.
        hostname_port = (
            url.hostname or ""
        )  # can't use parsed.netloc because it includes userinfo (username:password)
        if url.port:
            hostname_port += f":{url.port}"
        case_insensitive_prefix = f"{url.scheme}://{hostname_port}"
        return resolved, case_insensitive_prefix
    except Exception:
        return given_url, None


def nodelike_urlparse(url: str) -> ParseResult:
    parsed = urlparse(url, allow_fragments=True)

    # https://url.spec.whatwg.org/#special-scheme
    is_special_url = parsed.scheme in ["http", "https", "ws", "wss", "ftp", "file"]
    if is_special_url:
        # special urls have a list path, list paths are serialized as follows: https://url.spec.whatwg.org/#url-path-serializer
        # urllib diverges, so we patch it here
        if parsed.path == "":
            parsed = parsed._replace(path="/")

    return parsed
