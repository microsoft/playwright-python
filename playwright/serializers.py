from typing import Any, Awaitable, Dict, List, Optional, Union, TYPE_CHECKING
from playwright.helper import (
    ConsoleMessageLocation,
    FilePayload,
    SelectOption,
    is_function_body,
    locals_to_params,
)
from os import path
import mimetypes
import base64


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
                    "name": path.basename(item),
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
