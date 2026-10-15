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

"""Port of packages/playwright-core/src/client/errors.ts."""

# These are types that we use in the API. They are public and are a part of the
# stable API.


import re
import traceback
from types import TracebackType
from typing import Any, List, Optional, TypedDict


def is_target_closed_error(error: Exception) -> bool:
    return isinstance(error, TargetClosedError)


class Error(Exception):
    def __init__(self, message: str) -> None:
        self._message = message
        self._name: Optional[str] = None
        self._stack: Optional[str] = None
        self._details: Optional[Any] = None
        self._log: Optional[List[str]] = None
        super().__init__(message)

    @property
    def message(self) -> str:
        return self._message

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def stack(self) -> Optional[str]:
        return self._stack


class TimeoutError(Error):
    pass


class TargetClosedError(Error):
    def __init__(self, message: str = None) -> None:
        super().__init__(message or "Target page, context or browser has been closed")


def rewrite_error(error: Exception, message: str) -> Exception:
    rewritten_exc = type(error)(message)
    if isinstance(rewritten_exc, Error) and isinstance(error, Error):
        rewritten_exc._name = error.name
        rewritten_exc._stack = error.stack
        rewritten_exc._details = error._details
        rewritten_exc._log = error._log
    return rewritten_exc


class ErrorPayload(TypedDict, total=False):
    message: str
    name: str
    stack: str
    value: Optional[Any]


def serialize_error(ex: Exception, tb: Optional[TracebackType]) -> ErrorPayload:
    return ErrorPayload(
        message=str(ex), name="Error", stack="".join(traceback.format_tb(tb))
    )


def parse_error(error: ErrorPayload, log: Optional[str] = None) -> Error:
    base_error_class = Error
    if error.get("name") == "TimeoutError":
        base_error_class = TimeoutError
    if error.get("name") == "TargetClosedError":
        base_error_class = TargetClosedError
    if not log:
        log = ""
    exc = base_error_class(patch_error_message(error["message"]) + log)
    exc._name = error["name"]
    exc._stack = error["stack"]
    return exc


def patch_error_message(message: str) -> str:
    match = re.match(r"(\w+)(: expected .*)", message)
    if match:
        message = to_snake_case(match.group(1)) + match.group(2)
    message = message.replace(
        "Pass { acceptDownloads: true }", "Pass 'accept_downloads=True'"
    )
    return message


# Upstream: toSnakeCase() in packages/isomorphic/stringUtils.ts. It is here, not
# in _str_utils.py, because _str_utils.py imports this module.
to_snake_case_regex = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_snake_case(name: str) -> str:
    return to_snake_case_regex.sub(r"_\1", name).lower()
