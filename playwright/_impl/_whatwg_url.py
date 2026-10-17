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

"""The URL parser of the WHATWG URL Standard: what `new URL(input, base)` does
in Node.js, which the upstream client (packages/isomorphic/urlMatch.ts) uses.

https://url.spec.whatwg.org/#concept-basic-url-parser

urllib does not normalize URLs this way (default ports, percent-encoding, IDN
hosts, dot segments, backslashes). Only the parts that `href` and `origin`
need are here; there are no setters (no state override).
"""

import encodings.idna
import ipaddress
import re
from typing import List, Optional, Union

_SPECIAL_SCHEMES = {
    "ftp": 21,
    "file": None,
    "http": 80,
    "https": 443,
    "ws": 80,
    "wss": 443,
}

_ASCII_ALPHA = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
_ASCII_DIGITS = frozenset("0123456789")
_ASCII_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_ASCII_ALPHANUMERIC = _ASCII_ALPHA | _ASCII_DIGITS

# https://url.spec.whatwg.org/#percent-encoded-bytes
_C0_CONTROL_SET = frozenset(chr(c) for c in range(0x20))
_FRAGMENT_SET = _C0_CONTROL_SET | frozenset(' "<>`')
_QUERY_SET = _C0_CONTROL_SET | frozenset(' "#<>')
_SPECIAL_QUERY_SET = _QUERY_SET | frozenset("'")
_PATH_SET = _QUERY_SET | frozenset("?^`{}")
_USERINFO_SET = _PATH_SET | frozenset("/:;=@[\\]|")

# https://url.spec.whatwg.org/#forbidden-host-code-point
_FORBIDDEN_HOST_CODE_POINTS = frozenset("\x00\t\n\r #/:<>?@[\\]^|")
_FORBIDDEN_DOMAIN_CODE_POINTS = (
    _FORBIDDEN_HOST_CODE_POINTS | _C0_CONTROL_SET | frozenset("%\x7f")
)

# U+002E, U+3002, U+FF0E and U+FF61 separate the labels of a domain.
_LABEL_SEPARATORS = re.compile(
    "[" + "".join(map(chr, (0x2E, 0x3002, 0xFF0E, 0xFF61))) + "]"
)
# Sharp s and final sigma: IDNA 2003 maps them, UTS #46 keeps them.
_DEVIATION_CHARACTERS = re.compile("(" + "|".join(map(chr, (0xDF, 0x3C2))) + ")")


class URL:
    def __init__(self) -> None:
        self.scheme = ""
        self.username = ""
        self.password = ""
        # The serialized host; None is the null host.
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        # A list of segments, or a string for an opaque path.
        self.path: Union[str, List[str]] = []
        self.query: Optional[str] = None
        self.fragment: Optional[str] = None

    @property
    def is_special(self) -> bool:
        return self.scheme in _SPECIAL_SCHEMES

    @property
    def has_opaque_path(self) -> bool:
        return isinstance(self.path, str)

    @property
    def href(self) -> str:
        # https://url.spec.whatwg.org/#concept-url-serializer
        output = self.scheme + ":"
        if self.host is not None:
            output += "//"
            if self.username or self.password:
                output += self.username
                if self.password:
                    output += ":" + self.password
                output += "@"
            output += self.host
            if self.port is not None:
                output += ":" + str(self.port)
        if isinstance(self.path, str):
            output += self.path
        else:
            if self.host is None and len(self.path) > 1 and self.path[0] == "":
                output += "/."
            for segment in self.path:
                output += "/" + segment
        if self.query is not None:
            output += "?" + self.query
        if self.fragment is not None:
            output += "#" + self.fragment
        return output

    @property
    def origin(self) -> str:
        # https://url.spec.whatwg.org/#concept-url-origin
        if self.scheme == "blob":
            path_url = parse_url(self.path) if isinstance(self.path, str) else None
            if path_url and path_url.scheme in ("http", "https"):
                return path_url.origin
            return "null"
        if self.scheme in ("ftp", "http", "https", "ws", "wss"):
            result = self.scheme + "://" + (self.host or "")
            if self.port is not None:
                result += ":" + str(self.port)
            return result
        return "null"

    def _shorten_path(self) -> None:
        # https://url.spec.whatwg.org/#shorten-a-urls-path
        assert isinstance(self.path, list)
        if (
            self.scheme == "file"
            and len(self.path) == 1
            and _is_normalized_windows_drive_letter(self.path[0])
        ):
            return
        if self.path:
            self.path.pop()


