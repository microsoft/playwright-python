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

# Checks each message that the client sends against the protocol spec
# (_protocol.py). The driver drops parameters that it does not know without an
# error, so a wrong parameter name in the client is silent without this check.
#
# The check is on when PW_CHECK_PROTOCOL=1; the test suite sets it. It does not
# raise: it records each violation, and the test suite fails the test that
# caused it. So a violation in a message that is sent without waiting for the
# reply is reported as well.

import os
from typing import Any, Callable, Dict, List, Optional

from playwright._impl._protocol import COMMANDS, EXTENDS, TYPES

_violations: List[str] = []


def is_enabled() -> bool:
    return os.environ.get("PW_CHECK_PROTOCOL") == "1"


def take_violations() -> List[str]:
    result = list(_violations)
    _violations.clear()
    return result


def check_message(
    type_name: str,
    method: str,
    params: Dict,
    metadata: Dict,
    type_of_guid: Callable[[str], Optional[str]],
) -> None:
    checker = _Checker(type_of_guid)
    if method == "__waitInfo__":
        checker.check("WaitInfo", params, "params")
    else:
        properties = _find_command(type_name, method)
        if properties is None:
            checker.errors.append("unknown method")
        else:
            checker.check_object(properties, params, "params")
    checker.check("Metadata", metadata, "metadata")
    for error in checker.errors:
        _violations.append(f"{type_name}.{method}: {error}")


def _find_command(type_name: Optional[str], method: str) -> Optional[Dict[str, Any]]:
    while type_name:
        commands = COMMANDS.get(type_name, {})
        if method in commands:
            return commands[method]
        type_name = EXTENDS.get(type_name)
    return None


def _is_same_or_derived(type_name: Optional[str], base: str) -> bool:
    while type_name:
        if type_name == base:
            return True
        type_name = EXTENDS.get(type_name)
    return False


class _Checker:
    def __init__(self, type_of_guid: Callable[[str], Optional[str]]) -> None:
        self._type_of_guid = type_of_guid
        self.errors: List[str] = []

    def check(self, spec: Any, value: Any, path: str) -> None:
        if isinstance(spec, str):
            self._check_name(spec.rstrip("?"), value, path)
            return
        kind = spec["type"].rstrip("?")
        if kind == "array":
            if not isinstance(value, list):
                self._expected("array", value, path)
                return
            for index, item in enumerate(value):
                self.check(spec["items"], item, f"{path}[{index}]")
        elif kind == "enum":
            if value not in spec["literals"]:
                literals = "|".join(spec["literals"])
                self.errors.append(
                    f"{path}: expected one of ({literals}), got {value!r}"
                )
        elif kind == "object":
            self.check_object(spec["properties"], value, path)

    def check_object(self, properties: Dict[str, Any], value: Any, path: str) -> None:
        if not isinstance(value, dict):
            self._expected("object", value, path)
            return
        for name, spec in properties.items():
            if name in value:
                self.check(spec, value[name], f"{path}.{name}")
            elif not _is_optional(spec):
                self.errors.append(f"{path}.{name}: missing")
        for name in value:
            if name not in properties:
                self.errors.append(f"{path}.{name}: unknown")

    def _check_name(self, name: str, value: Any, path: str) -> None:
        if name == "json":
            return
        if name in ("string", "binary"):
            if not isinstance(value, str):
                self._expected("string", value, path)
        elif name == "int":
            if isinstance(value, bool) or not (
                isinstance(value, int)
                or (isinstance(value, float) and value.is_integer())
            ):
                self._expected("integer", value, path)
        elif name == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                self._expected("float", value, path)
        elif name == "boolean":
            if not isinstance(value, bool):
                self._expected("boolean", value, path)
        elif name == "Channel" or name in COMMANDS:
            self._check_channel(name, value, path)
        else:
            self.check(TYPES[name], value, path)

    def _check_channel(self, name: str, value: Any, path: str) -> None:
        if not isinstance(value, dict) or not isinstance(value.get("guid"), str):
            self._expected(name, value, path)
            return
        if name == "Channel":
            return
        actual = self._type_of_guid(value["guid"])
        # An unknown guid is an object that is already gone; the driver reports it.
        if actual and not _is_same_or_derived(actual, name):
            self.errors.append(f"{path}: expected {name}, got {actual}")

    def _expected(self, expected: str, value: Any, path: str) -> None:
        self.errors.append(f"{path}: expected {expected}, got {type(value).__name__}")


def _is_optional(spec: Any) -> bool:
    if isinstance(spec, str):
        return spec.endswith("?")
    return spec["type"].endswith("?")
