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

"""Port of packages/playwright-core/src/client/clientStackTrace.ts."""

import os
from typing import List, Optional, TypedDict

import playwright
import playwright._impl._impl_to_api_mapping
from playwright._impl_v2.utils.stack_trace import (
    StackFrame,
    capture_raw_stack,
    core_dir,
    filter_stack_file,
    frame_function_name,
)


class LibraryStackTrace(TypedDict):
    frames: List[StackFrame]
    apiName: str


# Python: the glue that maps the impl objects of an event to the API objects.
_MAPPING_FILE = playwright._impl._impl_to_api_mapping.__file__
# Python: the generated API, which the user code calls.
_GENERATED_API_FILES = {
    os.path.join(os.path.dirname(playwright.__file__), flavor, "_generated.py")
    for flavor in ("async_api", "sync_api")
}


def capture_library_stack_trace() -> LibraryStackTrace:
    stack = capture_raw_stack()
    playwright_core_dir = core_dir() or ""

    # Python: the parsed frames are the frame objects with a file; the function
    # name of a frame is read only for the frames that are kept, because reading
    # the locals of every frame on every API call is slow.
    parsed_frames = [
        raw
        for raw in stack
        if raw.f_code.co_filename and raw.f_code.co_filename != _MAPPING_FILE
    ]
    is_playwright_library = [
        bool(playwright_core_dir)
        and raw.f_code.co_filename.startswith(playwright_core_dir)
        for raw in parsed_frames
    ]

    api_name = ""

    # Deepest transition between non-client code calling into client
    # code is the api entry.
    for i in range(len(parsed_frames) - 1):
        if is_playwright_library[i] and not is_playwright_library[i + 1]:
            api_name = api_name or normalize_api_name(
                frame_function_name(parsed_frames[i])
            )
            break

    # Python: a coroutine of the API that runs in a task of its own (create_task(),
    # gather()) has no frame of the code that called it, because it starts when the
    # event loop runs it; a JS async function starts at once, in the caller's stack.
    # Then the outermost frame of the generated API names the call.
    if not api_name:
        for raw in reversed(parsed_frames):
            if raw.f_code.co_filename in _GENERATED_API_FILES:
                api_name = normalize_api_name(frame_function_name(raw))
                break

    # This is for the inspector so that it did not include the test runner stack frames.
    frames: List[StackFrame] = [
        {
            "file": raw.f_code.co_filename,
            "line": raw.f_lineno,
            "column": 0,
            "function": frame_function_name(raw),
        }
        for raw in parsed_frames
        if filter_stack_file(raw.f_code.co_filename)
    ]

    return {
        "frames": frames,
        "apiName": api_name,
    }


def normalize_api_name(name: Optional[str]) -> str:
    # Python: the API names keep the Python class names (Page.goto, not page.goto).
    if not name:
        return ""
    return name
