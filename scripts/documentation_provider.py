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
from typing import Any, Dict, List, Set, Union, get_args, get_origin, get_type_hints
from urllib.parse import urljoin

from playwright._impl._helper import to_snake_case

enum_regex = r"^\"[^\"]+\"(?:\|\"[^\"]+\")+$"
union_regex = r"^[^\|]+(?:\|[^\|]+)+$"


class DocumentationProvider:
    def __init__(self, is_async: bool) -> None:
        self.is_async = is_async
        self.api: Any = {}
        self.links: Dict[str, str] = {}
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
            if not works_for_python(clazz):
                continue
            members = {}
            self.classes[clazz["name"]] = clazz
            events = []
            for member in clazz["members"]:
                if not works_for_python(member):
                    continue
                member_name = member["name"]
                new_name = name_or_alias(member)
                self._add_link(member["kind"], clazz["name"], member_name, new_name)

                if member["kind"] == "event":
                    events.append(member)
                else:
                    new_name = to_snake_case(new_name)
                    member["name"] = new_name
                    members[new_name] = member
                apply_type_or_override(member)

                if "args" in member:
                    args = {}
                    for arg in member["args"]:
                        if not works_for_python(arg):
                            continue
                        if arg["name"] == "options":
                            for option in arg["type"]["properties"]:
                                if not works_for_python(option):
                                    continue
                                option = self_or_override(option)
                                option_name = to_snake_case(name_or_alias(option))
                                option["name"] = option_name
                                option["required"] = False
                                args[option_name] = option
                        else:
                            arg = self_or_override(arg)
                            arg_name = to_snake_case(name_or_alias(arg))
                            arg["name"] = arg_name
                            args[arg_name] = arg

                    member["args"] = args

            clazz["members"] = members
            clazz["events"] = events

    def _add_link(self, kind: str, clazz: str, member: str, alias: str) -> None:
        match = re.match(r"(JS|CDP|[A-Z])([^.]+)", clazz)
        if not match:
            raise Exception("Invalid class " + clazz)
        var_name = to_snake_case(f"{match.group(1).lower()}{match.group(2)}")
        new_name = to_snake_case(alias)
        if kind == "event":
            new_name = new_name.lower()
            self.links[f"[`event: {clazz}.{member}`]"] = (
                f"`{var_name}.on('{new_name}')`"
            )
        elif kind == "property":
            self.links[f"[`property: {clazz}.{member}`]"] = f"`{var_name}.{new_name}`"
        else:
            self.links[f"[`method: {clazz}.{member}`]"] = f"`{var_name}.{new_name}()`"

    def print_entry(
        self,
        class_name: str,
        method_name: str,
        signature: Dict[str, Any] = None,
        is_property: bool = False,
    ) -> None:
        if class_name in ["BindingCall"] or method_name in [
            "pid",
        ]:
            return
        original_method_name = method_name
        self.printed_entries.append(f"{class_name}.{method_name}")
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

        doc_is_property = (
            not method.get("async") and not len(method["args"]) and "type" in method
        )
        if (
            method["name"].startswith("is_")
            or method["name"].startswith("as_")
            or method["name"] == "connect_to_server"
        ):
            doc_is_property = False
        if doc_is_property != is_property:
            self.errors.add(f"Method vs property mismatch: {fqname}")
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
                original_name = name
                doc_value = args.get(name)
                if name in args:
                    del args[name]
                if not doc_value:
                    self.errors.add(f"Parameter not documented: {fqname}({name}=)")
                else:
                    code_type = self.serialize_python_type(value, "in")

                    print(f"{indent}{to_snake_case(original_name)} : {code_type}")
                    if doc_value.get("comment"):
                        print(
                            f"{indent}    {self.indent_paragraph(self.render_links(doc_value['comment']), f'{indent}    ')}"
                        )
                    if doc_value.get("deprecated"):
                        print(
                            f"{indent}    Deprecated: {self.render_links(doc_value['deprecated'])}"
                        )
                    self.compare_types(code_type, doc_value, f"{fqname}({name}=)", "in")
        if (
            signature
            and "return" in signature
            and str(signature["return"]) != "<class 'NoneType'>"
        ):
            value = signature["return"]
            doc_value = method
            self.compare_types(value, doc_value, f"{fqname}(return=)", "out")
            print("")
            print("        Returns")
            print("        -------")
            print(f"        {self.serialize_python_type(value, 'out')}")
        print(f'{indent}"""')

        for name in args:
            if args[name].get("deprecated"):
                continue
            self.errors.add(
                f"Parameter not implemented: {class_name}.{method_name}({name}=)"
            )

    def print_events(self, class_name: str) -> None:
        clazz = self.classes[class_name]
        events = clazz["events"]
        if events:
            doc = []
            for event_type in ["on", "once"]:
                for event in events:
                    return_type = (
                        "typing.Union[typing.Awaitable[None], None]"
                        if self.is_async
                        else "None"
                    )
                    func_arg = self.serialize_doc_type(event["type"], "")
                    if func_arg.startswith("{"):
                        func_arg = "typing.Dict"
                    if "Union[" in func_arg:
                        func_arg = func_arg.replace("Union[", "typing.Union[")
                    if len(events) > 1:
                        doc.append("    @typing.overload")
                    impl = ""
                    if len(events) == 1:
                        impl = f"        return super().{event_type}(event=event,f=f)"
                    doc.append(
                        f"    def {event_type}(self, event: Literal['{event['name'].lower()}'], f: typing.Callable[['{func_arg}'], '{return_type}']) -> None:"
                    )
                    doc.append(
                        f'        """{self.beautify_method_comment(event["comment"], " " * 8)}"""'
                    )
                    doc.append(impl)
                if len(events) > 1:
                    doc.append(
                        f"    def {event_type}(self, event: str, f: typing.Callable[...,{return_type}]) -> None:"
                    )
                    doc.append(f"        return super().{event_type}(event=event,f=f)")
            print("\n".join(doc))

    def indent_paragraph(self, p: str, indent: str) -> str:
        lines = p.split("\n")
        result = [lines[0]]
        for line in lines[1:]:
            result.append(indent + line)
        return "\n".join(result)

    def beautify_method_comment(self, comment: str, indent: str) -> str:
        comment = self.filter_out_redudant_python_code_snippets(comment)
        comment = comment.replace("\\", "\\\\")
        comment = comment.replace('"', '\\"')
        lines = comment.split("\n")
        result = []
        skip_example = False
        last_was_blank = True
        for line in lines:
            if not line.strip():
                last_was_blank = True
                continue
            match = re.match(r"\s*```(.+)", line)
            if match:
                lang = match[1]
                if lang in ["html", "yml", "sh", "py", "python"]:
                    skip_example = False
                elif lang == "python " + ("async" if self.is_async else "sync"):
                    skip_example = False
                    line = "```py"
                else:
                    skip_example = True
            if not skip_example:
                if last_was_blank:
                    last_was_blank = False
                    result.append("")
                result.append(self.render_links(line))
            if skip_example and line.strip() == "```":
                skip_example = False
        comment = self.indent_paragraph("\n".join(result), indent)
        return self.resolve_playwright_dev_links(comment)

    def filter_out_redudant_python_code_snippets(self, comment: str) -> str:
        groups = []
        current_group = []
        lines = comment.split("\n")
        start_pos = None
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith("```py"):
                start_pos = i
            elif line == "```" and start_pos is not None:
                current_group.append((start_pos, i))
                start_pos = None
            elif (
                (line.startswith("```") or i == len(lines) - 1)
                and start_pos is None
                and len(current_group) == 2
            ):
                groups.append(current_group)
                current_group = []
        groups.reverse()
        for first_pos, second_pos in groups:
            # flake8: noqa: E203
            second_snippet_is_async = "await" in lines[second_pos[0] : second_pos[1]]
            if second_snippet_is_async == self.is_async:
                # flake8: noqa: E203
                del lines[first_pos[0] : first_pos[1] + 1]
            else:
                # flake8: noqa: E203
                del lines[second_pos[0] : second_pos[1] + 1]
        return "\n".join(lines)

    def resolve_playwright_dev_links(self, comment: str) -> str:
        def replace_callback(m: re.Match) -> str:
            link_text = m.group(1)
            link_href = m.group(2)
            resolved = urljoin(
                "https://playwright.dev/python/docs/api/", link_href.replace(".md", "")
            )
            return f"[{link_text}]({resolved})"

        # matches against internal markdown links which start with '.'/'..'
        # e.g. [Playwright](./class-foobar.md)
        return re.sub(r"\[([^\]]+)\]\((\.[^\)]+)\)", replace_callback, comment)

    def render_links(self, comment: str) -> str:
        for [old, new] in self.links.items():
            comment = comment.replace(old, new)
        return comment

    def make_optional(self, text: str) -> str:
        if text.startswith("Union["):
            if text.endswith("None]"):
                return text
            return text[:-1] + ", None]"
        return f"Union[{text}, None]"

    def compare_types(
        self, value: Any, doc_value: Any, fqname: str, direction: str
    ) -> None:
        if "(arg=)" in fqname or "(pageFunction=)" in fqname:
            return
        code_type = self.serialize_python_type(value, direction)
        doc_type = self.serialize_doc_type(doc_value["type"], direction)
        if not doc_value["required"]:
            doc_type = self.make_optional(doc_type)

        if doc_type != code_type:
            self.errors.add(
                f"Parameter type mismatch in {fqname}: documented as {doc_type}, code has {code_type}"
            )

    def serialize_python_type(self, value: Any, direction: str) -> str:
        str_value = str(value)
        if isinstance(value, list):
            return f"[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), value)))}]"
        if str_value == "<class 'playwright._impl._errors.Error'>":
            return "Error"
        if str_value == "<class 'NoneType'>":
            return "None"
        if str_value == "<class 'datetime.datetime'>":
            return "datetime.datetime"
        match = re.match(r"^<class '((?:pathlib\.)?\w+)'>$", str_value)
        if match:
            return match.group(1)
        match = re.match(
            r"playwright._impl._event_context_manager.EventContextManagerImpl\[playwright._impl.[^.]+.(.*)\]",
            str_value,
        )
        if match:
            return "EventContextManager[" + match.group(1) + "]"
        match = re.match(r"^<class 'playwright\._impl\.[\w_]+\.([^']+)'>$", str_value)
        if match and "_api_structures" not in str_value and "_errors" not in str_value:
            if match.group(1) == "EventContextManagerImpl":
                return "EventContextManager"
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
                signature.append(
                    f"{name}: {self.serialize_python_type(value, direction)}"
                )
            return f"{{{', '.join(signature)}}}"
        if origin == Union:
            args = get_args(value)
            if len(args) == 2 and str(args[1]) == "<class 'NoneType'>":
                return self.make_optional(
                    self.serialize_python_type(args[0], direction)
                )
            ll = list(map(lambda a: self.serialize_python_type(a, direction), args))
            ll.sort(key=lambda item: "}" if item == "None" else item)
            return f"Union[{', '.join(ll)}]"
        if str(origin) == "<class 'dict'>":
            args = get_args(value)
            return f"Dict[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 'collections.abc.Sequence'>":
            args = get_args(value)
            return f"Sequence[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 'list'>":
            args = get_args(value)
            list_type = "Sequence" if direction == "in" else "List"
            return f"{list_type}[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 'collections.abc.Callable'>":
            args = get_args(value)
            return f"Callable[{', '.join(list(map(lambda a: self.serialize_python_type(a, direction), args)))}]"
        if str(origin) == "<class 're.Pattern'>":
            return "Pattern[str]"
        if str(origin) == "typing.Literal":
            args = get_args(value)
            if len(args) == 1:
                return '"' + self.serialize_python_type(args[0], direction) + '"'
            body = ", ".join(
                list(
                    map(
                        lambda a: '"' + self.serialize_python_type(a, direction) + '"',
                        args,
                    )
                )
            )
            return f"Union[{body}]"
        return str_value

    def serialize_doc_type(self, type: Any, direction: str) -> str:
        result = self.inner_serialize_doc_type(type, direction)
        return result

    def inner_serialize_doc_type(self, type: Any, direction: str) -> str:
        if type["name"] == "Promise":
            type = type["templates"][0]

        if "union" in type:
            ll = [self.serialize_doc_type(t, direction) for t in type["union"]]
            ll.sort(key=lambda item: "}" if item == "None" else item)
            for i in range(len(ll)):
                if ll[i].startswith("Union["):
                    ll[i] = ll[i][6:-1]
            return f"Union[{', '.join(ll)}]"

        type_name = type["name"]
        if type_name == "path":
            if direction == "in":
                return "Union[pathlib.Path, str]"
            else:
                return "pathlib.Path"

        if type_name == "function" and "args" not in type:
            return "Callable"

        if type_name == "function":
            return_type = "Any"
            if type.get("returnType"):
                return_type = self.serialize_doc_type(type["returnType"], direction)
            return f"Callable[[{', '.join(self.serialize_doc_type(t, direction) for t in type['args'])}], {return_type}]"

        if "templates" in type:
            base = type_name
            if type_name == "Array":
                base = "Sequence" if direction == "in" else "List"
            if type_name == "Object" or type_name == "Map":
                base = "Dict"
            return f"{base}[{', '.join(self.serialize_doc_type(t, direction) for t in type['templates'])}]"

        if type_name == "Object" and "properties" in type:
            items = []
            for p in type["properties"]:
                items.append(
                    (p["name"])
                    + ": "
                    + (
                        self.serialize_doc_type(p["type"], direction)
                        if p["required"]
                        else self.make_optional(
                            self.serialize_doc_type(p["type"], direction)
                        )
                    )
                )
            return f"{{{', '.join(items)}}}"
        if type_name == "boolean":
            return "bool"
        if type_name == "long":
            return "int"
        if type_name.lower() == "string":
            return "str"
        if type_name == "any" or type_name == "Serializable":
            return "Any"
        if type_name == "Object":
            return "Dict"
        if type_name == "Function":
            return "Callable"
        if type_name == "Buffer" or type_name == "ReadStream":
            return "bytes"
        if type_name == "Date":
            return "datetime.datetime"
        if type_name == "URL":
            return "str"
        if type_name == "RegExp":
            return "Pattern[str]"
        if type_name == "null":
            return "None"
        if type_name == "EvaluationArgument":
            return "Dict"
        return type["name"]

    def print_remainder(self) -> None:
        for [class_name, clazz] in self.classes.items():
            for [member_name, member] in clazz["members"].items():
                if member.get("deprecated"):
                    continue
                if class_name in ["Error"]:
                    continue
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


def works_for_python(item: Any) -> bool:
    return not item["langs"].get("only") or "python" in item["langs"]["only"]


def name_or_alias(item: Any) -> str:
    alias = (
        item["langs"].get("aliases").get("python")
        if item["langs"].get("aliases")
        else None
    )
    return alias or item["name"]


def self_or_override(item: Any) -> Any:
    override = (
        item["langs"].get("overrides").get("python")
        if item["langs"].get("overrides")
        else None
    )
    return override or item


def apply_type_or_override(member: Any) -> Any:
    if member["langs"].get("types") and member["langs"]["types"].get("python"):
        member["type"] = member["langs"]["types"]["python"]
