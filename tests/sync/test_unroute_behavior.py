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

from playwright.sync_api import BrowserContext, Page
from tests.server import Server
from tests.utils import must


def test_context_unroute_all_removes_all_handlers(
    page: Page, context: BrowserContext, server: Server
) -> None:
    context.route(
        "**/*",
        lambda route: route.abort(),
    )
    context.route(
        "**/empty.html",
        lambda route: route.abort(),
    )
    context.unroute_all()
    page.goto(server.EMPTY_PAGE)


def test_page_unroute_all_removes_all_routes(page: Page, server: Server) -> None:
    page.route(
        "**/*",
        lambda route: route.abort(),
    )
    page.route(
        "**/empty.html",
        lambda route: route.abort(),
    )
    page.unroute_all()
    response = must(page.goto(server.EMPTY_PAGE))
    assert response.ok