def parse_url(input: str, base: Optional[str] = None) -> Optional[URL]:
    """Returns None where `new URL(input, base)` throws."""
    base_url: Optional[URL] = None
    if base is not None:
        base_url = _basic_parse(base, None)
        if base_url is None:
            return None
    return _basic_parse(input, base_url)


def _is_windows_drive_letter(s: str) -> bool:
    return len(s) == 2 and s[0] in _ASCII_ALPHA and s[1] in (":", "|")


def _is_normalized_windows_drive_letter(s: str) -> bool:
    return len(s) == 2 and s[0] in _ASCII_ALPHA and s[1] == ":"


def _starts_with_windows_drive_letter(s: str) -> bool:
    return _is_windows_drive_letter(s[:2]) and (len(s) == 2 or s[2] in "/\\?#")


def _is_single_dot_segment(s: str) -> bool:
    return s == "." or s.lower() == "%2e"


def _is_double_dot_segment(s: str) -> bool:
    return s.lower() in ("..", ".%2e", "%2e.", "%2e%2e")


def _percent_encode(c: str, encode_set: frozenset) -> str:
    # https://url.spec.whatwg.org/#utf-8-percent-encode
    if c not in encode_set and c <= "\x7e":
        return c
    return "".join(f"%{b:02X}" for b in c.encode("utf-8"))


def _percent_encode_string(s: str, encode_set: frozenset) -> str:
    return "".join(_percent_encode(c, encode_set) for c in s)


def _percent_decode(s: str) -> bytes:
    # https://url.spec.whatwg.org/#percent-decode
    data = s.encode("utf-8")
    output = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        if (
            byte == 0x25
            and i + 2 < len(data)
            and chr(data[i + 1]) in _ASCII_HEX_DIGITS
            and chr(data[i + 2]) in _ASCII_HEX_DIGITS
        ):
            output.append(int(chr(data[i + 1]) + chr(data[i + 2]), 16))
            i += 3
            continue
        output.append(byte)
        i += 1
    return bytes(output)


