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

"""Port of packages/playwright-core/src/client/disposable.ts.

Python: the Disposable interface is a base class, and it is the impl class of the
public Disposable: the generated API wraps a DisposableObject and a DisposableStub
alike in its Disposable class (see Disposable._api_impl_class). That class is an
async context manager: `async with` calls close(), as `await using` calls
[Symbol.asyncDispose](), so [Symbol.asyncDispose]() is not ported.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional

from playwright._impl_v2.channel_owner import ChannelOwner, from_channel
from playwright._impl_v2.errors import is_target_closed_error
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.protocol_channels import DisposableChannel


class Disposable:
    # Python: the interface is a base class, so that the generated API can name it.
    async def dispose(self) -> None:
        raise NotImplementedError

    # Python only: the members of the Python API that upstream does not have.

    @property
    def _api_impl_class(self) -> type:
        # Python: the generated API registers this class for its Disposable class;
        # DisposableObject and DisposableStub are both Disposable in the API.
        return Disposable

    async def close(self) -> None:
        await self.dispose()


class DisposableObject(ChannelOwner, Disposable):
    _channel: "DisposableChannel"

    @staticmethod
    def from_(channel: "DisposableChannel") -> "DisposableObject":
        return from_channel(channel)

    # Not ported: [Symbol.asyncDispose](). Python: Disposable.close().

    async def dispose(self) -> None:
        try:
            await self._channel.dispose(timeout=NO_TIMEOUT)
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e


class DisposableStub(Disposable):
    def __init__(self, dispose: Callable[[], Awaitable[Any]]) -> None:
        self._dispose: Optional[Callable[[], Awaitable[Any]]] = dispose
        # Python: the generated API reads the event loop of each object. A stub is
        # created in an API call, so the loop is running.
        self._loop = asyncio.get_running_loop()

    # Not ported: [Symbol.asyncDispose](). Python: Disposable.close().

    async def dispose(self) -> None:
        if not self._dispose:
            return
        try:
            dispose = self._dispose
            self._dispose = None
            await dispose()
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e


async def dispose_all(disposables: List[Disposable]) -> None:
    copy = list(disposables)
    disposables.clear()
    await asyncio.gather(*[d.dispose() for d in copy])
