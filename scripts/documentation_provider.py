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

import json
import re
from sys import stderr
from typing import Any, Dict, List

enum_regex = r"^\"[^\"]+\"(?:\|\"[^\"]+\")+$"
union_regex = r"^[^\|]+(?:\|[^\|]+)+$"


class DocumentationProvider:
    def __init__(self) -> None:
        self.api: Any = {}
        self.printed_entries: List[str] = []
        with open("api.json") as json_file:
            self.api = json.load(json_file)

    method_name_rewrites: Dict[str, str] = {
        "continue_": "continue",
        "evalOnSelector": "$eval",
        "evalOnSelectorAll": "$$eval",
        "querySelector": "$",
        "querySelectorAll": "$$",
    }

    def print_entry(
        self, class_name: str, method_name: str, signature: Dict[str, Any] = None
    ) -> None:
        if class_name == "Playwright":
            return
        if class_name == "BindingCall" or method_name == "pid":
            return
        original_method_name = method_name
        if method_name in self.method_name_rewrites:
            method_name = self.method_name_rewrites[method_name]
        self.printed_entries.append(f"{class_name}.{method_name}")
        if class_name == "JSHandle":
            self.printed_entries.append(f"ElementHandle.{method_name}")
        clazz = self.api[class_name]
        method = clazz["members"][method_name]
        fqname = f"{class_name}.{method_name}"
        indent = " " * 8
        print(f'{indent}"""{class_name}.{original_method_name}')
        if method["comment"]:
            print(f"{indent}{self.beautify_method_comment(method['comment'], indent)}")
        signature_no_return = {**signature} if signature else None
        if signature_no_return and "return" in signature_no_return:
            del signature_no_return["return"]
        if signature and signature_no_return:
            print("")
            print("        Parameters")
            print("        ----------")
            for [name, value] in signature.items():
                if name == "return":
                    continue
                del signature_no_return[name]
                if name == "force_expr":
                    continue
                original_name = name
                name = self.rewrite_param_name(fqname, method_name, name)
                args = method["args"]
                doc_value = args.get(name)
                if not doc_value and "options" in args:
                    args = args["options"]["type"]["properties"]
                    doc_value = args.get(name)
                if not doc_value and fqname == "Route.fulfill":
                    args = args["response"]["type"]["properties"]
                    doc_value = args.get(name)
                if not doc_value and fqname == "Route.continue":
                    args = args["overrides"]["type"]["properties"]
                    doc_value = args.get(name)
                if not doc_value and fqname == "Page.setViewportSize":
                    args = args["viewportSize"]["type"]["properties"]
                    doc_value = args.get(name)
                if not doc_value:
                    print(
                        f"Missing parameter documentation: {fqname}({name}=)",
                        file=stderr,
                    )
                else:
                    code_type = self.normalize_class_type(value)

                    print(
                        f"{indent}{original_name} : {self.beautify_code_type(code_type)}"
                    )
                    if doc_value["comment"]:
                        print(
                            f"{indent}    {self.indent_paragraph(doc_value['comment'], f'{indent}    ')}"
                        )
                    if original_name == "expression":
                        print(f"{indent}force_expr : bool")
                        print(
                            f"{indent}    Whether to treat given expression as JavaScript evaluate expression, even though it looks like an arrow function"
                        )
                    self.compare_types(code_type, doc_value, f"{fqname}({name}=)")
        if (
            signature
            and "return" in signature
            and str(signature["return"]) != "<class 'NoneType'>"
        ):
            value = signature["return"]
            code_type = self.normalize_class_type(value)
            doc_value = method
            self.compare_types(code_type, doc_value, f"{fqname}(return=)")
            print("")
            print("        Returns")
            print("        -------")
            print(f"        {self.normalize_class_type(signature['return'])}")
            if method["returnComment"]:
                print(
                    f"            {self.indent_paragraph(method['returnComment'], '              ')}"
                )
        print(f'{indent}"""')

        if signature_no_return:
            for name in signature_no_return:
                print(
                    f"Parameter not implemented: {class_name}.{method_name}({name}=)",
                    file=stderr,
                )

    def normalize_class_type(self, value: Any) -> str:
        code_type = str(value)
        code_type = re.sub(r"<class '(.*)'>", r"\1", code_type)
        code_type = re.sub(r"playwright\.[\w]+\.([\w]+)", r"\1", code_type)
        return code_type

    def indent_paragraph(self, p: str, indent: str) -> str:
        lines = p.split("\n")
        result = [lines[0]]
        for line in lines[1:]:
            result.append(indent + line)
        return "\n".join(result)

    def beautify_method_comment(self, comment: str, indent: str) -> str:
        lines = comment.split("\n")
        result = []
        in_example = False
        last_was_blank = True
        for line in lines:
            if not line.strip():
                last_was_blank = True
                continue
            if line.strip() == "```js":
                in_example = True
            if not in_example:
                if last_was_blank:
                    last_was_blank = False
                    result.append("")
                result.append(line)
            if line.strip() == "```":
                in_example = False
        return self.indent_paragraph("\n".join(result), indent)

    def beautify_code_type(self, code_type: str) -> str:
        return re.sub(r"^typing.Union\[(.*), NoneType\]$", r"Optional[\1]", code_type)

    def compare_types(self, code_type: str, doc_value: Any, fqname: str) -> None:
        type_name = doc_value["type"]["name"]
        doc_type = self.serialize_doc_type(type_name, fqname)
        if not doc_value["required"]:
            doc_type = f"typing.Union[{doc_type}, NoneType]"
        if doc_type != code_type:
            print(
                f"Parameter type mismatch in {fqname}: documented as {doc_type}, code has {code_type}",
                file=stderr,
            )

    def serialize_doc_type(self, doc_value: Any, fqname: str) -> str:
        if doc_value == "string":
            return "str"

        if doc_value == "Buffer":
            return "bytes"

        if doc_value == "boolean":
            return "bool"

        if doc_value == "number":
            if "Mouse" in fqname and ("(x=)" in fqname or "(y=)" in fqname):
                return "float"
            elif fqname == "Page.pdf(width=)" or fqname == "Page.pdf(height=)":
                return "float"
            else:
                return "int"

        if doc_value == "Object":
            return "typing.Dict"

        if doc_value == "?Object":
            return "typing.Union[typing.Dict, NoneType]"

        if doc_value == "function":
            return "typing.Callable"

        match = re.match(r"^Object<([^,]+),\s*([^)]+)>$", doc_value)
        if match:
            return f"typing.Dict[{self.serialize_doc_type(match.group(1), fqname)}, {self.serialize_doc_type(match.group(2), fqname)}]"

        match = re.match(r"^Promise<(.*)>$", doc_value)
        if match:
            return self.serialize_doc_type(match.group(1), fqname)

        if re.match(enum_regex, doc_value):
            result = f"typing.Literal[{', '.join(doc_value.split('|'))}]"
            return result.replace('"', "'")

        match = re.match(r"^Array<(.*)>$", doc_value)
        if match:
            return f"typing.List[{self.serialize_doc_type(match.group(1), fqname)}]"

        match = re.match(r"^\?(.*)$", doc_value)
        if match:
            return f"typing.Union[{self.serialize_doc_type(match.group(1), fqname)}, NoneType]"

        match = re.match(r"^null\|(.*)$", doc_value)
        if match:
            return f"typing.Union[{self.serialize_doc_type(match.group(1), fqname)}, NoneType]"

        # Union detection is greedy
        if re.match(union_regex, doc_value):
            result = ", ".join(
                list(
                    map(
                        lambda a: self.serialize_doc_type(a, fqname),
                        doc_value.split("|"),
                    )
                )
            )
            return result.replace('"', "'")

        return doc_value

    def rewrite_param_name(self, fqname: str, method_name: str, name: str) -> str:
        if name == "expression":
            return "pageFunction"
        if method_name == "exposeBinding" and name == "binding":
            return "playwrightBinding"
        if method_name == "exposeFunction" and name == "binding":
            return "playwrightFunction"
        if method_name == "addInitScript" and name == "source":
            return "script"
        if fqname == "Selectors.register" and name == "source":
            return "script"
        if fqname == "Page.waitForRequest" and name == "url":
            return "urlOrPredicate"
        if fqname == "Page.waitForResponse" and name == "url":
            return "urlOrPredicate"
        return name

    def print_remainder(self) -> None:
        for [class_name, value] in self.api.items():
            class_name = re.sub(r"Chromium(.*)", r"\1", class_name)
            class_name = re.sub(r"WebKit(.*)", r"\1", class_name)
            class_name = re.sub(r"Firefox(.*)", r"\1", class_name)
            for [method_name, method] in value["members"].items():
                if method["kind"] == "event":
                    continue
                entry = f"{class_name}.{method_name}"
                if entry not in self.printed_entries:
                    print(f"Method not implemented: {entry}", file=stderr)


if __name__ == "__main__":
    DocumentationProvider().print_entry("Page", "goto")
    DocumentationProvider().print_entry("Page", "evaluateHandle")
    DocumentationProvider().print_entry("ElementHandle", "click")
    DocumentationProvider().print_entry("Page", "screenshot")