def _basic_parse(input: str, base: Optional[URL]) -> Optional[URL]:
    # https://url.spec.whatwg.org/#concept-basic-url-parser
    # A lone surrogate is not a scalar value: it becomes U+FFFD.
    input = input.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    input = input.strip("".join(chr(c) for c in range(0x21)))
    input = input.replace("\t", "").replace("\n", "").replace("\r", "")

    url = URL()
    state = "scheme start"
    buffer = ""
    at_sign_seen = False
    inside_brackets = False
    password_token_seen = False
    pointer = 0
    length = len(input)

    while True:
        c = input[pointer] if pointer < length else ""  # "" is EOF

        if state == "scheme start":
            if c and c in _ASCII_ALPHA:
                buffer += c.lower()
                state = "scheme"
            else:
                state = "no scheme"
                pointer -= 1

        elif state == "scheme":
            if c and (c in _ASCII_ALPHANUMERIC or c in "+-."):
                buffer += c.lower()
            elif c == ":":
                url.scheme = buffer
                buffer = ""
                if url.scheme == "file":
                    state = "file"
                elif url.is_special and base is not None and base.scheme == url.scheme:
                    state = "special relative or authority"
                elif url.is_special:
                    state = "special authority slashes"
                elif input.startswith("/", pointer + 1):
                    state = "path or authority"
                    pointer += 1
                else:
                    url.path = ""
                    state = "opaque path"
            else:
                buffer = ""
                state = "no scheme"
                pointer = -1

        elif state == "no scheme":
            if base is None or (base.has_opaque_path and c != "#"):
                return None
            if base.has_opaque_path and c == "#":
                url.scheme = base.scheme
                url.path = base.path
                url.query = base.query
                url.fragment = ""
                state = "fragment"
            elif base.scheme != "file":
                state = "relative"
                pointer -= 1
            else:
                state = "file"
                pointer -= 1

        elif state == "special relative or authority":
            if c == "/" and input.startswith("/", pointer + 1):
                state = "special authority ignore slashes"
                pointer += 1
            else:
                state = "relative"
                pointer -= 1

        elif state == "path or authority":
            if c == "/":
                state = "authority"
            else:
                state = "path"
                pointer -= 1

        elif state == "relative":
            assert base is not None
            url.scheme = base.scheme
            if c == "/" or (url.is_special and c == "\\"):
                state = "relative slash"
            else:
                url.username = base.username
                url.password = base.password
                url.host = base.host
                url.port = base.port
                url.path = list(base.path)
                url.query = base.query
                if c == "?":
                    url.query = ""
                    state = "query"
                elif c == "#":
                    url.fragment = ""
                    state = "fragment"
                elif c:
                    url.query = None
                    url._shorten_path()
                    state = "path"
                    pointer -= 1

        elif state == "relative slash":
            assert base is not None
            if url.is_special and c in ("/", "\\") and c:
                state = "special authority ignore slashes"
            elif c == "/":
                state = "authority"
            else:
                url.username = base.username
                url.password = base.password
                url.host = base.host
                url.port = base.port
                state = "path"
                pointer -= 1

        elif state == "special authority slashes":
            if c == "/" and input.startswith("/", pointer + 1):
                state = "special authority ignore slashes"
                pointer += 1
            else:
                state = "special authority ignore slashes"
                pointer -= 1

        elif state == "special authority ignore slashes":
            if c not in ("/", "\\") or not c:
                state = "authority"
                pointer -= 1

        elif state == "authority":
            if c == "@":
                if at_sign_seen:
                    buffer = "%40" + buffer
                at_sign_seen = True
                for code_point in buffer:
                    if code_point == ":" and not password_token_seen:
                        password_token_seen = True
                        continue
                    encoded = _percent_encode(code_point, _USERINFO_SET)
                    if password_token_seen:
                        url.password += encoded
                    else:
                        url.username += encoded
                buffer = ""
            elif (not c or c in "/?#") or (url.is_special and c == "\\"):
                if at_sign_seen and buffer == "":
                    return None
                pointer -= len(buffer) + 1
                buffer = ""
                state = "host"
            else:
                buffer += c

        elif state == "host":
            if c == ":" and not inside_brackets:
                if buffer == "":
                    return None
                host = _parse_host(buffer, not url.is_special)
                if host is None:
                    return None
                url.host = host
                buffer = ""
                state = "port"
            elif (not c or c in "/?#") or (url.is_special and c == "\\"):
                pointer -= 1
                if url.is_special and buffer == "":
                    return None
                host = _parse_host(buffer, not url.is_special)
                if host is None:
                    return None
                url.host = host
                buffer = ""
                state = "path start"
            else:
                if c == "[":
                    inside_brackets = True
                if c == "]":
                    inside_brackets = False
                buffer += c

        elif state == "port":
            if c and c in _ASCII_DIGITS:
                buffer += c
            elif (not c or c in "/?#") or (url.is_special and c == "\\"):
                if buffer != "":
                    port = int(buffer)
                    if port > 65535:
                        return None
                    url.port = (
                        None if _SPECIAL_SCHEMES.get(url.scheme) == port else port
                    )
                    buffer = ""
                state = "path start"
                pointer -= 1
            else:
                return None

        elif state == "file":
            url.scheme = "file"
            url.host = ""
            if c and c in "/\\":
                state = "file slash"
            elif base is not None and base.scheme == "file":
                url.host = base.host
                url.path = list(base.path)
                url.query = base.query
                if c == "?":
                    url.query = ""
                    state = "query"
                elif c == "#":
                    url.fragment = ""
                    state = "fragment"
                elif c:
                    url.query = None
                    if not _starts_with_windows_drive_letter(input[pointer:]):
                        url._shorten_path()
                    else:
                        url.path = []
                    state = "path"
                    pointer -= 1
            else:
                state = "path"
                pointer -= 1

        elif state == "file slash":
            if c and c in "/\\":
                state = "file host"
            else:
                if base is not None and base.scheme == "file":
                    url.host = base.host
                    if (
                        not _starts_with_windows_drive_letter(input[pointer:])
                        and isinstance(base.path, list)
                        and base.path
                        and _is_normalized_windows_drive_letter(base.path[0])
                    ):
                        assert isinstance(url.path, list)
                        url.path.append(base.path[0])
                state = "path"
                pointer -= 1

        elif state == "file host":
            if not c or c in "/\\?#":
                pointer -= 1
                if _is_windows_drive_letter(buffer):
                    # The buffer is not reset here: the path state uses it.
                    state = "path"
                elif buffer == "":
                    url.host = ""
                    state = "path start"
                else:
                    host = _parse_host(buffer, not url.is_special)
                    if host is None:
                        return None
                    if host == "localhost":
                        host = ""
                    url.host = host
                    buffer = ""
                    state = "path start"
            else:
                buffer += c

        elif state == "path start":
            if url.is_special:
                state = "path"
                if not c or c not in "/\\":
                    pointer -= 1
            elif c == "?":
                url.query = ""
                state = "query"
            elif c == "#":
                url.fragment = ""
                state = "fragment"
            elif c:
                state = "path"
                if c != "/":
                    pointer -= 1

        elif state == "path":
            assert isinstance(url.path, list)
            slash = c == "/" or (url.is_special and c == "\\")
            if not c or slash or c in ("?", "#"):
                if _is_double_dot_segment(buffer):
                    url._shorten_path()
                    if not slash:
                        url.path.append("")
                elif _is_single_dot_segment(buffer) and not slash:
                    url.path.append("")
                elif not _is_single_dot_segment(buffer):
                    if (
                        url.scheme == "file"
                        and not url.path
                        and _is_windows_drive_letter(buffer)
                    ):
                        buffer = buffer[0] + ":"
                    url.path.append(buffer)
                buffer = ""
                if c == "?":
                    url.query = ""
                    state = "query"
                if c == "#":
                    url.fragment = ""
                    state = "fragment"
            else:
                buffer += _percent_encode(c, _PATH_SET)

        elif state == "opaque path":
            assert isinstance(url.path, str)
            if c == "?":
                url.query = ""
                state = "query"
            elif c == "#":
                url.fragment = ""
                state = "fragment"
            elif c == " ":
                if input.startswith("?", pointer + 1) or input.startswith(
                    "#", pointer + 1
                ):
                    url.path += "%20"
                else:
                    url.path += " "
            elif c:
                url.path += _percent_encode(c, _C0_CONTROL_SET)

        elif state == "query":
            if c == "#" or not c:
                encode_set = _SPECIAL_QUERY_SET if url.is_special else _QUERY_SET
                url.query = (url.query or "") + _percent_encode_string(
                    buffer, encode_set
                )
                buffer = ""
                if c == "#":
                    url.fragment = ""
                    state = "fragment"
            else:
                buffer += c

        elif state == "fragment":
            if c:
                url.fragment = (url.fragment or "") + _percent_encode(c, _FRAGMENT_SET)

        if pointer >= length:
            break
        pointer += 1

    return url


