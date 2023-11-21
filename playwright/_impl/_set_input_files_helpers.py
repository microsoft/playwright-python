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
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import TypedDict
else:  # pragma: no cover
    from typing_extensions import TypedDict

from playwright._impl._connection import Channel, from_channel
from playwright._impl._helper import Error
from playwright._impl._writable_stream import WritableStream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext

from playwright._impl._api_structures import FilePayload

SIZE_LIMIT_IN_BYTES = 50 * 1024 * 1024


class InputFilesList(TypedDict, total=False):
    streams: Optional[List[Channel]]
    localPaths: Optional[List[str]]
    payloads: Optional[List[Dict[str, Union[str, bytes]]]]


async def convert_input_files(
    files: Union[str, Path, FilePayload, List[Union[str, Path]], List[FilePayload]],
    context: "BrowserContext",
) -> InputFilesList:
    items = files if isinstance(files, list) else [files]

    if any([isinstance(item, (str, Path)) for item in items]):
        if not all([isinstance(item, (str, Path)) for item in items]):
            raise Error("File paths cannot be mixed with buffers")
        if context._channel._connection.is_remote:
            streams = []
            for item in items:
                assert isinstance(item, (str, Path))
                last_modified_ms = int(os.path.getmtime(item) * 1000)
                stream: WritableStream = from_channel(
                    await context._channel.send(
                        "createTempFile",
                        {
                            "name": os.path.basename(item),
                            "lastModifiedMs": last_modified_ms,
                        },
                    )
                )
                await stream.copy(item)
                streams.append(stream._channel)
            return InputFilesList(streams=streams)
        return InputFilesList(
            localPaths=[
                str(Path(cast(Union[str, Path], item)).absolute().resolve())
                for item in items
            ]
        )

    file_payload_exceeds_size_limit = (
        sum([len(f.get("buffer", "")) for f in items if not isinstance(f, (str, Path))])
        > SIZE_LIMIT_IN_BYTES
    )
    if file_payload_exceeds_size_limit:
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )

    return InputFilesList(
        payloads=[
            {
                "name": item["name"],
                "mimeType": item["mimeType"],
                "buffer": base64.b64encode(item["buffer"]).decode(),
            }
            for item in cast(List[FilePayload], items)
        ]
    )
