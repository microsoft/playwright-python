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

from playwright.connection import ChannelOwner, ConnectionScope, from_channel
from playwright.js_handle import JSHandle, parse_result, serialize_argument
from typing import Any, Dict


class Worker(ChannelOwner):
    def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
        super().__init__(scope, guid, initializer)

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def evaluate(
        self, expression: str, arg: Any = None, force_expr: bool = False
    ) -> Any:
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
