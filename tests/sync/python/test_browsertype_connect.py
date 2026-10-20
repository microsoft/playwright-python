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

from typing import Callable

from playwright.sync_api import BrowserType
from tests.conftest import RemoteServer


def test_browser_type_connect_should_forward_close_events_to_pages(
    browser_type: BrowserType, launch_server: Callable[[], RemoteServer]
) -> None:
    # Launch another server to not affect other tests.
    remote = launch_server()

    browser = browser_type.connect(remote.ws_endpoint)
    context = browser.new_context()
    page = context.new_page()

    events = []
    browser.on("disconnected", lambda browser: events.append("browser::disconnected"))
    context.on("close", lambda context: events.append("context::close"))
    page.on("close", lambda page: events.append("page::close"))

    browser.close()
    assert events == ["page::close", "context::close", "browser::disconnected"]
    remote.kill()
    assert events == ["page::close", "context::close", "browser::disconnected"]
