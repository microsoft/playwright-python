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

"""Port of tests/library/webmcp-disabled.spec.ts."""

import pytest

from playwright.async_api import Error, Page

pytestmark = pytest.mark.skip_browser("webkit")


async def test_WM_015_should_throw_when_the_browser_was_launched_without_web_mcp(
    page: Page, browser_name: str
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.webmcp.tools()
    assert "WebMCP is not enabled." in exc_info.value.message
    assert (
        "dom.modelcontext.enabled"
        if browser_name == "firefox"
        else "--enable-features=WebMCP"
    ) in exc_info.value.message
