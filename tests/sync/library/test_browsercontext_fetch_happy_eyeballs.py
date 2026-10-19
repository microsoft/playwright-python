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

"""Port of tests/library/browsercontext-fetch-happy-eyeballs.spec.ts."""

import os

import pytest

from playwright.sync_api import Playwright, expect
from tests.server import Server


@pytest.fixture(autouse=True)
def force_new_connection(server: Server) -> None:
    # Force a new connection every time, so that we can intercept the hostname lookup.
    server.set_extra_headers("/simple.json", {"Connection": "close"})


def test_FE_188_should_work_with_ip6_and_port_as_the_host(
    playwright: Playwright, server: Server
) -> None:
    if os.environ.get("INSIDE_DOCKER"):
        pytest.skip("docker does not support IPv6 by default")
    # The request fixture.
    request = playwright.request.new_context()
    try:
        response = request.get(f"http://[::1]:{server.PORT}/simple.json")
        assert response.url == f"http://[::1]:{server.PORT}/simple.json"
        expect(response).to_be_ok()
    finally:
        request.dispose()
