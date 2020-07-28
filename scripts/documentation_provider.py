import json
import re
from typing import Dict, List

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
        for line in api_md.split("\n"):
            matches = re.search(r"(class: (\w+)|(Playwright) module)", line)
            if matches:
                class_name = matches.group(2) or matches.group(3)
                method_name = None
            if class_name:
                if class_name not in self.documentation:
                    self.documentation[class_name] = {}
            matches = re.search(r"#### \w+\.(.+?)(\(|$)", line)
            if matches:
                method_name = matches.group(1)
                # Skip heading
                continue
            if "```js" in line:
                in_a_code_block = True
            elif "```" in line:
                in_a_code_block = False
            elif method_name and not in_a_code_block:
                if method_name not in self.documentation[class_name]:  # type: ignore
                    self.documentation[class_name][method_name] = []  # type: ignore
                self.documentation[class_name][method_name].append(line)  # type: ignore

    def _transform_doc_entry(self, entries: List[str]) -> List[str]:
        trimmed = "\n".join(entries).strip().replace("\\", "\\\\")
        trimmed = re.sub(r"<\[Array\]<\[(.*?)\]>>", r"<List[\1]>", trimmed)
        trimmed = trimmed.replace("Object", "Dict")
        trimmed = trimmed.replace("Array", "List")
        trimmed = trimmed.replace("boolean", "bool")
        trimmed = trimmed.replace("string", "str")
        trimmed = trimmed.replace("number", "int")
        trimmed = trimmed.replace("Buffer", "bytes")
        trimmed = re.sub(r"<\?\[(.*?)\]>", r"<Optional[\1]>", trimmed)
        trimmed = re.sub(r"<\[Promise\]<(.*)>>", r"<\1>", trimmed)
        trimmed = re.sub(r"<\[(\w+?)\]>", r"<\1>", trimmed)

        return trimmed.replace("\n\n\n", "\n\n").split("\n")

    def print_entry(self, class_name: str, method_name: str) -> None:
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
        doc_entries = self._transform_doc_entry(raw_doc)
        print(f'{ident}"""')
        for line in doc_entries:
            print(f"{ident}{line}")
        print(f'{ident}"""')


if __name__ == "__main__":
    print(
        json.dumps(
            DocumentationProvider().documentation["Page"].get("keyboard"),
            sort_keys=True,
            indent=4,
        )
    )
