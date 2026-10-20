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

"""Port of packages/utils/debug.ts and getAsBooleanFromENV() in packages/utils/env.ts."""

import os


def get_from_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        value = os.environ.get("npm_config_" + name.lower())
    return value or ""


def get_as_boolean_from_env(name: str, default_value: bool = False) -> bool:
    value = get_from_env(name)
    if value == "false" or value == "0":
        return False
    if value:
        return True
    return default_value


_debug_mode = get_from_env("PWDEBUG") or ""


def debug_mode() -> str:
    if _debug_mode == "console":
        return "console"
    if _debug_mode == "0" or _debug_mode == "false":
        return ""
    return "inspector" if _debug_mode else ""


_is_under_test = get_as_boolean_from_env("PWTEST_UNDER_TEST")


def is_under_test() -> bool:
    return _is_under_test
