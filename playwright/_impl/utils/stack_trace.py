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

"""Port of the parts of packages/utils/stackTrace.ts that the client uses.

Python: a stack is a chain of frame objects, not text, so there is no
parseStackFrame(), and a frame has no column.
"""

import asyncio
import copy
import functools
import os
import site
import sys
import sysconfig
from types import FrameType
from typing import List, Optional, Tuple, TypedDict

import playwright
from playwright._impl.errors import Error
from playwright._impl.utils.debug import get_as_boolean_from_env


class StackFrame(TypedDict, total=False):
    file: str
    line: int
    column: int
    function: str


# Python: the frames of the stack, the innermost first, as the lines of error.stack.
RawStack = List[FrameType]

# The event loop runs each task step and callback from Handle._run(). The frames below
# it run the event loop and did not call the task, as in the Node.js event loop.
_EVENT_LOOP_CALLBACK_CODE = asyncio.events.Handle._run.__code__


def capture_raw_stack() -> RawStack:
    stack: RawStack = []
    frame: Optional[FrameType] = sys._getframe(1)
    while frame and len(stack) < 50:
        if frame.f_code is _EVENT_LOOP_CALLBACK_CODE:
            # Python: under the sync API the call runs in a task of the dispatcher
            # fiber, and the frames of the user code are in the greenlet of the
            # sync call, suspended; the task points to them (_sync_base.py).
            frame = _sync_caller_frame()
            continue
        stack.append(frame)
        frame = frame.f_back
    return stack


def _sync_caller_frame() -> Optional[FrameType]:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return None
    return getattr(task, "__pw_caller_frame__", None)


def rewrite_error_message(e: Exception, new_message: str) -> Exception:
    """Port of rewriteErrorMessage().

    Python: upstream changes the error itself; this changes a copy, because the same
    error can fail several calls (the closed error of a connection), and each call
    adds its prefix. An exception that formats its message from other fields
    (OSError, KeyError) keeps its message.
    """
    try:
        rewritten = copy.copy(e)
    except Exception:
        rewritten = e
    if isinstance(rewritten, Error):
        rewritten._message = new_message
        rewritten.args = (new_message,)
    elif len(rewritten.args) <= 1 and type(rewritten).__str__ is BaseException.__str__:
        rewritten.args = (new_message,)
    return rewritten.with_traceback(e.__traceback__)


def stringify_stack_frames(frames: List[StackFrame]) -> List[str]:
    stack_lines: List[str] = []
    for frame in frames:
        if frame.get("function"):
            stack_lines.append(
                f"    at {frame['function']} ({frame['file']}:{frame['line']}:{frame['column']})"
            )
        else:
            stack_lines.append(
                f"    at {frame['file']}:{frame['line']}:{frame['column']}"
            )
    return stack_lines


def _non_user_code_dirs() -> Tuple[str, ...]:
    # Python: the directories of the standard library and of the installed packages
    # (pytest, pluggy, ...), the counterpart of the Node.js internals and the
    # boxed stack prefixes of the test runner.
    paths = sysconfig.get_paths()
    dirs = {
        paths.get(name)
        for name in ("stdlib", "platstdlib", "purelib", "platlib", "scripts")
    }
    if hasattr(site, "getsitepackages"):
        dirs.update(site.getsitepackages())
    if hasattr(site, "getusersitepackages"):
        dirs.add(site.getusersitepackages())
    dirs.update(
        entry
        for entry in sys.path
        if os.path.basename(entry) in ("site-packages", "dist-packages")
    )
    result = set()
    for dir in dirs:
        if not dir:
            continue
        for variant in (dir, os.path.realpath(dir)):
            result.add(os.path.join(os.path.normcase(os.path.abspath(variant)), ""))
    return tuple(result)


_NON_USER_CODE_DIRS = _non_user_code_dirs()


@functools.lru_cache(maxsize=None)
def filter_stack_file(file: str) -> bool:
    if _show_internal_stack_frames:
        return True
    if _core_dir and file.startswith(_core_dir):
        return False
    # Python: code without a source file, such as frozen modules of the standard
    # library (runpy, importlib) and code that exec() runs.
    if file.startswith("<") and file.endswith(">"):
        return False
    if os.path.normcase(file).startswith(_NON_USER_CODE_DIRS):
        return False
    return True


def filtered_stack_trace(raw_stack: RawStack) -> List[StackFrame]:
    frames: List[StackFrame] = []
    for frame in raw_stack:
        file = frame.f_code.co_filename
        if not filter_stack_file(file):
            continue
        frames.append(
            {
                "file": file,
                "line": frame.f_lineno,
                "column": 0,
                "function": frame_function_name(frame),
            }
        )
    return frames


def frame_function_name(frame: FrameType) -> str:
    # Python: the Class.method name that a V8 stack line has.
    name = frame.f_code.co_name
    self = frame.f_locals.get("self")
    if self is not None:
        return type(self).__name__ + "." + name
    return name


# Python: the whole playwright package, the counterpart of playwright-core: the
# generated API and the implementation.
_core_dir: Optional[str] = os.path.join(os.path.dirname(playwright.__file__), "")


def set_core_dir(dir: Optional[str]) -> None:
    global _core_dir
    _core_dir = dir
    filter_stack_file.cache_clear()


def core_dir() -> Optional[str]:
    return _core_dir


_show_internal_stack_frames = get_as_boolean_from_env("PWDEBUGIMPL")


def show_internal_stack_frames() -> bool:
    return _show_internal_stack_frames
