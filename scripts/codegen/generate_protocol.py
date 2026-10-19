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

# Generates from the protocol spec (packages/protocol/spec/*.yml in
# microsoft/playwright):
# - playwright/_impl/_protocol.py: the tables that _protocol_check.py uses;
# - playwright/_impl/_protocol_types.py: the TypedDicts of the messages;
# - playwright/_impl/_protocol_channels.py: a typed channel class per interface.
#
# Usage:
#   PW_SRC_DIR=<microsoft/playwright checkout> python scripts/codegen/generate_protocol.py \
#       --out <file> --types-out <file> --channels-out <file>
#
# The spec is loaded the same way as utils/protocol_spec.js does it. The output
# is not formatted; run black on it.

import argparse
import json
import keyword
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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


def title_case(name: str) -> str:
    return name[0].upper() + name[1:]


def is_optional(spec: Any) -> bool:
    return (spec if isinstance(spec, str) else spec["type"]).endswith("?")


class TypesEmitter:
    # Names follow upstream's utils/generate_channels.js. An inline object gets
    # the name of its owner plus the field name.
    #
    # The types differ from upstream's in these ways:
    # - The top-level fields of the params, results and events are all present.
    #   An absent optional field is None: the caller passes None, and the
    #   channel fills in None for a field that the driver left out. So mypy
    #   reports each call that does not pass a new parameter.
    # - In the data that the client sends, an optional field of a nested object
    #   also accepts None, and an array accepts any sequence. The connection
    #   drops None values from objects before it sends a message. It does not
    #   drop them from objects inside arrays, so there an optional field does
    #   not accept None.

    def __init__(self, protocol: Dict[str, Any]) -> None:
        self._protocol = protocol
        self.blocks: List[str] = []
        self.names: Set[str] = set()

    def py_type(
        self, spec: Any, name: str, sent: bool = False, in_array: bool = False
    ) -> str:
        if isinstance(spec, str):
            base = spec.rstrip("?")
            simple = {
                "string": "str",
                "binary": "str",
                "int": "int",
                "float": "float",
                "boolean": "bool",
                "json": "Any",
                "Channel": "Channel",
            }
            if base in simple:
                return simple[base]
            if self._protocol[base]["type"] == "interface":
                return f"{base}Channel"
            return base
        kind = spec["type"].rstrip("?")
        if kind == "array":
            array = "Sequence" if sent else "List"
            return f"{array}[{self.py_type(spec['items'], name, sent, True)}]"
        if kind == "enum":
            return "Literal[" + ", ".join(json.dumps(v) for v in spec["literals"]) + "]"
        self.emit_class(name, self.fields(name, spec["properties"], sent, in_array))
        return name

    def fields(
        self,
        name: str,
        properties: Dict[str, Any],
        sent: bool = False,
        in_array: bool = False,
        top_level: bool = False,
    ) -> List[Tuple[str, str]]:
        result = []
        for field, spec in properties.items():
            field_type = self.py_type(spec, name + title_case(field), sent, in_array)
            if is_optional(spec):
                if top_level or (sent and not in_array):
                    field_type = f"Optional[{field_type}]"
                if not top_level:
                    field_type = f"NotRequired[{field_type}]"
            result.append((field, field_type))
        return result

    def emit_class(self, name: str, fields: List[Tuple[str, str]]) -> None:
        if name in self.names:
            errors.append(f"Two types are named {name}")
        self.names.add(name)
        if any(keyword.iskeyword(field) for field, _ in fields):
            # A field name is a Python keyword, so the class syntax cannot be used.
            items = ", ".join(f'"{field}": "{t}"' for field, t in fields)
            self.blocks.append(f'{name} = TypedDict("{name}", {{{items}}})')
            return
        body = "\n".join(f"    {field}: {t}" for field, t in fields) or "    pass"
        self.blocks.append(f"class {name}(TypedDict):\n{body}")


class Payload:
    """The fields of a result or an event, and the TypedDict that has them."""

    def __init__(self, type_name: str, properties: Dict[str, Any]) -> None:
        self.type_name = type_name
        self.fields = [(name, is_optional(spec)) for name, spec in properties.items()]


class Command:
    def __init__(
        self,
        name: str,
        params: List[Tuple[str, str]],
        result: Optional[Payload],
    ) -> None:
        self.name = name
        self.params = params
        self.result = result


class Interface:
    def __init__(self, name: str, extends: Optional[str]) -> None:
        self.name = name
        self.extends = extends
        self.commands: List[Command] = []
        self.events: List[Tuple[str, Optional[Payload]]] = []


