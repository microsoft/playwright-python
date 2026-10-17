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

"""Reads a trace zip, for the tracing tests in both flavors.

parse_trace_raw() is a port of parseTraceRaw() in tests/config/utils.ts. The action
titles come from the driver's own renderFullTitleForCall() (iso in coreBundle.js), as
upstream renders them, with the JavaScript locator syntax.
"""

import json
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Union

from playwright._impl._driver import compute_driver_executable

_RENDER_TITLES_SCRIPT = """
const { iso } = require(process.argv[1]);
let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const calls = JSON.parse(input);
  const titles = calls.map(call => iso.renderFullTitleForCall({ ...call, type: call.class }));
  process.stdout.write(JSON.stringify(titles));
});
"""


@dataclass
class ParsedTrace:
    events: List[Dict[str, Any]]
    resources: Dict[str, bytes]
    actions: List[str]
    action_objects: List[Dict[str, Any]]
    stacks: Dict[str, List[Dict[str, Any]]]


def render_titles(calls: List[Dict[str, Any]]) -> List[str]:
    """Renders the action titles like iso.renderFullTitleForCall() does."""
    if not calls:
        return []
    node, cli = compute_driver_executable()
    core_bundle = Path(cli).parent / "lib" / "coreBundle.js"
    result = subprocess.run(
        [node, "-e", _RENDER_TITLES_SCRIPT, str(core_bundle)],
        input=json.dumps(calls).encode(),
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def _lines(data: bytes) -> List[str]:
    return [line for line in data.decode().split("\n") if line]


def parse_trace_raw(path: Union[str, Path]) -> ParsedTrace:
    """Port of parseTraceRaw() in tests/config/utils.ts."""
    with zipfile.ZipFile(path) as zip_file:
        resources = {name: zip_file.read(name) for name in zip_file.namelist()}

    action_map: Dict[str, Dict[str, Any]] = {}
    events: List[Dict[str, Any]] = []
    for trace_file in [name for name in resources if name.endswith(".trace")]:
        for line in _lines(resources[trace_file]):
            event = json.loads(line)
            events.append(event)
            if event["type"] == "before":
                action_map[event["callId"]] = {**event, "type": "action", "endTime": 0}
            elif event["type"] == "input":
                action_map[event["callId"]]["point"] = event.get("point")
            elif event["type"] == "after":
                existing = action_map[event["callId"]]
                existing["endTime"] = event.get("endTime")
                existing["error"] = event.get("error")
                existing["result"] = event.get("result")

    for network_file in [name for name in resources if name.endswith(".network")]:
        for line in _lines(resources[network_file]):
            events.append(json.loads(line))

    stacks: Dict[str, List[Dict[str, Any]]] = {}
    for stacks_file in [name for name in resources if name.endswith(".stacks")]:
        # Port of parseClientSideCallMetadata() in packages/isomorphic/trace/traceUtils.ts.
        data = json.loads(resources[stacks_file])
        files = data["files"]
        for call_id, frames in data["stacks"]:
            stacks[call_id] = [
                {"file": files[f[0]], "line": f[1], "column": f[2], "function": f[3]}
                for f in frames
            ]

    action_objects = sorted(action_map.values(), key=lambda a: a["startTime"])
    return ParsedTrace(
        events=events,
        resources=resources,
        actions=render_titles(action_objects),
        action_objects=action_objects,
        stacks=stacks,
    )
