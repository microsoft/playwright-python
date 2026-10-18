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

from typing import Dict, cast

from playwright._impl._artifact import Artifact
from playwright._impl._browser import Browser
from playwright._impl._browser_context import BrowserContext
from playwright._impl._browser_type import BrowserType
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import (
    ChannelOwner,
    ChannelOwnerFactory,
    DummyChannelOwner,
)
from playwright._impl._debugger import Debugger
from playwright._impl._dialog import Dialog
from playwright._impl._disposable import Disposable
from playwright._impl._element_handle import ElementHandle
from playwright._impl._fetch import APIRequestContext
from playwright._impl._frame import Frame
from playwright._impl._js_handle import JSHandle
from playwright._impl._json_pipe import JsonPipe
from playwright._impl._local_utils import LocalUtils
from playwright._impl._network import (
    Request,
    Response,
    Route,
    WebSocket,
    WebSocketRoute,
)
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._playwright import Playwright
from playwright._impl._stream import Stream
from playwright._impl._tracing import Tracing
from playwright._impl._writable_stream import WritableStream


def _create_local_utils(
    parent: ChannelOwner, type: str, guid: str, initializer: Dict
) -> ChannelOwner:
    result = LocalUtils(parent, type, guid, initializer)
    if not result._connection._local_utils:
        result._connection._local_utils = result
    return result


# The object factories that the Connection constructor in client/connection.ts
# registers. Android and Electron are not in the Python API.
object_factories: Dict[str, ChannelOwnerFactory] = {
    "Android": DummyChannelOwner,
    "AndroidDevice": DummyChannelOwner,
    "AndroidSocket": DummyChannelOwner,
    "APIRequestContext": APIRequestContext,
    "Artifact": Artifact,
    "BindingCall": BindingCall,
    "Browser": lambda parent, type, guid, initializer: Browser(
        cast(BrowserType, parent), type, guid, initializer
    ),
    "BrowserContext": BrowserContext,
    "BrowserType": BrowserType,
    "CDPSession": CDPSession,
    "Debugger": Debugger,
    "Dialog": Dialog,
    "Disposable": Disposable,
    "Electron": DummyChannelOwner,
    "ElectronApplication": DummyChannelOwner,
    "ElementHandle": ElementHandle,
    "Frame": Frame,
    "JSHandle": JSHandle,
    "JsonPipe": JsonPipe,
    "LocalUtils": _create_local_utils,
    "Page": Page,
    "Playwright": Playwright,
    "Request": Request,
    "Response": Response,
    "Route": Route,
    "Stream": Stream,
    "SocksSupport": DummyChannelOwner,
    "Tracing": Tracing,
    "WebSocket": WebSocket,
    "WebSocketRoute": WebSocketRoute,
    "Worker": Worker,
    "WritableStream": WritableStream,
}
