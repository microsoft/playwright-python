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
        for line in api_md.split("\n"):
            if matches := re.search(r"(class: (\w+)|(Playwright) module)", line):
                class_name = matches.group(2) or matches.group(3)
                method_name = None
            if class_name:
                if class_name not in self.documentation:
                    self.documentation[class_name] = {}
            if matches := re.search(r"#### \w+\.(.+?)(\(|$)", line):
                method_name = matches.group(1)
                # Skip heading
                continue
            if method_name:
                if method_name not in self.documentation[class_name]:  # type: ignore
                    self.documentation[class_name][method_name] = []  # type: ignore
                self.documentation[class_name][method_name].append(line)  # type: ignore

    def _trim_lines(self, entries: List[str]) -> List[str]:
        return "\n".join(entries).strip().replace("\\", "\\\\").split("\n")

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
        doc_entries = self._trim_lines(raw_doc)
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
