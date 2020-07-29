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

import re
from sys import stderr
from typing import Any, Dict, List, cast

import requests


class DocumentationProvider:
    def __init__(self) -> None:
        self.documentation: Dict[str, Dict[str, List[str]]] = {}
        self.load()

    method_name_rewrites: Dict[str, str] = {
        "continue_": "continue",
        "evalOnSelector": "$eval",
        "evalOnSelectorAll": "$$eval",
        "querySelector": "$",
        "querySelectorAll": "$$",
    }

    def load(self) -> None:
        api_md = requests.get(
            "https://raw.githubusercontent.com/microsoft/playwright/master/docs/api.md"
        ).text

        class_name = None
        method_name = None
        in_a_code_block = False
        in_options = False
        pending_empty_line = False

        for line in api_md.split("\n"):
            if "```js" in line:
                in_a_code_block = True
            elif "```" in line:
                in_a_code_block = False
                continue
            if in_a_code_block:
                continue

            if line.startswith("### "):
                class_name = None
                method_name = None
                match = re.search(r"### class: (\w+)", line) or re.search(
                    r"### Playwright module", line
                )
                if match:
                    class_name = match.group(1) if match.groups() else "Playwright"
                    self.documentation[class_name] = {}  # type: ignore
                    continue
            if line.startswith("#### "):
                match = re.search(r"#### (\w+)\.(.+?)(\(|$)", line)
                if match:
                    if not class_name or match.group(1).lower() != class_name.lower():
                        print("Error: " + line + " in " + cast(str, class_name))
                    method_name = match.group(2)
                    pending_empty_line = False
                    self.documentation[class_name][method_name] = []  # type: ignore
                continue

            if not method_name:  # type: ignore
                continue

            if (
                line.startswith("- `options` <[Object]>")
                or line.startswith("- `options` <[string]|[Object]>")
                or line.startswith("- `overrides` <")
                or line.startswith("- `response` <")
            ):
                in_options = True
                continue
            if not line.startswith("  "):
                in_options = False
            if in_options:
                line = line[2:]
            # if not line.strip():
            #     continue
            if "Shortcut for" in line:
                continue
            if not line.strip():
                pending_empty_line = bool(self.documentation[class_name][method_name])  # type: ignore
                continue
            else:
                if pending_empty_line:
                    pending_empty_line = False
                    self.documentation[class_name][method_name].append("")  # type: ignore
            self.documentation[class_name][method_name].append(line)  # type: ignore

    def _transform_doc_entry(self, line: str) -> str:
        line = line.replace("\\", "\\\\")
        line = re.sub(r"<\[Array\]<\[(.*?)\]>>", r"<List[\1]>", line)
        line = line.replace("Object", "Dict")
        line = line.replace("Array", "List")
        line = line.replace("boolean", "bool")
        line = line.replace("string", "str")
        line = line.replace("number", "int")
        line = line.replace("Buffer", "bytes")
        line = re.sub(r"<\?\[(.*?)\]>", r"<Optional[\1]>", line)
        line = re.sub(r"<\[Promise\]<(.*)>>", r"<\1>", line)
        line = re.sub(r"<\[(\w+?)\]>", r"<\1>", line)

        # Following should be fixed in the api.md upstream
        line = re.sub(r"- `pageFunction` <[^>]+>", "- `expression` <[str]>", line)
        line = re.sub("- `urlOrPredicate`", "- `url`", line)
        line = re.sub("- `playwrightBinding`", "- `binding`", line)
        line = re.sub("- `playwrightFunction`", "- `binding`", line)
        line = re.sub("- `script`", "- `source`", line)

        return line

    def print_entry(
        self, class_name: str, method_name: str, signature: Dict[str, Any] = None
    ) -> None:
        if class_name == "BindingCall" or method_name == "pid":
            return
        if method_name in self.method_name_rewrites:
            method_name = self.method_name_rewrites[method_name]
        if (
            class_name == "ElementHandle"
            and method_name not in self.documentation[class_name]
        ):
            raw_doc = self.documentation["JSHandle"][method_name]
        else:
            raw_doc = self.documentation[class_name][method_name]

        ident = " " * 4 * 2

        if signature:
            if "return" in signature:
                del signature["return"]

        print(f'{ident}"""')

        # Validate signature
        validate_parameters = True
        for line in raw_doc:
            if not line.strip():
                validate_parameters = (
                    False  # Stop validating parameters after a blank line
                )

            transformed = self._transform_doc_entry(line)
            match = re.search(r"^\- `(\w+)`", transformed)
            if validate_parameters and signature and match:
                name = match.group(1)
                if name not in signature:
                    print(
                        f"Not implemented parameter {class_name}.{method_name}({name}=)",
                        file=stderr,
                    )
                    continue
                else:
                    del signature[name]
                print(f"{ident}{transformed}")
                if name == "expression" and "force_expr" in signature:
                    print(
                        f"{ident}- `force_expr` <[bool]> Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function"
                    )
                    del signature["force_expr"]
            else:
                print(f"{ident}{transformed}")

        print(f'{ident}"""')

        if signature:
            print(
                f"Not documented parameters: {class_name}.{method_name}({signature.keys()})",
                file=stderr,
            )


if __name__ == "__main__":
    DocumentationProvider().print_entry("Page", "goto")
    DocumentationProvider().print_entry("Page", "evaluateHandle")
    DocumentationProvider().print_entry("ElementHandle", "click")
    DocumentationProvider().print_entry("Page", "screenshot")
