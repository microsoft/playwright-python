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

from playwright.async_api import Page, Route
from tests.server import Server


async def test_should_show_exception_after_fulfill(page: Page, server: Server) -> None:
    async def _handle(route: Route) -> None:
        await route.continue_()
        raise Exception("Exception text!?")

    await page.route("*/**", _handle)
    await page.goto(server.EMPTY_PAGE)
    # Any next API call should throw because handler did throw during previous goto()
    with pytest.raises(Exception, match="Exception text!?"):
        await page.goto(server.EMPTY_PAGE)
