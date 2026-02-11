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

import pytest

from playwright.sync_api import BrowserContext, Error, Page
from tests.server import Server


def test_context_request_should_support_timeout_option(
    page: Page, context: BrowserContext, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/39220

    server.set_route("/", lambda req: None)
    with pytest.raises(Error, match="Timeout 123ms exceeded"):
        page.request.get(server.PREFIX, timeout=123)
    with pytest.raises(Error, match="Timeout 123ms exceeded"):
        context.request.get(server.PREFIX, timeout=123)

    context.set_default_timeout(123)
    with pytest.raises(Error, match="Timeout 123ms exceeded"):
        page.request.get(server.PREFIX)
    with pytest.raises(Error, match="Timeout 123ms exceeded"):
        context.request.get(server.PREFIX)
