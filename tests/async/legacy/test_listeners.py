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

from playwright.async_api import Page, Response
from tests.server import Server


async def test_listeners(page: Page, server: Server) -> None:
    log = []

    def print_response(response: Response) -> None:
        log.append(response)

    page.on("response", print_response)
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    assert len(log) > 0
    page.remove_listener("response", print_response)

    log = []
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    assert len(log) == 0
