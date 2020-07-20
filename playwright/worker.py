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

from types import SimpleNamespace
from typing import Any, Dict

from playwright.connection import ChannelOwner, ConnectionScope, from_channel
from playwright.helper import is_function_body
from playwright.js_handle import JSHandle, parse_result, serialize_argument


class Worker(ChannelOwner):
    Events = SimpleNamespace(Close="close")

    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)
        self._channel.on("close", lambda _: self._on_close())

    def _on_close(self) -> None:
        if self._page:
            self._page._workers.remove(self)
        self.emit(Worker.Events.Close, self)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def evaluate(
        self, expression: str, arg: Any = None, force_expr: bool = False
    ) -> Any:
        if not is_function_body(expression):
            force_expr = True
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluateHandle(
        self, expression: str, arg: Any = None, force_expr: bool = False
    ) -> JSHandle:
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    isFunction=not (force_expr),
                    arg=serialize_argument(arg),
                ),
            )
        )
