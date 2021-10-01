from typing import Dict

from ._connection import ChannelOwner
from ._helper import locals_to_params


class JsonPipe(ChannelOwner):
    def __init__(
        self, parent: "ChannelOwner", type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.on("message", lambda msg: self.emit("message", msg["message"]))
        self._channel.on("closed", lambda _: self.emit("closed"))

    async def send(self, message: Dict) -> None:
        await self._channel.send("send", locals_to_params(locals()))

    async def close(self) -> None:
        await self._channel.send("close")
