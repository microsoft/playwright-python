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


import copy
import re
import traceback
from types import TracebackType
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels


def is_target_closed_error(error: Exception) -> bool:
    return isinstance(error, TargetClosedError)


class Error(Exception):
    def __init__(self, message: str) -> None:
        self._message = message
        self._name = "Error"
        self._stack: Optional[str] = None
        self._details: Optional[Any] = None
        self._log: List[str] = []
        super().__init__(message)

    @property
    def message(self) -> str:
        return self._message

    @property
    def name(self) -> str:
        return self._name

    @property
    def stack(self) -> Optional[str]:
        return self._stack


class TimeoutError(Error):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self._name = "TimeoutError"


class TargetClosedError(Error):
    def __init__(self, message: str = None) -> None:
        super().__init__(message or "Target page, context or browser has been closed")


def rewrite_error_message(error: Exception, message: str) -> Exception:
    """Port of rewriteErrorMessage() in packages/utils/stackTrace.ts.

    The rewritten error keeps the class, the fields and the traceback. Upstream
    changes the error itself; this changes a copy, because the same error can fail
    several calls (the closed error of a connection), and each call adds its prefix.
    An exception that formats its message from other fields (OSError, KeyError)
    keeps its message.
    """
    try:
        rewritten = copy.copy(error)
    except Exception:
        # The class can not be built from its args: change the error itself.
        rewritten = error
    if isinstance(rewritten, Error):
        rewritten._message = message
        rewritten.args = (message,)
    elif len(rewritten.args) <= 1 and type(rewritten).__str__ is BaseException.__str__:
        rewritten.args = (message,)
    return rewritten.with_traceback(error.__traceback__)


def serialize_error(
    ex: Exception, tb: Optional[TracebackType]
) -> "channels.SerializedError":
    # Port of serializeError() in client/errors.ts. Python raises only exceptions, so
    # there is no "value" form. Only an Error has a name: other exceptions use the
    # class name, as e.name in JavaScript.
    return {
        "error": {
            "message": str(ex),
            "name": ex.name if isinstance(ex, Error) else type(ex).__name__,
            "stack": "".join(traceback.format_tb(tb)),
        }
    }


def parse_error(serialized: "channels.SerializedError") -> Error:
    # Port of parseError() in client/errors.ts.
    error = serialized.get("error")
    if not error:
        if "value" not in serialized:
            raise Error("Serialized error must have either an error or a value")
        # Upstream throws the value itself; Python can only raise an exception.
        from playwright._impl._serializers import parse_serialized_value

        return Error(str(parse_serialized_value(serialized["value"], None)))
    exc: Error
    if error.get("name") == "TimeoutError":
        exc = TimeoutError(patch_error_message(error["message"]))
    elif error.get("name") == "TargetClosedError":
        exc = TargetClosedError(patch_error_message(error["message"]))
    else:
        exc = Error(patch_error_message(error["message"]))
        exc._name = error["name"]
    exc._stack = error.get("stack") or ""
    return exc


def patch_error_message(message: str) -> str:
    from playwright._impl._str_utils import to_snake_case

    match = re.match(r"(\w+)(: expected .*)", message)
    if match:
        message = to_snake_case(match.group(1)) + match.group(2)
    message = message.replace(
        "Pass { acceptDownloads: true }", "Pass 'accept_downloads=True'"
    )
    return message
