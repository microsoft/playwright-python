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

import sys
from typing import TYPE_CHECKING, List

import pytest

from playwright.async_api import Page
from tests.server import Server

if TYPE_CHECKING:
    # Real type for static checkers, undefined at runtime (PEP 649 case).
    from playwright.async_api import ConsoleMessage as TypeCheckingOnlyConsoleMessage


async def test_console_should_have_location_for_console_api_calls(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_console_message() as message_info:
        await page.goto(server.PREFIX + "/consolelog.html")
    message = await message_info.value
    assert message.text.startswith("here:")
    assert message.type == "log"
    location = message.location
    # Engines have different column notion.
    assert location["url"] == server.PREFIX + "/consolelog.html"
    assert location["lineNumber"] == 7
    # Added in 1.60: location now also exposes line/column aliases for parity with WebError.location.
    assert location["line"] == 7
    assert location["column"] == location["columnNumber"]


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="PEP 649 lazy annotations require Python 3.14+",
)
async def test_console_should_support_annotations_with_runtime_unresolved_types(
    page: Page,
) -> None:
    # Since PEP 649, annotations are lazily evaluated; the signature
    # inspection done for event listeners must not resolve them eagerly.
    messages: List[str] = []

    def on_console(message: TypeCheckingOnlyConsoleMessage) -> None:
        messages.append(message.text)

    page.on("console", on_console)
    await page.evaluate('() => console.log("hello")')
    assert messages == ["hello"]