def generate_types(protocol: Dict[str, Any]) -> Tuple[str, List[Interface], Set[str]]:
    converter = Converter(protocol)
    emitter = TypesEmitter(protocol)
    interfaces: List[Interface] = []
    aliases: List[str] = []
    channel_names: List[str] = []
    for name, item in protocol.items():
        if item["type"] == "interface":
            channel_names.append(f"{name}Channel")
        elif item["type"] == "enum":
            emitter.names.add(name)
            aliases.append(
                f"{name} = {emitter.py_type(converter.type(item, name), name)}"
            )
    for name, item in protocol.items():
        if item["type"] == "object":
            emitter.emit_class(
                name,
                emitter.fields(
                    name, converter.properties(item.get("properties"), name)
                ),
            )
        if item["type"] != "interface":
            continue
        interface = Interface(name, item.get("extends"))
        interfaces.append(interface)
        if item.get("initializer"):
            initializer = f"{name}Initializer"
            emitter.emit_class(
                initializer,
                emitter.fields(
                    initializer,
                    converter.properties(item["initializer"], f"{name}.initializer"),
                ),
            )
        else:
            # Like upstream: the initializer of the nearest ancestor that has one.
            ancestor = item.get("extends")
            while ancestor and not protocol[ancestor].get("initializer"):
                ancestor = protocol[ancestor].get("extends")
            if ancestor:
                emitter.names.add(f"{name}Initializer")
                emitter.blocks.append(
                    f"class {name}Initializer({ancestor}Initializer):\n    pass"
                )
        for method, command in (item.get("commands") or {}).items():
            command = command or {}
            prefix = f"{name}{title_case(method)}"
            # The params are the arguments of the channel method, so they have
            # no TypedDict of their own. Their nested objects have one.
            params = emitter.fields(
                f"{prefix}Params",
                converter.properties(command.get("parameters"), f"{name}.{method}"),
                sent=True,
                top_level=True,
            )
            returns = converter.properties(command.get("returns"), f"{name}.{method}")
            result = None
            if returns:
                result = Payload(f"{prefix}Result", returns)
                emitter.emit_class(
                    result.type_name,
                    emitter.fields(result.type_name, returns, top_level=True),
                )
            interface.commands.append(Command(method, params, result))
        for event, event_spec in (item.get("events") or {}).items():
            properties = converter.properties(
                (event_spec or {}).get("parameters"), f"{name}.{event}"
            )
            payload = None
            if properties:
                payload = Payload(f"{name}{title_case(event)}Event", properties)
                emitter.emit_class(
                    payload.type_name,
                    emitter.fields(payload.type_name, properties, top_level=True),
                )
            interface.events.append((event, payload))

    body = "\n".join([*aliases, "", "", "\n\n\n".join(emitter.blocks)])
    used_channels = [c for c in sorted(channel_names) if re.search(rf"\b{c}\b", body)]
    text = "\n".join(
        [
            LICENSE,
            TYPES_DOCSTRING,
            "from __future__ import annotations",
            "",
            "from typing import (",
            "    TYPE_CHECKING,",
            "    Any,",
            "    List,",
            "    Literal,",
            "    Optional,",
            "    Sequence,",
            "    TypedDict,",
            ")",
            "",
            "if TYPE_CHECKING:",
            "    from typing_extensions import NotRequired",
            "",
            "    from playwright._impl._channel import Channel",
            "    from playwright._impl._protocol_channels import (",
            *[f"        {channel}," for channel in used_channels],
            "    )",
            "",
            body,
            "",
        ]
    )
    return text, interfaces, emitter.names


def qualify(type_text: str, type_names: Set[str]) -> str:
    """Prefixes the names from _protocol_types.py with `channels.`."""

    def prefix(match: "re.Match[str]") -> str:
        name = match.group(0)
        return f"channels.{name}" if name in type_names else name

    parts = re.split(r'("[^"]*")', type_text)
    for index in range(0, len(parts), 2):
        parts[index] = re.sub(r"\b[A-Za-z_]\w*\b", prefix, parts[index])
    return "".join(parts)


def python_name(name: str) -> str:
    return name + "_" if keyword.iskeyword(name) else name


def payload_dict(payload: Payload, source: str) -> str:
    items = []
    for field, optional in payload.fields:
        value = f'{source}.get("{field}")' if optional else f'{source}["{field}"]'
        items.append(f'"{field}": {value}')
    return "{" + ", ".join(items) + "}"


