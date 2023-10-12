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

    total_buffer_size_exceeds_limit = (
        sum(
            [
                len(f.get("buffer", ""))
                for f in file_list
                if not isinstance(f, (str, Path))
            ]
        )
        > SIZE_LIMIT_IN_BYTES
    )
    if total_buffer_size_exceeds_limit:
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )

    total_file_size_exceeds_limit = (
        sum([os.stat(f).st_size for f in file_list if isinstance(f, (str, Path))])
        > SIZE_LIMIT_IN_BYTES
    )
    if total_file_size_exceeds_limit:
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
