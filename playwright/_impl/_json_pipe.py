from types import SimpleNamespace
from typing import Dict

from playwright._impl._connection import ChannelOwner
from playwright._impl._helper import locals_to_params


class JsonPipe(ChannelOwner):
    Events = SimpleNamespace(
        Message="message",
        Closed="closed",
    )

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: Dict,
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on(
            JsonPipe.Events.Message,
            lambda msg: self.emit(JsonPipe.Events.Message, msg["message"]),
        )
        self._channel.on(
            JsonPipe.Events.Closed, lambda _: self.emit(JsonPipe.Events.Closed)
        )

    async def send(self, message: Dict) -> None:
        await self._channel.send("send", locals_to_params(locals()))

    async def close(self) -> None:
        await self._channel.send("close")
