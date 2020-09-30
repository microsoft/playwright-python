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
from typing import (  # type: ignore
    Any,
    Dict,
    List,
    Set,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

enum_regex = r"^\"[^\"]+\"(?:\|\"[^\"]+\")+$"
union_regex = r"^[^\|]+(?:\|[^\|]+)+$"

exceptions = {
    "Route.fulfill(path=)": {
        "doc": "Optional[str]",
        "code": "Union[str, pathlib.Path, NoneType]",
    },
    "Browser.newContext(viewport=)": {
        "doc": 'Optional[{"width": int, "height": int}]',
        "code": 'Union[{"width": int, "height": int}, \'0\', NoneType]',
    },
    "Browser.newPage(viewport=)": {
        "doc": 'Optional[{"width": int, "height": int}]',
        "code": 'Union[{"width": int, "height": int}, \'0\', NoneType]',
    },
}


class DocumentationProvider:
    def __init__(self) -> None:
        self.api: Any = {}
        self.printed_entries: List[str] = []
        with open("api.json") as json_file:
            self.api = json.load(json_file)
        self.errors: Set[str] = set()

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
        if class_name in ["BindingCall", "Playwright"] or method_name in [
            "pid",
            "_add_event_handler",
            "remove_listener",
        ]:
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
                elif not doc_value and fqname == "Route.fulfill":
                    args = args["response"]["type"]["properties"]
                    doc_value = args.get(name)
                elif not doc_value and fqname == "Route.continue":
                    args = args["overrides"]["type"]["properties"]
                    doc_value = args.get(name)
                elif not doc_value and fqname == "Page.setViewportSize":
                    args = args["viewportSize"]["type"]["properties"]
                    doc_value = args.get(name)
                if not doc_value:
                    self.errors.add(
                        f"Missing parameter documentation: {fqname}({name}=)"
                    )
                else:
                    code_type = self.serialize_python_type(value)

                    print(f"{indent}{original_name} : {code_type}")
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
            doc_value = method
            self.compare_types(value, doc_value, f"{fqname}(return=)")
            print("")
            print("        Returns")
            print("        -------")
            print(f"        {self.serialize_python_type(value)}")
            if method["returnComment"]:
                print(
                    f"            {self.indent_paragraph(method['returnComment'], '              ')}"
                )
        print(f'{indent}"""')

        if signature_no_return:
            for name in signature_no_return:
                self.errors.add(
                    f"Parameter not implemented: {class_name}.{method_name}({name}=)"
                )

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

    def make_optional(self, text: str) -> str:
        if text.startswith("Union["):
            return text[:-1] + ", NoneType]"
        if text.startswith("Optional["):
            return text
        return f"Optional[{text}]"

    def compare_types(self, value: Any, doc_value: Any, fqname: str) -> None:
        if "(arg=)" in fqname or "(pageFunction=)" in fqname:
            return
        code_type = self.serialize_python_type(value)
        doc_type = self.serialize_doc_type(
            doc_value["type"]["name"],
            fqname,
            doc_value["type"],
        )
        if not doc_value["required"]:
            doc_type = self.make_optional(doc_type)
        if (
            fqname in exceptions
            and exceptions[fqname]["doc"] == doc_type
            and exceptions[fqname]["code"] == code_type
        ):
            return

        if doc_type != code_type:
            self.errors.add(
                f"Parameter type mismatch in {fqname}: documented as {doc_type}, code has {code_type}"
            )

    def serialize_python_type(self, value: Any) -> str:
        str_value = str(value)
        if str_value == "<class 'playwright.helper.Error'>":
            return "Error"
        match = re.match(r"^<class '((?:pathlib\.)?\w+)'>$", str_value)
        if match:
            return match.group(1)
        match = re.match(r"^<class 'playwright\.[\w]+\.([\w]+)'>$", str_value)
        if match and "helper" not in str_value:
            return match.group(1)

        match = re.match(r"^typing\.(\w+)$", str_value)
        if match:
            return match.group(1)

        origin = get_origin(value)
        args = get_args(value)
        hints = None
        try:
            hints = get_type_hints(value)
        except Exception:
            pass
        if hints:
            signature: List[str] = []
            for [name, value] in hints.items():
                signature.append(f'"{name}": {self.serialize_python_type(value)}')
            return f"{{{', '.join(signature)}}}"
        if origin == Union:
            args = get_args(value)
            if len(args) == 2 and "None" in str(args[1]):
                return self.make_optional(self.serialize_python_type(args[0]))
            return f"Union[{', '.join(list(map(lambda a: self.serialize_python_type(a), args)))}]"
        if str(origin) == "<class 'dict'>":
            args = get_args(value)
            return f"Dict[{', '.join(list(map(lambda a: self.serialize_python_type(a), args)))}]"
        if str(origin) == "<class 'list'>":
            args = get_args(value)
            return f"List[{', '.join(list(map(lambda a: self.serialize_python_type(a), args)))}]"
        if str(origin) == "typing.Literal":
            args = get_args(value)
            if len(args) == 1:
                return "'" + self.serialize_python_type(args[0]) + "'"
            body = ", ".join(
                list(map(lambda a: "'" + self.serialize_python_type(a) + "'", args))
            )
            return f"Literal[{body}]"
        return str_value

    def serialize_doc_type(
        self, type_name: Any, fqname: str, doc_type: Any = None
    ) -> str:
        type_name = re.sub(r"^Promise<(.*)>$", r"\1", type_name)

        if type_name == "string":
            return "str"

        if type_name == "Buffer":
            return "bytes"

        if type_name == "Array":
            return "List"

        if type_name == "boolean":
            return "bool"

        if type_name == "number":
            if "Mouse" in fqname and ("(x=)" in fqname or "(y=)" in fqname):
                return "float"
            if (
                "(position=)" in fqname
                or "(geolocation=)" in fqname
                or ".boundingBox(" in fqname
            ):
                return "float"
            if "screenshot(clip=)" in fqname:
                return "float"
            if fqname == "Page.pdf(width=)" or fqname == "Page.pdf(height=)":
                return "float"
            return "int"

        if type_name == "Serializable":
            return "Any"

        if type_name == "Object" or type_name == "?Object":
            intermediate = "Dict"
            if doc_type and len(doc_type["properties"]):
                signature: List[str] = []
                for [name, value] in doc_type["properties"].items():
                    value_type = self.serialize_doc_type(
                        value["type"]["name"], fqname, value["type"]
                    )
                    signature.append(
                        f"\"{name}\": {value_type if value['required'] else self.make_optional(value_type)}"
                    )
                intermediate = f"{{{', '.join(signature)}}}"
            return (
                intermediate
                if type_name == "Object"
                else self.make_optional(intermediate)
            )

        if type_name == "function":
            return "Callable"

        match = re.match(r"^Object<([^,]+),\s*([^)]+)>$", type_name)
        if match:
            return f"Dict[{self.serialize_doc_type(match.group(1), fqname)}, {self.serialize_doc_type(match.group(2), fqname)}]"

        match = re.match(r"^Map<([^,]+),\s*([^)]+)>$", type_name)
        if match:
            return f"Dict[{self.serialize_doc_type(match.group(1), fqname)}, {self.serialize_doc_type(match.group(2), fqname)}]"

        if re.match(enum_regex, type_name):
            result = f"Literal[{', '.join(type_name.split('|'))}]"
            return result.replace('"', "'")

        match = re.match(r"^Array<(.*)>$", type_name)
        if match:
            return f"List[{self.serialize_doc_type(match.group(1), fqname)}]"

        match = re.match(r"^\?(.*)$", type_name)
        if match:
            return self.make_optional(self.serialize_doc_type(match.group(1), fqname))

        match = re.match(r"^null\|(.*)$", type_name)
        if match:
            return self.make_optional(self.serialize_doc_type(match.group(1), fqname))

        # Union detection is greedy
        if re.match(union_regex, type_name):
            result = ", ".join(
                list(
                    map(
                        lambda a: self.serialize_doc_type(a, fqname),
                        type_name.split("|"),
                    )
                )
            )
            body = result.replace('"', "'")
            return f"Union[{body}]"

        return type_name

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
                    self.errors.add(f"Method not implemented: {entry}")

        with open("scripts/expected_api_mismatch.txt") as f:
            for line in f.readlines():
                sline = line.strip()
                if not len(sline) or sline.startswith("#"):
                    continue
                self.errors.remove(sline)

        if len(self.errors) > 0:
            for error in self.errors:
                print(error, file=stderr)
            exit(1)


if __name__ == "__main__":
    DocumentationProvider().print_entry("Page", "goto")
    DocumentationProvider().print_entry("Page", "evaluateHandle")
    DocumentationProvider().print_entry("ElementHandle", "click")
    DocumentationProvider().print_entry("Page", "screenshot")
