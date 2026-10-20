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

import asyncio

from playwright.async_api import Browser


async def test_close_should_be_callable_twice(browser: Browser) -> None:
    context = await browser.new_context()
    await asyncio.gather(
        context.close(),
        context.close(),
    )
    await context.close()


async def test_is_closed_should_reflect_state(browser: Browser) -> None:
    context = await browser.new_context()
    assert context.is_closed() is False
    await context.close()
    assert context.is_closed() is True
