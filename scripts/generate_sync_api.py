#!/usr/bin/env python
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

import inspect
import re
import sys
from types import FunctionType
from typing import Any, get_type_hints

from playwright._impl._helper import to_snake_case
from scripts.documentation_provider import DocumentationProvider
from scripts.generate_api import (
    all_types,
    api_globals,
    arguments,
    header,
    process_type,
    return_type,
    return_value,
    short_name,
    signature,
)

documentation_provider = DocumentationProvider(False)


def generate(t: Any) -> None:
    print("")
    class_name = short_name(t)
    base_class = t.__bases__[0].__name__
    if class_name in ["Page", "BrowserContext", "Browser"]:
        base_sync_class = "SyncContextManager"
    elif base_class in ["ChannelOwner", "object"]:
        base_sync_class = "SyncBase"
    else:
        base_sync_class = base_class
    print(f"class {class_name}({base_sync_class}):")
    print("")
    print(f"    def __init__(self, obj: {class_name}Impl):")
    print("        super().__init__(obj)")
    for [name, type] in get_type_hints(t, api_globals).items():
        print("")
        print("    @property")
        print(f"    def {name}(self) -> {process_type(type)}:")
        documentation_provider.print_entry(class_name, name, {"return": type}, True)
        [prefix, suffix] = return_value(type)
        prefix = "        return " + prefix + f"self._impl_obj.{name}"
        print(f"{prefix}{suffix}")
    for [name, value] in t.__dict__.items():
        if name.startswith("_"):
            continue
        if str(value).startswith("<property"):
            value = value.fget
            print("")
            print("    @property")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
            )
            documentation_provider.print_entry(
                class_name, name, get_type_hints(value, api_globals), True
            )
            [prefix, suffix] = return_value(
                get_type_hints(value, api_globals)["return"]
            )
            prefix = "        return " + prefix + f"self._impl_obj.{name}"
            print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
    for [name, value] in t.__dict__.items():
        if (
            not name.startswith("_")
            and isinstance(value, FunctionType)
            and "remove_listener" != name
        ):
            is_async = inspect.iscoroutinefunction(value)
            return_type_value = return_type(value)
            return_type_value = re.sub(r"\"([^\"]+)Impl\"", r"\1", return_type_value)
            print("")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type_value}:"
            )
            documentation_provider.print_entry(
                class_name, name, get_type_hints(value, api_globals)
            )
            if "expect_" in name:
                print(
                    f"        return EventContextManager(self, self._impl_obj.{name}({arguments(value, 12)}).future)"
                )
            else:
                [prefix, suffix] = return_value(
                    get_type_hints(value, api_globals)["return"]
                )
                if is_async:
                    prefix = (
                        prefix
                        + f'self._sync("{to_snake_case(class_name)}.{name}", self._impl_obj.{name}('
                    )
                    suffix = "))" + suffix
                else:
                    prefix = prefix + f"self._impl_obj.{name}("
                    suffix = ")" + suffix

                print(
                    f"""
        return {prefix}{arguments(value, len(prefix))}{suffix}"""
                )
    if class_name == "Playwright":
        print(
            """
    def __getitem__(self, value: str) -> "BrowserType":
        if value == "chromium":
            return self.chromium
        elif value == "firefox":
            return self.firefox
        elif value == "webkit":
            return self.webkit
        raise ValueError("Invalid browser "+value)
            """
        )
    print("")
    print(f"mapping.register({class_name}Impl, {class_name})")


def main() -> None:
    assert sys.version_info >= (3, 9)

    print(header)
    print(
        "from playwright._impl._sync_base import EventContextManager, SyncBase, SyncContextManager, mapping"
    )
    print("NoneType = type(None)")

    for t in all_types:
        generate(t)
    documentation_provider.print_remainder()


if __name__ == "__main__":  # pragma: no cover
    main()
