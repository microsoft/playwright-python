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

"""Port of packages/playwright-core/src/client/errors.ts.

Python: the error classes are the public classes of playwright/_impl/_errors.py, so
that the API exports one set of classes for both implementations and
`type(error) is TimeoutError` holds. Error is the JS Error class that the client
throws (`throw new Error(...)`); PlaywrightError is upstream's PlaywrightError, the
same class here.
"""

import errno
import re
import traceback
from typing import TYPE_CHECKING, Any, Optional

from playwright._impl import _errors as api_errors

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import protocol_types as channels

__all__ = [
    "Error",
    "PlaywrightError",
    "TimeoutError",
    "TargetClosedError",
    "AbortError",
    "is_target_closed_error",
    "serialize_error",
    "parse_error",
    "patch_error_message",
]

PlaywrightError = api_errors.Error
# Python: `new Error(message)` in the client.
Error = api_errors.Error
TimeoutError = api_errors.TimeoutError
TargetClosedError = api_errors.TargetClosedError


# mirrors https://github.com/nodejs/node/blob/4e7c07dfe2b253393702545c0ffe2712b21fd3dd/lib/internal/errors.js#L976-L988
class AbortError(PlaywrightError):
    def __init__(self, message: str = "The operation was aborted") -> None:
        super().__init__(message)
        self._name = "AbortError"


def is_target_closed_error(error: BaseException) -> bool:
    return isinstance(error, TargetClosedError)


def serialize_error(e: Any) -> "channels.SerializedError":
    # Python: only exceptions are raised, so there is no "value" form. The message
    # and the code of an OSError are systemErrorMessage() and systemErrorCode().
    name = (e.name or "Error") if isinstance(e, api_errors.Error) else type(e).__name__
    error: Any = {
        "message": str(e),
        "stack": "".join(traceback.format_exception(type(e), e, e.__traceback__)),
        "name": name,
    }
    code = _system_error_code(e)
    if code is not None:
        error["code"] = code
    return {"error": error}


def _system_error_code(e: Any) -> Optional[str]:
    if isinstance(e, OSError) and e.errno is not None:
        return errno.errorcode.get(e.errno)
    return None


def parse_error(error: "channels.SerializedError") -> PlaywrightError:
    if not error.get("error"):
        if "value" not in error:
            raise PlaywrightError(
                "Serialized error must have either an error or a value"
            )
        # Python: upstream returns the thrown value itself; only an exception can
        # be raised.
        from playwright._impl.protocol.serializers import parse_serialized_value

        return PlaywrightError(str(parse_serialized_value(error["value"], None)))
    serialized = error["error"]
    e: PlaywrightError
    # Python: the messages use the Python option names (patch_error_message).
    message = patch_error_message(serialized["message"])
    if serialized.get("name") == "TimeoutError":
        e = TimeoutError(message)
    elif serialized.get("name") == "TargetClosedError":
        e = TargetClosedError(message)
    elif serialized.get("name") == "AbortError":
        e = AbortError(message)
    else:
        e = PlaywrightError(message)
    # Python: the name of each error is set here, as `new TimeoutError()` sets it in JS.
    e._name = serialized.get("name") or ""
    e._stack = serialized.get("stack") or ""
    if serialized.get("code") is not None:
        setattr(e, "code", serialized.get("code"))
    return e


def patch_error_message(message: str) -> str:
    # Python: the messages name the Python options.
    from playwright._impl.isomorphic.string_utils import to_snake_case

    match = re.match(r"(\w+)(: expected .*)", message)
    if match:
        message = to_snake_case(match.group(1)) + match.group(2)
    message = message.replace(
        "Pass { acceptDownloads: true }", "Pass 'accept_downloads=True'"
    )
    return message
