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

"""Port of packages/playwright-core/src/client/consoleMessage.ts.

Python: the getters are properties, as the generated API reads them. The
util.inspect.custom hook of Node.js is not ported; __str__() is its Python
counterpart. The object keeps the event loop, as the generated API reads the loop
of each object.
"""

from typing import TYPE_CHECKING, List, Literal, Optional, Union, cast

from playwright._impl._api_structures import SourceLocation
from playwright._impl.js_handle import JSHandle

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import protocol_types as channels
    from playwright._impl.channel_owner import ChannelOwner
    from playwright._impl.page import Page
    from playwright._impl.worker import Worker

# Python: ReturnType<api.ConsoleMessage['type']>.
ConsoleMessageType = Literal[
    "assert",
    "clear",
    "count",
    "debug",
    "dir",
    "dirxml",
    "endGroup",
    "error",
    "info",
    "log",
    "profile",
    "profileEnd",
    "startGroup",
    "startGroupCollapsed",
    "table",
    "time",
    "timeEnd",
    "trace",
    "warning",
]

# Python: the result of Page.consoleMessages() has the fields of the event, too.
ConsoleMessageEvent = Union[
    "channels.BrowserContextConsoleEvent",
    "channels.WorkerConsoleEvent",
    "channels.ElectronApplicationConsoleEvent",
    "channels.PageConsoleMessagesResultMessages",
]


class ConsoleMessage:
    def __init__(
        self,
        event: ConsoleMessageEvent,
        page: Optional["Page"],
        worker: Optional["Worker"],
        parent: "ChannelOwner",
    ) -> None:
        self._page = page
        self._worker = worker
        self._event = event
        # Not ported: the util.inspect.custom hook. Python: __str__() below.
        # Python: the generated API reads the event loop and the dispatcher fiber of
        # each object. The parent is the page, worker or context that creates the
        # message; the page and the worker may be None.
        self._loop = parent._loop
        self._dispatcher_fiber = parent._dispatcher_fiber

    @property
    def worker(self) -> Optional["Worker"]:
        return self._worker

    @property
    def page(self) -> Optional["Page"]:
        return self._page

    @property
    def type(self) -> ConsoleMessageType:
        return cast(ConsoleMessageType, self._event["type"])

    @property
    def text(self) -> str:
        return self._event["text"]

    @property
    def args(self) -> List[JSHandle]:
        return [JSHandle.from_(arg) for arg in self._event["args"]]

    @property
    def location(self) -> SourceLocation:
        location = self._event["location"]
        url = location["url"]
        line_number = location["lineNumber"]
        column_number = location["columnNumber"]
        return {
            "url": url,
            "line": line_number,
            "column": column_number,
            "lineNumber": line_number,
            "columnNumber": column_number,
        }

    @property
    def timestamp(self) -> float:
        return self._event["timestamp"]

    def _inspect(self) -> str:
        return self.text

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<ConsoleMessage type={self.type} text={self.text}>"

    def __str__(self) -> str:
        # Python: what util.inspect.custom gives upstream.
        return self._inspect()