def _parse_host(input: str, is_opaque: bool) -> Optional[str]:
    # https://url.spec.whatwg.org/#concept-host-parser
    if input.startswith("["):
        if not input.endswith("]"):
            return None
        address = _parse_ipv6(input[1:-1])
        return None if address is None else "[" + address + "]"
    if is_opaque:
        if any(c in _FORBIDDEN_HOST_CODE_POINTS for c in input):
            return None
        return _percent_encode_string(input, _C0_CONTROL_SET)
    domain = _percent_decode(input).decode("utf-8", "replace")
    ascii_domain = _domain_to_ascii(domain)
    if ascii_domain is None:
        return None
    if _ends_in_a_number(ascii_domain):
        return _parse_ipv4(ascii_domain)
    return ascii_domain


def _domain_to_ascii(domain: str) -> Optional[str]:
    # https://url.spec.whatwg.org/#concept-domain-to-ascii
    # UTS #46 ToASCII, approximated with the IDNA 2003 nameprep of the codecs
    # module for the labels that are not ASCII.
    labels = []
    for label in _LABEL_SEPARATORS.split(domain):
        if label.isascii():
            labels.append(label.lower())
            continue
        try:
            # UTS #46 keeps the deviation characters that IDNA 2003 maps.
            label = "".join(
                (
                    part
                    if _DEVIATION_CHARACTERS.fullmatch(part)
                    else encodings.idna.nameprep(part)
                )
                for part in _DEVIATION_CHARACTERS.split(label)
            )
            if not label.isascii():
                if label.startswith("xn--"):
                    return None
                label = "xn--" + label.encode("punycode").decode("ascii")
        except UnicodeError:
            return None
        labels.append(label.lower())
    result = ".".join(labels)
    if result == "" or any(c in _FORBIDDEN_DOMAIN_CODE_POINTS for c in result):
        return None
    return result


