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

"""Port of packages/playwright-core/src/client/jsHandle.ts.

Python: a page function is a string of JavaScript source, never a function. The
calls send isFunction as undefined (None), not as `typeof pageFunction ===
'function'`: the driver then calls the value of the expression when it is a
function, as the Python docs of evaluate() say.

Python: the exposeFunctions option of evaluate() and evaluateHandle() is JavaScript
only (langs: js in the docs). serialize_argument_with_callbacks() is ported, but no
call passes the option, so nothing calls it.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from playwright._impl_v2.channel_owner import (
    ApiCallOptions,
    Channel,
    ChannelOwner,
    from_channel,
)
from playwright._impl_v2.errors import Error, is_target_closed_error
from playwright._impl_v2.protocol.serializers import (
    HandleOrValue,
    parse_serialized_value,
    serialize_value,
)
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.crypto import create_guid

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.element_handle import ElementHandle
    from playwright._impl_v2.page import Page
    from playwright._impl_v2.protocol_channels import JSHandleChannel

# Python: kFunctionBindingPrefix of isomorphic/utilityScriptSerializers.ts.
K_FUNCTION_BINDING_PREFIX = "__pw_fn_"

# Python: the type of an evaluation argument (structs.ts).
Serializable = Any


class JSHandle(ChannelOwner):
    _channel: "JSHandleChannel"

    @staticmethod
    def from_(handle: "JSHandleChannel") -> "JSHandle":
        return from_channel(handle)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.JSHandleInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._preview: str = self._initializer["preview"]

        def on_preview_updated(event: "channels.JSHandlePreviewUpdatedEvent") -> None:
            self._preview = event["preview"]

        self._channel.onPreviewUpdated(on_preview_updated)

    async def evaluate(self, expression: str, arg: Serializable) -> Any:
        # Not ported: assertEvaluateOptions(options), and the exposeFunctions option
        # (JS only), with which the argument is serialize_argument_with_callbacks().
        serialized_arg = serialize_argument(arg)
        result = await self._channel.evaluateExpression(
            expression=expression,
            # Python: undefined; see the module docstring.
            isFunction=None,
            arg=serialized_arg,
            timeout=NO_TIMEOUT,
        )
        return parse_result(result["value"])

    async def evaluate_handle(self, expression: str, arg: Serializable) -> "JSHandle":
        # Not ported: assertEvaluateOptions(options), and the exposeFunctions option
        # (JS only), with which the argument is serialize_argument_with_callbacks().
        serialized_arg = serialize_argument(arg)
        result = await self._channel.evaluateExpressionHandle(
            expression=expression,
            # Python: undefined; see the module docstring.
            isFunction=None,
            arg=serialized_arg,
            timeout=NO_TIMEOUT,
        )
        return JSHandle.from_(result["handle"])

    async def get_property(self, property_name: str) -> "JSHandle":
        result = await self._channel.getProperty(name=property_name, timeout=NO_TIMEOUT)
        return JSHandle.from_(result["handle"])

    async def get_properties(self) -> Dict[str, "JSHandle"]:
        # Python: a dict is the Map; it keeps the order of the names.
        map: Dict[str, JSHandle] = {}
        for prop in (await self._channel.getPropertyList(timeout=NO_TIMEOUT))[
            "properties"
        ]:
            map[prop["name"]] = JSHandle.from_(prop["value"])
        return map

    async def json_value(self) -> Any:
        return parse_result(
            (await self._channel.jsonValue(timeout=NO_TIMEOUT))["value"]
        )

    def as_element(self) -> Optional["ElementHandle"]:
        return None

    # Not ported: [Symbol.asyncDispose](). There is no `await using` in Python.

    async def dispose(self) -> None:
        try:
            await self._channel.dispose(timeout=NO_TIMEOUT)
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e

    def __str__(self) -> str:
        # Python: toString().
        return self._preview

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<JSHandle preview={self._preview}>"


# This function takes care of converting all JSHandles to their channels,
# so that generic channel serializer converts them to guids.
def serialize_argument(
    arg: Serializable,
    register_callback: Optional[Callable[[Callable[..., Any]], str]] = None,
) -> "channels.SerializedArgument":
    handles: List[Channel] = []

    def push_handle(channel: Channel) -> int:
        handles.append(channel)
        return len(handles) - 1

    def handle_serializer(value: Any) -> HandleOrValue:
        if isinstance(value, JSHandle):
            return {"h": push_handle(value._channel)}
        if callable(value) and register_callback:
            return {"fn": register_callback(value)}
        return {"fallThrough": value}

    value = serialize_value(arg, handle_serializer)
    return {"value": value, "handles": handles}


# Not ported: the ExposeFunctionsOptions and EvaluateOptions types. The Python API
# has no exposeFunctions option.


async def serialize_argument_with_callbacks(
    owner: ChannelOwner, page: Optional["Page"], arg: Any
) -> "channels.SerializedArgument":
    async def inner() -> "channels.SerializedArgument":
        expose_promises: List[Awaitable[None]] = []

        def register_callback(callback: Callable[..., Any]) -> str:
            if not page:
                raise Error("Passing a function is not supported as an argument here")
            name = K_FUNCTION_BINDING_PREFIX + create_guid()
            # Python: the coroutine runs as a task, as the JS promise runs.
            expose_promises.append(
                asyncio.ensure_future(page._expose_evaluate_callback(name, callback))
            )
            return name

        serialized = serialize_argument(arg, register_callback)
        await asyncio.gather(*expose_promises)
        return serialized

    return await owner._wrap_api_call(lambda _: inner(), ApiCallOptions(internal=True))


def parse_result(value: "channels.SerializedValue") -> Any:
    return parse_serialized_value(value, None)


def assert_max_arguments(count: int, max: int) -> None:
    # Python: no Python method takes more arguments than its signature has, so no
    # call site passes `arguments.length`; this is kept for the mirror.
    if count > max:
        raise Error(
            "Too many arguments. If you need to pass more than 1 argument to the function wrap them in an object."
        )


def assert_evaluate_options(options: Any) -> None:
    # Python: the Python API has no options object for evaluate(); this is kept for
    # the mirror.
    if options is not None and not isinstance(options, dict):
        raise Error(
            "Too many arguments. If you need to pass more than 1 argument to the function wrap them in an object."
        )
