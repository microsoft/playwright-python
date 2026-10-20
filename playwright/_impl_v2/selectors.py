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

"""Port of packages/playwright-core/src/client/selectors.ts.

Python: Selectors is not a ChannelOwner, so it keeps the event loop for the generated
API. The script of register() is a string or a file path, never a function, and the
options object is separate parameters. A set does not keep the insertion order of a
JS Set; nothing depends on that order.
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Set, Union

from playwright._impl._errors import Error
from playwright._impl_v2.client_helper import evaluation_script
from playwright._impl_v2.locator import set_test_id_attribute
from playwright._impl_v2.timeout_settings import NO_TIMEOUT
from playwright._impl_v2.utils.promise import catch

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.browser_context import BrowserContext


class Selectors:
    def __init__(self) -> None:
        self._selector_engines: List["channels.SelectorEngine"] = []
        self._test_id_attribute_name: Optional[str] = None
        self._contexts_for_selectors: Set["BrowserContext"] = set()
        # Python: the generated API reads the event loop of each object. Playwright
        # creates Selectors in the loop of the connection.
        self._loop = asyncio.get_event_loop()

    async def register(
        self,
        name: str,
        script: Optional[str],
        path: Optional[Union[str, Path]],
        content_script: Optional[bool],
    ) -> None:
        if any(engine["name"] == name for engine in self._selector_engines):
            # Python: the message names the Python class, Selectors, as the tests
            # expect.
            raise Error(
                f'Selectors.register: "{name}" selector engine has been already registered'
            )

        # Python: script and path are the { content, path } form of upstream.
        source = await evaluation_script(
            {"content": script, "path": path}, add_source_url=False
        )
        selector_engine: "channels.SelectorEngine" = {"name": name, "source": source}
        # Python: `{ ...options }` copies only the options that are set.
        if content_script is not None:
            selector_engine["contentScript"] = content_script
        # Python: iterates a copy. A context can open or close while this awaits;
        # a JS Set can change while it is iterated, a Python set can not.
        for context in list(self._contexts_for_selectors):
            await context._channel.registerSelectorEngine(
                selectorEngine=selector_engine, timeout=NO_TIMEOUT
            )
        self._selector_engines.append(selector_engine)

    def set_test_id_attribute(self, attribute_name: str) -> None:
        self._test_id_attribute_name = attribute_name
        set_test_id_attribute(attribute_name)
        for context in self._contexts_for_selectors:
            context._options["testIdAttributeName"] = attribute_name
            catch(
                context._channel.setTestIdAttributeName(
                    testIdAttributeName=attribute_name, timeout=NO_TIMEOUT
                )
            )

    def _with_selector_options(self, options: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            **options,
            "selectorEngines": self._selector_engines,
            "testIdAttributeName": self._test_id_attribute_name,
        }
