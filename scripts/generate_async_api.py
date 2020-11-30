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
            and "expect_" not in name
            and "remove_listener" != name
        ):
            print("")
            if inspect.iscoroutinefunction(value):
                print(
                    f"    async def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
                )
                documentation_provider.print_entry(
                    class_name, name, get_type_hints(value, api_globals)
                )
                [prefix, suffix] = return_value(
                    get_type_hints(value, api_globals)["return"]
                )
                prefix = "        return " + prefix + f"await self._impl_obj.{name}("
                suffix = ")" + suffix
                print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
            else:
                print(
                    f"    def {name}({signature(value, len(name) + 9)}) -> {return_type(value)}:"
                )
                documentation_provider.print_entry(
                    class_name, name, get_type_hints(value, api_globals)
                )
                [prefix, suffix] = return_value(
                    get_type_hints(value, api_globals)["return"]
                )
                prefix = "        return " + prefix + f"self._impl_obj.{name}("
                suffix = ")" + suffix
                print(f"{prefix}{arguments(value, len(prefix))}{suffix}")
        if "expect_" in name:
            print("")
            return_type_value = return_type(value)
            return_type_value = re.sub(r"\"([^\"]+)Impl\"", r"\1", return_type_value)
            event_name = re.sub(r"expect_(.*)", r"\1", name)
            event_name = re.sub(r"_", "", event_name)
            event_name = re.sub(r"consolemessage", "console", event_name)

            print(
                f"""    def {name}({signature(value, len(name) + 9)}) -> Async{return_type_value}:
        \"\"\"{class_name}.{name}

        Returns context manager that waits for ``event`` to fire upon exit. It passes event's value
        into the ``predicate`` function and waits for the predicate to return a truthy value. Will throw
        an error if the page is closed before the ``event`` is fired.

        async with page.expect_{event_name}() as event_info:
            await page.click("button")
        value = event_info.value

        Parameters
        ----------
        predicate : Optional[typing.Callable[[Any], bool]]
            Predicate receiving event data.
        timeout : Optional[int]
            Maximum wait time in milliseconds, defaults to 30 seconds, pass `0` to disable the timeout.
            The default value can be changed by using the browserContext.setDefaultTimeout(timeout) or
            page.setDefaultTimeout(timeout) methods.
        \"\"\""""
            )

            wait_for_method = "waitForEvent(event, predicate, timeout)"
            if event_name == "request":
                wait_for_method = "waitForRequest(url, predicate, timeout)"
            elif event_name == "response":
                wait_for_method = "waitForResponse(url, predicate, timeout)"
            elif event_name == "loadstate":
                wait_for_method = "waitForLoadState(state, timeout)"
            elif event_name == "navigation":
                wait_for_method = "waitForNavigation(url, waitUntil, timeout)"
            elif event_name != "event":
                print(f'        event = "{event_name}"')

            print(
                f"        return AsyncEventContextManager(self._impl_obj.{wait_for_method})"
            )

    print("")
    print(f"mapping.register({class_name}Impl, {class_name})")


def main() -> None:
    print(header)
    print(
        "from playwright.async_base import AsyncEventContextManager, AsyncBase, mapping"
    )
    print("NoneType = type(None)")

    for t in all_types:
        generate(t)
    documentation_provider.print_remainder()


if __name__ == "__main__":  # pragma: no cover
    main()