def _ends_in_a_number(input: str) -> bool:
    # https://url.spec.whatwg.org/#ends-in-a-number-checker
    parts = input.split(".")
    if parts[-1] == "":
        if len(parts) == 1:
            return False
        parts.pop()
    last = parts[-1]
    if last != "" and all(c in _ASCII_DIGITS for c in last):
        return True
    return _parse_ipv4_number(last) is not None


def _parse_ipv4_number(input: str) -> Optional[int]:
    # https://url.spec.whatwg.org/#ipv4-number-parser
    if input == "":
        return None
    radix = 10
    if input[:2] in ("0x", "0X"):
        input = input[2:]
        radix = 16
    elif len(input) >= 2 and input[0] == "0":
        input = input[1:]
        radix = 8
    if input == "":
        return 0
    digits = {8: "01234567", 10: "0123456789", 16: "0123456789abcdefABCDEF"}[radix]
    if any(c not in digits for c in input):
        return None
    return int(input, radix)


def _parse_ipv4(input: str) -> Optional[str]:
    # https://url.spec.whatwg.org/#concept-ipv4-parser
    parts = input.split(".")
    if parts[-1] == "" and len(parts) > 1:
        parts.pop()
    if len(parts) > 4:
        return None
    numbers = []
    for part in parts:
        n = _parse_ipv4_number(part)
        if n is None:
            return None
        numbers.append(n)
    if any(n > 255 for n in numbers[:-1]):
        return None
    if numbers[-1] >= 256 ** (5 - len(numbers)):
        return None
    ipv4 = numbers[-1]
    for counter, n in enumerate(numbers[:-1]):
        ipv4 += n * 256 ** (3 - counter)
    return ".".join(str((ipv4 >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def _parse_ipv6(input: str) -> Optional[str]:
    # https://url.spec.whatwg.org/#concept-ipv6-parser
    if "%" in input:
        return None
    try:
        value = int(ipaddress.IPv6Address(input))
    except ValueError:
        return None
    # https://url.spec.whatwg.org/#concept-ipv6-serializer
    pieces = [(value >> (16 * (7 - i))) & 0xFFFF for i in range(8)]
    compress = None
    best = 1
    i = 0
    while i < 8:
        if pieces[i] != 0:
            i += 1
            continue
        start = i
        while i < 8 and pieces[i] == 0:
            i += 1
        if i - start > best:
            best = i - start
            compress = start
    output = ""
    ignore0 = False
    for index, piece in enumerate(pieces):
        if ignore0 and piece == 0:
            continue
        ignore0 = False
        if compress == index:
            output += "::" if index == 0 else ":"
            ignore0 = True
            continue
        output += format(piece, "x")
        if index != 7:
            output += ":"
    return output
