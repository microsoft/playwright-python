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

"""Python only: tests of behaviors that no upstream test covers."""

import pytest

from playwright.async_api import Page


@pytest.mark.only_browser("chromium")
async def test_should_work(page: Page) -> None:
    client = await page.context.new_cdp_session(page)
    events = []
    client.on("Runtime.consoleAPICalled", lambda params: events.append(params))
    await client.send("Runtime.enable")
    result = await client.send(
        "Runtime.evaluate",
        {"expression": "window.foo = 'bar'; console.log('log'); 'result'"},
    )
    assert result == {"result": {"type": "string", "value": "result"}}
    foo = await page.evaluate("() => window.foo")
    assert foo == "bar"
    assert events[0]["args"][0]["value"] == "log"
