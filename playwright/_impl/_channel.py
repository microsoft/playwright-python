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

"""Port of the channel proxy in packages/playwright-core/src/client/channelOwner.ts."""

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Mapping, Optional, Tuple

from pyee.asyncio import AsyncIOEventEmitter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._connection import ChannelOwner, Connection


class Channel:
    """The base of the generated channels in _protocol_channels.py."""

    def __init__(self, connection: "Connection", object: "ChannelOwner") -> None:
        self._connection = connection
        self._guid = object._guid
        self._object = object
        self._emitter = AsyncIOEventEmitter()
        self._emitter.on(
            "error", lambda exc: self._connection._on_event_listener_error(exc)
        )
        # (event, handler) -> the wrappers registered for it, in order.
        self._event_listeners: Dict[Tuple[str, Any], List[Callable[[Any], Any]]] = {}

    async def _call(
        self, method: str, params: Mapping[str, Any], timeout: float
    ) -> Dict[str, Any]:
        """Sends a command and returns its result, {} when it has none."""
        result = await self._connection.wrap_api_call(
            lambda: self._inner_send(method, _filter_none(params), timeout)
        )
        return result or {}

    def _add_event_listener(
        self, event: str, handler: Any, listener: Callable[[Any], Any]
    ) -> None:
        """Registers listener, the wrapper that calls handler with the typed payload.

        A handler can be registered more than once, like on an EventEmitter;
        each off<Event> call removes one registration.
        """
        self._event_listeners.setdefault((event, handler), []).append(listener)
        self._emitter.on(event, listener)

    def _remove_event_listener(self, event: str, handler: Any) -> None:
        listeners = self._event_listeners.get((event, handler))
        if not listeners:
            return
        listener = listeners.pop()
        if not listeners:
            del self._event_listeners[(event, handler)]
        self._emitter.remove_listener(event, listener)

    def send_no_reply(
        self,
        method: str,
        params: Mapping[str, Any] = None,
        is_internal: bool = False,
        title: str = None,
    ) -> None:
        """Sends a message without waiting for the reply.

        For messages that must go out synchronously, such as __waitInfo__ and
        updateSubscription.
        """
        self._connection.wrap_api_call_sync(
            lambda: self._connection._send_message_to_server(
                self._object, method, _filter_none(params or {}), 0, True
            ),
            is_internal,
            title,
        )

    async def _inner_send(
        self, method: str, params: Dict[str, Any], timeout: float
    ) -> Optional[Dict[str, Any]]:
        if self._connection._error:
            error = self._connection._error
            self._connection._error = None
            raise error
        callback = self._connection._send_message_to_server(
            self._object, method, params, timeout
        )
        try:
            done, _ = await asyncio.wait(
                {
                    self._connection._transport.on_error_future,
                    callback.future,
                },
                return_when=asyncio.FIRST_COMPLETED,
            )
        except asyncio.CancelledError as exc:
            await self._connection._abort(
                self._object,
                callback,
                str(exc) or "Task was cancelled",
            )
            raise
        if not callback.future.done():
            callback.future.cancel()
        result = next(iter(done)).result()
        if not result:
            return None
        assert isinstance(result, dict)
        return result


def _filter_none(d: Mapping) -> Dict:
    result = {}
    for k, v in d.items():
        if v is None:
            continue
        result[k] = _filter_none(v) if isinstance(v, dict) else v
    return result
