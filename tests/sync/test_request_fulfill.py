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

from playwright.sync_api import Page, Route
from tests.server import Server


def test_should_fetch_original_request_and_fulfill(page: Page, server: Server) -> None:
    def handle(route: Route) -> None:
        response = page.request.fetch(route.request)
        route.fulfill(response=response)

    page.route("**/*", handle)
    response = page.goto(server.PREFIX + "/title.html")
    assert response
    assert response.status == 200
    assert page.title() == "Woof-Woof"
