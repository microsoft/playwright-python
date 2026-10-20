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

"""Port of packages/playwright-core/src/client/webmcp.ts.

Python: WebMCP is not a ChannelOwner, so it keeps the event loop of its frame for the
generated API. The WebMCPTool type is the TypedDict of the Python API,
playwright/_impl/_api_structures.py.
"""

from typing import TYPE_CHECKING, Any, List, Optional, cast

from playwright._impl._api_structures import WebMCPTool
from playwright._impl_v2.js_handle import parse_result, serialize_argument

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.frame import Frame


class WebMCP:
    def __init__(self, frame: "Frame") -> None:
        self._frame = frame
        # Python: the generated API reads the event loop and the dispatcher fiber of
        # each object.
        self._loop = frame._loop
        self._dispatcher_fiber = frame._dispatcher_fiber

    async def tools(self, timeout: Optional[float]) -> List[WebMCPTool]:
        tools = (
            await self._frame._channel.webmcpTools(
                timeout=self._frame._timeout(timeout)
            )
        )["tools"]
        return cast(List[WebMCPTool], tools)

    async def call_tool(self, name: str, input: Any, timeout: Optional[float]) -> Any:
        result = (
            await self._frame._channel.webmcpCallTool(
                name=name,
                input=serialize_argument(input),
                timeout=self._frame._timeout(timeout),
            )
        )["result"]
        return parse_result(result)
