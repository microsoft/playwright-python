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

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Set, Union

from playwright._impl._browser_context import BrowserContext
from playwright._impl._errors import Error
from playwright._impl._helper import async_readfile
from playwright._impl._locator import set_test_id_attribute_name

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels


class Selectors:
    def __init__(self, loop: asyncio.AbstractEventLoop, dispatcher_fiber: Any) -> None:
        self._loop = loop
        self._contexts_for_selectors: Set[BrowserContext] = set()
        self._selector_engines: List[channels.SelectorEngine] = []
        self._dispatcher_fiber = dispatcher_fiber
        self._test_id_attribute_name: Optional[str] = None

    async def register(
        self,
        name: str,
        script: Optional[str],
        path: Optional[Union[str, Path]],
        content_script: Optional[bool],
    ) -> None:
        if any(engine for engine in self._selector_engines if engine["name"] == name):
            raise Error(
                f'Selectors.register: "{name}" selector engine has been already registered'
            )
        if path:
            source = (await async_readfile(path)).decode()
        elif script:
            source = script
        else:
            raise Error("Either source or path should be specified")
        engine: channels.SelectorEngine = {"name": name, "source": source}
        if content_script:
            engine["contentScript"] = content_script
        for context in self._contexts_for_selectors:
            await context._channel.registerSelectorEngine(selectorEngine=engine)
        self._selector_engines.append(engine)

    def set_test_id_attribute(self, attribute_name: str) -> None:
        set_test_id_attribute_name(attribute_name)
        self._test_id_attribute_name = attribute_name
        for context in self._contexts_for_selectors:
            context._channel.send_no_reply(
                "setTestIdAttributeName", {"testIdAttributeName": attribute_name}
            )
