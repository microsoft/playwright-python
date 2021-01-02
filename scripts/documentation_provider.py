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
import subprocess
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

from playwright._impl._helper import to_snake_case

enum_regex = r"^\"[^\"]+\"(?:\|\"[^\"]+\")+$"
union_regex = r"^[^\|]+(?:\|[^\|]+)+$"


class DocumentationProvider:
    def __init__(self) -> None:
        self.api: Any = {}
        self.printed_entries: List[str] = []
        process_output = subprocess.run(
            ["python", "-m", "playwright", "print-api-json"],
            check=True,
            capture_output=True,
        )
        self.api = json.loads(process_output.stdout)
        self.errors: Set[str] = set()
        self._patch_case()

    def _patch_case(self) -> None:
        self.classes = {}
        for clazz in self.api:
            members = {}
            self.classes[clazz["name"]] = clazz
            for member in clazz["members"]:
                if member["kind"] == "event":
                    continue
                method_name = member["name"]
                new_name = to_snake_case(method_name)
                if method_name == "continue":
                    new_name = "continue_"
                if method_name == "$eval":
                    new_name = "eval_on_selector"
                if method_name == "$$eval":
                    new_name = "eval_on_selector_all"
                if method_name == "$":
                    new_name = "query_selector"
                if method_name == "$$":
                    new_name = "query_selector_all"
                members[new_name] = member
                member["name"] = new_name

                if "args" in member:
                    args = {}
                    for arg in member["args"]:
                        arg_name = arg["name"]
                        new_name = to_snake_case(arg_name)
                        if arg_name == "pageFunction":
                            new_name = "expression"

                        expand_type = None
                        expand_as_optional = False
                        if arg_name == "options":
                            expand_type = arg["type"]
                            expand_as_optional = True
                        if arg_name == "optionsOrPredicate":
                            expand_type = arg["type"]["union"][1]
                            expand_as_optional = True
                        if arg_name == "params" and "properties" in arg["type"]:
                            expand_type = arg["type"]
                        if method_name == "emulateMedia" and arg_name == "params":
                            expand_type = arg["type"]
                        if method_name == "fulfill" and arg_name == "response":
                            expand_type = arg["type"]
                        if method_name == "continue" and arg_name == "overrides":
                            expand_type = arg["type"]
                        if (
                            method_name == "setViewportSize"
                            and arg_name == "viewportSize"
                        ):
                            expand_type = arg["type"]
                        if arg_name == "geolocation":
                            expand_type = arg["type"]["union"][1]
                        if arg_name == "frameSelector":
                            expand_type = arg["type"]["union"][1]

                        if expand_type:
                            for opt_property in expand_type["properties"]:
                                opt_name = opt_property["name"]
                                if opt_name == "recordHar" or opt_name == "recordVideo":
                                    for sub_property in opt_property["type"][
                                        "properties"
                                    ]:
                                        sub_name = sub_property["name"]
                                        new_sub_name = to_snake_case(
                                            opt_name
                                            + sub_name[0:1].upper()
                                            + sub_name[1:]
                                        )
                                        args[new_sub_name] = sub_property
                                        sub_property["name"] = new_sub_name
                                        sub_property["required"] = False
                                else:
                                    args[to_snake_case(opt_name)] = opt_property
                                    opt_property["name"] = to_snake_case(opt_name)
                                    if expand_as_optional:
                                        opt_property["required"] = False
                        else:
                            args[new_name] = arg
                            arg["name"] = new_name

                    member["args"] = args

            clazz["members"] = members

    def print_entry(
        self, class_name: str, method_name: str, signature: Dict[str, Any] = None
    ) -> None:
        if class_name in ["BindingCall"] or method_name in [
            "pid",
            "_add_event_handler",
            "remove_listener",
        ]:
            return
        original_method_name = method_name
        self.printed_entries.append(f"{class_name}.{method_name}")
        if class_name == "JSHandle":
            self.printed_entries.append(f"ElementHandle.{method_name}")
        clazz = self.classes[class_name]
        method = clazz["members"].get(method_name)
        if not method and "extends" in clazz:
            superclass = self.classes.get(clazz["extends"])
            if superclass:
                method = superclass["members"].get(method_name)
        fqname = f"{class_name}.{method_name}"

        if not method:
            self.errors.add(f"Method not documented: {fqname}")
            return

        indent = " " * 8
        print(f'{indent}"""{class_name}.{to_snake_case(original_method_name)}')
        if method.get("comment"):
            print(f"{indent}{self.beautify_method_comment(method['comment'], indent)}")
        signature_no_return = {**signature} if signature else None
        if signature_no_return and "return" in signature_no_return:
            del signature_no_return["return"]

        # Collect a list of all names, flatten options.
        args = method["args"]
        if signature and signature_no_return:
            print("")
            print("        Parameters")
            print("        ----------")
            for [name, value] in signature.items():
                name = to_snake_case(name)
                if name == "return":
                    continue
                if name == "force_expr":
                    continue
                original_name = name
                doc_value = args.get(name)
                if name in args:
                    del args[name]
                if not doc_value:
                    self.errors.add(f"Parameter not documented: {fqname}({name}=)")
                else:
                    code_type = self.serialize_python_type(value)

                    print(f"{indent}{to_snake_case(original_name)} : {code_type}")
                    if doc_value.get("comment"):
                        print(
                            f"{indent}    {self.indent_paragraph(self.render_links(doc_value['comment']), f'{indent}    ')}"
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
        print(f'{indent}"""')

        for name in args:
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
                result.append(self.render_links(line))
            if line.strip() == "```":
                in_example = False
        return self.indent_paragraph("\n".join(result), indent)

    def render_links(self, comment: str) -> str:
        def render(match: Any) -> str:
            return f"{to_snake_case(match.group(1).lower() + match.group(2))}.{to_snake_case(match.group(3))}"

        def render_property(match: Any) -> str:
            return f"`{render(match)}`"

        def render_method(match: Any) -> str:
            return f"`{render(match)}()`"

        comment = re.sub(
            r"\[`method: (JS|CDP|[A-Z])([^.]+)\.([^`]+)`\]", render_method, comment
        )
        comment = re.sub(
            r"\[`property: (JS|CDP|[A-Z])([^.]+)\.([^`]+)`\]", render_property, comment
        )
        return comment

    def make_optional(self, text: str) -> str:
        if text.startswith("Union["):
            if text.endswith("NoneType]"):
                return text
            return text[:-1] + ", NoneType]"
        return f"Union[{text}, NoneType]"

    def compare_types(self, value: Any, doc_value: Any, fqname: str) -> None:
        if "(arg=)" in fqname or "(pageFunction=)" in fqname:
            return
        code_type = self.serialize_python_type(value)
        doc_type = self.serialize_doc_type(doc_value["type"])
        if not doc_value["required"]:
            doc_type = self.make_optional(doc_type)

        if doc_type != code_type:
            self.errors.add(
                f"Parameter type mismatch in {fqname}: documented as {doc_type}, code has {code_type}"
            )

    def serialize_python_type(self, value: Any) -> str:
        str_value = str(value)
        if isinstance(value, list):
            return f"[{', '.join(list(map(lambda a: self.serialize_python_type(a), value)))}]"
        if str_value == "<class 'playwright._impl._types.Error'>":
            return "Error"
        match = re.match(r"^<class '((?:pathlib\.)?\w+)'>$", str_value)
        if match:
            return match.group(1)
        match = re.match(r"^<class 'playwright\._impl\.[\w_]+\.([\w]+)'>$", str_value)
        if (
            match
            and "_api_structures" not in str_value
            and "_api_types" not in str_value
        ):
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
                signature.append(f"{name}: {self.serialize_python_type(value)}")
            return f"{{{', '.join(signature)}}}"
        if origin == Union:
            args = get_args(value)
            if len(args) == 2 and str(args[1]) == "<class 'NoneType'>":
                return self.make_optional(self.serialize_python_type(args[0]))
            ll = list(map(lambda a: self.serialize_python_type(a), args))
            ll.sort(key=lambda item: "}" if item == "NoneType" else item)
            return f"Union[{', '.join(ll)}]"
        if str(origin) == "<class 'dict'>":
            args = get_args(value)
            return f"Dict[{', '.join(list(map(lambda a: self.serialize_python_type(a), args)))}]"
        if str(origin) == "<class 'list'>":
            args = get_args(value)
            return f"List[{', '.join(list(map(lambda a: self.serialize_python_type(a), args)))}]"
        if str(origin) == "<class 'collections.abc.Callable'>":
            args = get_args(value)
            return f"Callable[{', '.join(list(map(lambda a: self.serialize_python_type(a), args)))}]"
        if str(origin) == "typing.Literal":
            args = get_args(value)
            if len(args) == 1:
                return '"' + self.serialize_python_type(args[0]) + '"'
            body = ", ".join(
                list(map(lambda a: '"' + self.serialize_python_type(a) + '"', args))
            )
            return f"Union[{body}]"
        return str_value

    def serialize_doc_type(self, type: Any) -> str:
        result = self.inner_serialize_doc_type(type)
        if result == "{x: float, y: float}":
            result = "typing.Tuple[float, float]"
        if result == "Union[Callable, str]":
            return "str"
        if result == "{width: int, height: int}":
            return "typing.Tuple[int, int]"
        if result == "{username: str, password: str}":
            return "typing.Tuple[str, str]"
        return result

    def inner_serialize_doc_type(self, type: Any) -> str:
        if type["name"] == "Promise":
            type = type["templates"][0]

        if "union" in type:
            ll = [self.serialize_doc_type(t) for t in type["union"]]
            ll.sort(key=lambda item: "}" if item == "NoneType" else item)
            return f"Union[{', '.join(ll)}]"

        type_name = type["name"]
        if type_name == "path":
            return "Union[pathlib.Path, str]"

        if type_name == "function" and "args" not in type:
            return "Callable"

        if type_name == "function":
            return_type = "Any"
            if type.get("returnType"):
                return_type = self.serialize_doc_type(type["returnType"])
            return f"Callable[[{', '.join(self.serialize_doc_type(t) for t in type['args'])}], {return_type}]"

        if "templates" in type:
            base = type_name
            if type_name == "Array":
                base = "List"
            if type_name == "Object" or type_name == "Map":
                base = "Dict"
            return f"{base}[{', '.join(self.serialize_doc_type(t) for t in type['templates'])}]"

        if type_name == "Object" and "properties" in type:
            items = []
            for p in type["properties"]:
                items.append(
                    to_snake_case(p["name"])
                    + ": "
                    + (
                        self.serialize_doc_type(p["type"])
                        if p["required"]
                        else self.make_optional(self.serialize_doc_type(p["type"]))
                    )
                )
            return f"{{{', '.join(items)}}}"

        if type_name == "boolean":
            return "bool"
        if type_name == "string":
            return "str"
        if type_name == "Object" or type_name == "Serializable":
            return "Any"
        if type_name == "Buffer":
            return "bytes"
        if type_name == "URL":
            return "str"
        if type_name == "RegExp":
            return "Pattern"
        if type_name == "null":
            return "NoneType"
        if type_name == "EvaluationArgument":
            return "Dict"
        return type["name"]

    def print_remainder(self) -> None:
        for clazz in self.api:
            class_name = clazz["name"]
            for [member_name, member] in clazz["members"].items():
                entry = f"{class_name}.{member_name}"
                if entry not in self.printed_entries:
                    self.errors.add(f"Method not implemented: {entry}")

        with open("scripts/expected_api_mismatch.txt") as f:
            for line in f.readlines():
                sline = line.strip()
                if not len(sline) or sline.startswith("#"):
                    continue
                if sline in self.errors:
                    self.errors.remove(sline)
                else:
                    print("No longer there: " + sline, file=stderr)

        if len(self.errors) > 0:
            for error in self.errors:
                print(error, file=stderr)
            exit(1)
