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

from typing import List, Union
import os
import mimetypes
import base64

from playwright.helper import FilePayload


def normalize_file_payloads(
    files: Union[str, FilePayload, List[Union[str, FilePayload]]]
) -> List[FilePayload]:
    ff: List[Union[str, FilePayload]] = []
    if not isinstance(files, list):
        ff = [files]
    else:
        ff = files
    file_payloads: List[FilePayload] = []
    for item in ff:
        if isinstance(item, str):
            with open(item, mode="rb") as fd:
                file: FilePayload = {
                    "name": os.path.basename(item),
                    "mimeType": mimetypes.guess_type(item)[0]
                    or "application/octet-stream",
                    "buffer": base64.b64encode(fd.read()).decode(),
                }
                file_payloads.append(file)
        else:
            if isinstance(item["buffer"], bytes):
                item["buffer"] = base64.b64encode(item["buffer"]).decode()
            file_payloads.append(item)

    return file_payloads
