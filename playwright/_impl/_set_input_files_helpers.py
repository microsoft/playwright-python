import base64
import os
import shutil
from pathlib import Path
from posixpath import basename
from typing import TYPE_CHECKING, List, Union

from playwright._impl._helper import Error, async_readfile
from playwright._impl._writeable_stream import WriteableStream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext

from playwright._impl._api_structures import FilePayload

SIZE_LIMIT_IN_BYTES = 50 * 1024 * 1024


async def convert_input_files(
    files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]],
    context: "BrowserContext",
):
    files = files if isinstance(files, list) else [files]

    has_large_buffer = list(
        filter(
            lambda f: not isinstance(f, (str, Path))
            and len(f.get("buffer", "")) > SIZE_LIMIT_IN_BYTES,
            files,
        )
    )
    if has_large_buffer:
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )

    has_large_file = list(
        map(
            lambda f: os.stat(f).st_size,
            filter(lambda f: isinstance(f, (str, Path)), files),
        )
    )
    if has_large_file:
        if context._channel._connection.is_remote:
            streams = []
            for file in files:
                stream: WriteableStream = await context._channel.send(
                    "createTempFile", {"name": os.path.basename(file)}
                )
                await WriteableStream.copy(file, stream)
                streams.append(stream)
            return {"streams": streams}
        return {"localPaths": list(map(lambda f: Path(f).absolute().resolve(), files))}

    return {"files": await normalize_file_payloads(files)}


async def normalize_file_payloads(
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
