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

"""Port of packages/playwright-core/src/client/clientHelper.ts.

Python: a script is a string or a { path, content } object, never a function, so the
function forms of evaluationScript() and initScriptSourceWithExposedFunctions() are
not ported: the Python API takes JavaScript source only.
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Union

from playwright._impl.errors import Error
from playwright._impl.isomorphic.string_utils import js_string

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import protocol_types as channels


def env_object_to_array(env: Mapping[str, Any]) -> List["channels.NameValue"]:
    result: List["channels.NameValue"] = []
    for name in env:
        # Python: None is undefined.
        if env[name] is not None:
            result.append({"name": name, "value": js_string(env[name])})
    return result


async def evaluation_script(
    fun: Union[str, Dict[str, Any]],
    arg: Any = None,
    add_source_url: bool = True,
) -> str:
    # Not ported: the function form, `(${source})(${argString})`.
    if arg is not None:
        raise Error("Cannot evaluate a string with arguments")
    if isinstance(fun, str):
        return fun
    if fun.get("content") is not None:
        return fun["content"]
    if fun.get("path") is not None:
        source = await _read_file(fun["path"])
        if add_source_url:
            source = add_source_url_to_script(source, fun["path"])
        return source
    # Python: the message names the Python parameters, script and path.
    raise Error("Either path or script parameter must be present")


async def _read_file(path: Union[str, Path]) -> str:
    # Python: fs.promises.readFile(path, 'utf8') reads in a thread.
    def read() -> str:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    return await asyncio.get_running_loop().run_in_executor(None, read)


def add_source_url_to_script(source: str, path: Union[str, Path]) -> str:
    return f"{source}\n//# sourceURL={str(path).replace(chr(10), '')}"
