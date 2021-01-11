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
from types import FunctionType
from typing import Any, get_type_hints  # type: ignore

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

documentation_provider = DocumentationProvider()


def generate(t: Any) -> None:
    print("")
    class_name = short_name(t)
    base_class = t.__bases__[0].__name__
    base_sync_class = (
        "AsyncBase"
        if base_class == "ChannelOwner" or base_class == "object"
        else base_class
    )
    print(f"class {class_name}({base_sync_class}):")
    print("")
    print(f"    def __init__(self, obj: {class_name}Impl):")
    print("        super().__init__(obj)")
    for [name, type] in get_type_hints(t, api_globals).items():
        print("")
        print("    @property")
        print(f"    def {name}(self) -> {process_type(type)}:")
        documentation_provider.print_entry(class_name, name, {"return": type})
        [prefix, suffix] = return_value(type)
        prefix = "        return " + prefix + f"self._impl_obj.{name}"
        print(f"{prefix}{suffix}")
    for [name, value] in t.__dict__.items():
        if name.startswith("_"):
            continue
        if not name.startswith("_") and str(value).startswith("<property"):
            value = value.fget
            print("")
            print("    @property")
            print(
                f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
            )
            documentation_provider.print_entry(
                class_name, name, get_type_hints(value, api_globals)
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
            return_type_value = return_type_value.replace(
                "EventContextManager", "AsyncEventContextManager"
            )
            print("")
            async_prefix = "async " if is_async else ""
            await_prefix = "await " if is_async else ""
            print(
                f"    {async_prefix}def {name}({signature(value, len(name) + 9)}) -> {return_type_value}:"
            )
            documentation_provider.print_entry(
                class_name, name, get_type_hints(value, api_globals)
            )
            if "expect_" in name:
                print("")
                event_name = re.sub(r"expect_(.*)", r"\1", name)
                event_name = re.sub(r"_", "", event_name)
                event_name = re.sub(r"consolemessage", "console", event_name)
                wait_for_method = "wait_for_event(event, predicate, timeout)"
                if event_name == "request":
                    wait_for_method = "wait_for_request(url_or_predicate, timeout)"
                elif event_name == "response":
                    wait_for_method = "wait_for_response(url_or_predicate, timeout)"
                elif event_name == "loadstate":
                    wait_for_method = "wait_for_load_state(state, timeout)"
                elif event_name == "navigation":
                    wait_for_method = "wait_for_navigation(url, wait_until, timeout)"
                elif event_name != "event":
                    print(f'        event = "{event_name}"')

                print(
                    f"        return AsyncEventContextManager(self._impl_obj.{wait_for_method})"
                )
            else:
                [prefix, suffix] = return_value(
                    get_type_hints(value, api_globals)["return"]
                )
                prefix = prefix + f"{await_prefix}self._impl_obj.{name}("
                suffix = ")" + suffix
                print(
                    f"""
        try:
            log_api("=> {to_snake_case(class_name)}.{name} started")
            result = {prefix}{arguments(value, len(prefix))}{suffix}
            log_api("<= {to_snake_case(class_name)}.{name} succeded")
            return result
        except Exception as e:
            log_api("<= {to_snake_case(class_name)}.{name} failed")
            raise e"""
                )

    print("")
    print(f"mapping.register({class_name}Impl, {class_name})")


def main() -> None:
    print(header)
    print(
        "from playwright._impl._async_base import AsyncEventContextManager, AsyncBase, mapping"
    )
    print("NoneType = type(None)")

    for t in all_types:
        generate(t)
    documentation_provider.print_remainder()


if __name__ == "__main__":  # pragma: no cover
    main()
