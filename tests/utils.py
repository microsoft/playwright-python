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
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypeVar


def parse_trace(path: Path) -> Tuple[Dict[str, bytes], List[Any]]:
    resources: Dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as zip:
        for name in zip.namelist():
            resources[name] = zip.read(name)
    action_map: Dict[str, Any] = {}
    events: List[Any] = []
    for name in ["trace.trace", "trace.network"]:
        for line in resources[name].decode().splitlines():
            if not line:
                continue
            event = json.loads(line)
            if event["type"] == "before":
                event["type"] = "action"
                action_map[event["callId"]] = event
                events.append(event)
            elif event["type"] == "input":
                pass
            elif event["type"] == "after":
                existing = action_map[event["callId"]]
                existing["error"] = event.get("error", None)
            else:
                events.append(event)
    return (resources, events)


def get_trace_actions(events: List[Any]) -> List[str]:
    action_events = sorted(
        list(
            filter(
                lambda e: e["type"] == "action",
                events,
            )
        ),
        key=lambda e: e["startTime"],
    )
    return [e["apiName"] for e in action_events]


TARGET_CLOSED_ERROR_MESSAGE = "Target page, context or browser has been closed"

MustType = TypeVar("MustType")


def must(value: Optional[MustType]) -> MustType:
    assert value
    return value


def chromium_version_less_than(a: str, b: str) -> bool:
    left = list(map(int, a.split(".")))
    right = list(map(int, b.split(".")))
    for i in range(4):
        if left[i] > right[i]:
            return False
        if left[i] < right[i]:
            return True
    return False
