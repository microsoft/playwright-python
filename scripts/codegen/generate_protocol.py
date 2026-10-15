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

# Generates playwright/_impl/_protocol.py from the protocol spec
# (packages/protocol/spec/*.yml in microsoft/playwright).
#
# Usage:
#   PW_SRC_DIR=<microsoft/playwright checkout> python scripts/codegen/generate_protocol.py [--out <file>]
#
# The spec is loaded the same way as utils/protocol_spec.js does it. The output
# is not formatted; run black on it.

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

PRIMITIVES = {"string", "int", "float", "boolean", "binary", "json", "Channel"}

errors: List[str] = []


def load_protocol(spec_dir: Path) -> Dict[str, Any]:
    protocol: Dict[str, Any] = {}
    for file in sorted(spec_dir.glob("*.yml")):
        doc = yaml.safe_load(file.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise SystemExit(f"{file} is empty or not a YAML map")
        for name, value in doc.items():
            if name in protocol:
                raise SystemExit(f'Duplicate top-level definition "{name}" in {file}')
            protocol[name] = value
    return protocol


def js_string(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class Converter:
    def __init__(self, protocol: Dict[str, Any]) -> None:
        self._protocol = protocol

    def properties(self, props: Any, path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for name, value in (props or {}).items():
            if name.startswith("$mixin"):
                mixin = self._protocol[value]
                result.update(self.properties(mixin.get("properties"), path))
                continue
            if not isinstance(name, str):
                errors.append(f"{path}: property name {name!r} is not a string")
                continue
            result[name] = self.type(value, f"{path}.{name}")
        return result

    def type(self, value: Any, path: str) -> Any:
        if isinstance(value, str):
            name = value.rstrip("?")
            if name not in PRIMITIVES and name not in self._protocol:
                errors.append(f"{path}: unknown type {name}")
            return value
        kind = value["type"].rstrip("?")
        if kind == "array":
            return {"type": value["type"], "items": self.type(value["items"], path)}
        if kind == "enum":
            # Upstream turns each literal into a string, so `- null` is "null".
            return {
                "type": value["type"],
                "literals": [js_string(literal) for literal in value["literals"]],
            }
        if kind == "object":
            return {
                "type": value["type"],
                "properties": self.properties(value.get("properties"), path),
            }
        errors.append(f"{path}: unknown type {value['type']}")
        return value


def generate(protocol: Dict[str, Any]) -> str:
    converter = Converter(protocol)
    extends: Dict[str, str] = {}
    types: Dict[str, Any] = {}
    commands: Dict[str, Dict[str, Any]] = {}
    for name, item in protocol.items():
        if item["type"] == "interface":
            if item.get("extends"):
                extends[name] = item["extends"]
            commands[name] = {}
            for method, command in (item.get("commands") or {}).items():
                commands[name][method] = converter.properties(
                    (command or {}).get("parameters"), f"{name}.{method}"
                )
        elif item["type"] in ("object", "enum"):
            types[name] = converter.type(item, name)

    def dump(value: Any) -> str:
        return json.dumps(value, indent=4, sort_keys=False)

    return "\n".join(
        [
            LICENSE,
            "# Generated from packages/protocol/spec by scripts/codegen/generate_protocol.py. Do not edit.",
            "",
            "from typing import Any, Dict",
            "",
            "# The interface that each interface extends.",
            f"EXTENDS: Dict[str, str] = {dump(extends)}",
            "",
            "# The object and enum types, in the form of the spec.",
            f"TYPES: Dict[str, Any] = {dump(types)}",
            "",
            "# The parameters of each command, by interface and method.",
            f"COMMANDS: Dict[str, Dict[str, Dict[str, Any]]] = {dump(commands)}",
            "",
        ]
    )


LICENSE = """# Copyright (c) Microsoft Corporation.
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
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()
    pw_src_dir = os.environ.get("PW_SRC_DIR")
    if not pw_src_dir:
        raise SystemExit(
            "Set PW_SRC_DIR to a microsoft/playwright checkout at the release branch in DRIVER_VERSION."
        )
    text = generate(load_protocol(Path(pw_src_dir) / "packages" / "protocol" / "spec"))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
