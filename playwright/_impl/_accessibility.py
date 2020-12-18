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

from typing import Dict, Optional

from playwright._impl._connection import Channel
from playwright._impl._element_handle import ElementHandle
from playwright._impl._helper import locals_to_params


def _ax_node_from_protocol(axNode: Dict) -> Dict:
    result = {**axNode}
    if "valueNumber" in axNode:
        result["value"] = axNode["valueNumber"]
    elif "valueString" in axNode:
        result["value"] = axNode["valueString"]

    if "checked" in axNode:
        result["checked"] = (
            True
            if axNode.get("checked") == "checked"
            else (
                False if axNode.get("checked") == "unchecked" else axNode.get("checked")
            )
        )

    if "pressed" in axNode:
        result["pressed"] = (
            True
            if axNode.get("pressed") == "pressed"
            else (
                False if axNode.get("pressed") == "released" else axNode.get("pressed")
            )
        )

    if axNode.get("children"):
        result["children"] = list(map(_ax_node_from_protocol, axNode["children"]))
    if "valueNumber" in result:
        del result["valueNumber"]
    if "valueString" in result:
        del result["valueString"]
    return result


class Accessibility:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def snapshot(
        self, interestingOnly: bool = None, root: ElementHandle = None
    ) -> Optional[Dict]:
        params = locals_to_params(locals())
        if root:
            params["root"] = root._channel
        result = await self._channel.send("accessibilitySnapshot", params)
        return _ax_node_from_protocol(result) if result else None