def generate_channels(interfaces: List[Interface], type_names: Set[str]) -> str:
    blocks: List[str] = []
    for interface in interfaces:
        base = f"{interface.extends}Channel" if interface.extends else "Channel"
        methods: List[str] = []
        for command in interface.commands:
            args = "".join(
                f"        {python_name(field)}: {qualify(field_type, type_names)},\n"
                for field, field_type in command.params
            )
            params = (
                "{"
                + ", ".join(
                    f'"{field}": {python_name(field)}' for field, _ in command.params
                )
                + "}"
            )
            if command.result:
                returns = f"channels.{command.result.type_name}"
                body = (
                    f'        result = await self._call("{command.name}", {params}, timeout)\n'
                    f"        return {payload_dict(command.result, 'result')}"
                )
            else:
                returns = "None"
                body = f'        await self._call("{command.name}", {params}, timeout)'
            methods.append(
                f"    async def {python_name(command.name)}(\n"
                f"        self,\n{args}        timeout: float = 0,\n"
                f"    ) -> {returns}:\n{body}"
            )
        for event, payload in interface.events:
            if payload:
                handler = f"Callable[[channels.{payload.type_name}], Any]"
                listener = f"lambda event: handler({payload_dict(payload, 'event')})"
            else:
                handler = "Callable[[], Any]"
                listener = "lambda event: handler()"
            suffix = title_case(event)
            methods.append(
                f"    def on{suffix}(self, handler: {handler}) -> None:\n"
                f'        self._add_event_listener("{event}", handler, {listener})'
            )
            methods.append(
                f"    def off{suffix}(self, handler: {handler}) -> None:\n"
                f'        self._remove_event_listener("{event}", handler)'
            )
        body = "\n\n".join(methods) or "    pass"
        blocks.append(f"class {interface.name}Channel({base}):\n{body}")
    classes = "\n".join(
        f'    "{interface.name}": {interface.name}Channel,' for interface in interfaces
    )
    code = "\n\n\n".join(blocks)
    typing_names = ["TYPE_CHECKING", "Dict", "Type"] + [
        name
        for name in ["Any", "Callable", "List", "Literal", "Optional", "Sequence"]
        if re.search(rf"\b{name}\[|\b{name}\b(?!\[)", code)
    ]
    return "\n".join(
        [
            LICENSE,
            CHANNELS_DOCSTRING,
            "from __future__ import annotations",
            "",
            f"from typing import {', '.join(sorted(typing_names))}",
            "",
            "from playwright._impl._channel import Channel",
            "",
            "if TYPE_CHECKING:",
            "    from playwright._impl import _protocol_types as channels",
            "",
            "",
            code,
            "",
            "",
            "# The channel class for each protocol type name.",
            "CHANNEL_CLASSES: Dict[str, Type[Channel]] = {",
            classes,
            "}",
            "",
        ]
    )


CHANNELS_DOCSTRING = '''"""Typed channels for the protocol interfaces, generated from packages/protocol/spec.

Like upstream's channels in packages/protocol/src/channels.d.ts: each command is
an async method with the protocol name and parameters, and each event has
on<Event> and off<Event> methods. Every parameter must be passed; an absent
optional parameter is None. The result and the event payloads have every
top-level field; a field that the driver left out is None. `timeout` is the
timeout of the message, in milliseconds; 0 means no timeout.

Generated by scripts/codegen/generate_protocol.py. Do not edit.
"""
'''


TYPES_DOCSTRING = '''"""Types of the protocol messages, generated from packages/protocol/spec.

The names follow upstream's utils/generate_channels.js: <Interface>Initializer,
<Interface><Method>Result and <Interface><Event>Event. The parameters of each
command are the arguments of its method in _protocol_channels.py. An object that
the spec writes inline is named after its owner and field, for example
PageInitializerViewportSize or BrowserNewContextParamsProxy. A reference to
another protocol object has the type <Interface>Channel.

The top-level fields of a result or an event are all present; a field that the
driver left out is None. In the data that the client sends, an optional field of
a nested object also accepts None, except in objects inside arrays, and an array
accepts any sequence. The connection drops None values from objects, but not from
objects inside arrays, before it sends a message.

Generated by scripts/codegen/generate_protocol.py. Do not edit.
"""
'''


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
    parser.add_argument("--out", required=True)
    parser.add_argument("--types-out", required=True)
    parser.add_argument("--channels-out", required=True)
    args = parser.parse_args()
    pw_src_dir = os.environ.get("PW_SRC_DIR")
    if not pw_src_dir:
        raise SystemExit(
            "Set PW_SRC_DIR to a microsoft/playwright checkout at the commit in DRIVER_VERSION (rev=)."
        )
    protocol = load_protocol(Path(pw_src_dir) / "packages" / "protocol" / "spec")
    text = generate(protocol)
    types_text, interfaces, type_names = generate_types(protocol)
    channels_text = generate_channels(interfaces, type_names)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    Path(args.out).write_text(text, encoding="utf-8")
    Path(args.types_out).write_text(types_text, encoding="utf-8")
    Path(args.channels_out).write_text(channels_text, encoding="utf-8")


if __name__ == "__main__":
    main()
