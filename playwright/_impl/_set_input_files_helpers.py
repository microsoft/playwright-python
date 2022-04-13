import base64
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import TypedDict
else:  # pragma: no cover
    from typing_extensions import TypedDict

from playwright._impl._connection import Channel, from_channel
from playwright._impl._helper import Error, async_readfile
from playwright._impl._writable_stream import WritableStream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext

from playwright._impl._api_structures import FilePayload

SIZE_LIMIT_IN_BYTES = 50 * 1024 * 1024


class InputFilesList(TypedDict):
    streams: Optional[List[Channel]]
    localPaths: Optional[List[str]]
    files: Optional[List[FilePayload]]


async def convert_input_files(
    files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]],
    context: "BrowserContext",
) -> InputFilesList:
    file_list = files if isinstance(files, list) else [files]

    has_large_buffer = any(
        [
            len(f.get("buffer", "")) > SIZE_LIMIT_IN_BYTES
            for f in file_list
            if not isinstance(f, (str, Path))
        ]
    )
    if has_large_buffer:
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )

    has_large_file = any(
        [
            os.stat(f).st_size > SIZE_LIMIT_IN_BYTES
            for f in file_list
            if isinstance(f, (str, Path))
        ]
    )
    if has_large_file:
        if context._channel._connection.is_remote:
            streams = []
            for file in file_list:
                assert isinstance(file, (str, Path))
                stream: WritableStream = from_channel(
                    await context._channel.send(
                        "createTempFile", {"name": os.path.basename(file)}
                    )
                )
                await stream.copy(file)
                streams.append(stream._channel)
            return InputFilesList(streams=streams, localPaths=None, files=None)
        local_paths = []
        for p in file_list:
            assert isinstance(p, (str, Path))
            local_paths.append(str(Path(p).absolute().resolve()))
        return InputFilesList(streams=None, localPaths=local_paths, files=None)

    return InputFilesList(
        streams=None, localPaths=None, files=await _normalize_file_payloads(files)
    )


async def _normalize_file_payloads(
    files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]]
) -> List:
    file_list = files if isinstance(files, list) else [files]
    file_payloads: List = []
    for item in file_list:
        if isinstance(item, (str, Path)):
            file_payloads.append(
                {
                    "name": os.path.basename(item),
                    "buffer": base64.b64encode(await async_readfile(item)).decode(),
                }
            )
        else:
            file_payloads.append(
                {
                    "name": item["name"],
                    "mimeType": item["mimeType"],
                    "buffer": base64.b64encode(item["buffer"]).decode(),
                }
            )

    return file_payloads
