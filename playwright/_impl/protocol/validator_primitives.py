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

"""Port of packages/protocol/src/validatorPrimitives.ts.

Python: None is undefined. Binary values are base64 strings on both sides of the
channel (the "base64" mode); the JS modes are kept for completeness.
"""

import base64
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Union

from playwright._impl.errors import Error


class ValidationError(Error):
    # Python: a playwright Error, so that `except Error` sees it, as the driver's
    # validation errors are seen today.
    pass


BinaryMode = Literal["toBase64", "fromBase64", "buffer", "base64"]


class ValidatorContext:
    def __init__(
        self,
        t_channel_impl: Callable[
            [Union[Literal["*"], List[str]], Any, str, "ValidatorContext"], Any
        ],
        binary: BinaryMode,
        is_under_test: Callable[[], bool],
    ) -> None:
        self.t_channel_impl = t_channel_impl
        self.binary: BinaryMode = binary
        self.is_under_test = is_under_test
        # Python: whether the value is inside an array; see t_optional().
        self.in_array = False

    def _array_items(self) -> "ValidatorContext":
        if self.in_array:
            return self
        context = ValidatorContext(self.t_channel_impl, self.binary, self.is_under_test)
        context.in_array = True
        return context


Validator = Callable[[Any, str, ValidatorContext], Any]

scheme: Dict[str, Validator] = {}


def find_validator(type: str, method: str, kind: str) -> Validator:
    validator = maybe_find_validator(type, method, kind)
    if not validator:
        raise ValidationError(f"Unknown scheme for {kind}: {type}.{method}")
    return validator


def maybe_find_validator(type: str, method: str, kind: str) -> Optional[Validator]:
    scheme_name = (
        type + ("" if kind == "Initializer" else method[0].upper() + method[1:]) + kind
    )
    return scheme.get(scheme_name)


def create_metadata_validator() -> Validator:
    return t_optional(scheme["Metadata"])


def create_wait_info_validator() -> Validator:
    return scheme["WaitInfo"]


def _typeof(arg: Any) -> str:
    # Python: the JS typeof of a Python value.
    if arg is None:
        return "undefined"
    if isinstance(arg, bool):
        return "boolean"
    if isinstance(arg, (int, float)):
        return "number"
    if isinstance(arg, str):
        return "string"
    if callable(arg):
        return "function"
    return "object"


def _is_number(arg: Any) -> bool:
    return isinstance(arg, (int, float)) and not isinstance(arg, bool)


def t_float(arg: Any, path: str, context: ValidatorContext) -> Any:
    if _is_number(arg):
        return arg
    raise ValidationError(f"{path}: expected float, got {_typeof(arg)}")


def t_int(arg: Any, path: str, context: ValidatorContext) -> Any:
    if _is_number(arg):
        value = arg
    else:
        raise ValidationError(f"{path}: expected integer, got {_typeof(arg)}")
    if isinstance(value, float) and not value.is_integer():
        raise ValidationError(f"{path}: expected integer, got float {value}")
    return value


def t_boolean(arg: Any, path: str, context: ValidatorContext) -> Any:
    if isinstance(arg, bool):
        return arg
    raise ValidationError(f"{path}: expected boolean, got {_typeof(arg)}")


def t_string(arg: Any, path: str, context: ValidatorContext) -> Any:
    if isinstance(arg, str):
        return arg
    raise ValidationError(f"{path}: expected string, got {_typeof(arg)}")


def t_binary(arg: Any, path: str, context: ValidatorContext) -> Any:
    if context.binary == "base64":
        # Python: the base64 string goes through as it is.
        if isinstance(arg, str):
            return arg
        raise ValidationError(
            f"{path}: expected base64-encoded buffer, got {_typeof(arg)}"
        )
    if context.binary == "fromBase64":
        if isinstance(arg, str):
            return base64.b64decode(arg)
        raise ValidationError(
            f"{path}: expected base64-encoded buffer, got {_typeof(arg)}"
        )
    if context.binary == "toBase64":
        if not isinstance(arg, (bytes, bytearray)):
            raise ValidationError(f"{path}: expected Buffer, got {_typeof(arg)}")
        return base64.b64encode(arg).decode()
    if context.binary == "buffer":
        # Python: `arg instanceof Object` is false for a primitive.
        if not isinstance(arg, (bytes, bytearray)) and isinstance(
            arg, (str, int, float, type(None))
        ):
            raise ValidationError(f"{path}: expected Buffer, got {_typeof(arg)}")
        return arg
    raise ValidationError(f'Unsupported binary behavior "{context.binary}"')


def t_undefined(arg: Any, path: str, context: ValidatorContext) -> Any:
    if arg is None:
        return arg
    raise ValidationError(f"{path}: expected undefined, got {_typeof(arg)}")


def t_any(arg: Any, path: str, context: ValidatorContext) -> Any:
    return arg


# Python: None is undefined, and also JSON null. In the items of an array, a JSON
# value that is there with None is null, as it is data (an IndexedDB value in a
# storage state); everywhere else, None is an absent option.
_NULL = object()


def t_optional(v: Validator) -> Validator:
    keeps_null = v is t_any

    def validator(arg: Any, path: str, context: ValidatorContext) -> Any:
        if arg is None:
            return _NULL if keeps_null and context.in_array else arg
        return v(arg, path, context)

    return validator


def t_array(v: Validator) -> Validator:
    def validator(arg: Any, path: str, context: ValidatorContext) -> Any:
        # Python: a tuple is an array too.
        if not isinstance(arg, (list, tuple)):
            raise ValidationError(f"{path}: expected array, got {_typeof(arg)}")
        items = context._array_items()
        result = [
            v(x, path + "[" + str(index) + "]", items) for index, x in enumerate(arg)
        ]
        return [None if x is _NULL else x for x in result]

    return validator


def t_object(s: Dict[str, Validator]) -> Validator:
    def validator(arg: Any, path: str, context: ValidatorContext) -> Any:
        if not isinstance(arg, dict):
            raise ValidationError(f"{path}: expected object, got {_typeof(arg)}")
        result: Dict[str, Any] = {}
        for key, v in s.items():
            value = v(arg.get(key), path + "." + key if path else key, context)
            if value is _NULL:
                # Python: a key that is there with None is null; a key that is not
                # there is undefined.
                if key in arg:
                    result[key] = None
            elif value is not None:
                result[key] = value
        if context.is_under_test():
            for key, value in arg.items():
                if key.startswith("__testHook"):
                    result[key] = value
        return result

    return validator


def t_enum(e: Sequence[str]) -> Validator:
    def validator(arg: Any, path: str, context: ValidatorContext) -> Any:
        if arg not in e:
            raise ValidationError(f"{path}: expected one of ({'|'.join(e)})")
        return arg

    return validator


def t_channel(names: Union[Literal["*"], List[str]]) -> Validator:
    def validator(arg: Any, path: str, context: ValidatorContext) -> Any:
        return context.t_channel_impl(names, arg, path, context)

    return validator


def t_type(name: str) -> Validator:
    def validator(arg: Any, path: str, context: ValidatorContext) -> Any:
        v = scheme.get(name)
        if not v:
            raise ValidationError(path + ': unknown type "' + name + '"')
        return v(arg, path, context)

    return validator
