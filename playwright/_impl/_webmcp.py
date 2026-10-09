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

from typing import TYPE_CHECKING, Any, List

from playwright._impl._api_structures import WebMCPTool
from playwright._impl._helper import locals_to_params
from playwright._impl._js_handle import Serializable, parse_result, serialize_argument

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._frame import Frame


class WebMCP:
    def __init__(self, frame: "Frame") -> None:
        self._frame = frame
        self._loop = frame._loop
        self._dispatcher_fiber = frame._dispatcher_fiber

    async def tools(self, timeout: float = None) -> List[WebMCPTool]:
        return await self._frame._channel.send(
            "webmcpTools", self._frame._timeout, locals_to_params(locals())
        )

    async def call_tool(
        self, name: str, input: Serializable = None, timeout: float = None
    ) -> Any:
        result = await self._frame._channel.send(
            "webmcpCallTool",
            self._frame._timeout,
            {"name": name, "input": serialize_argument(input), "timeout": timeout},
        )
        return parse_result(result)
