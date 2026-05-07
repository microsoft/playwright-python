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

from typing import Dict

from playwright.sync_api import Browser, BrowserType


def test_should_return_browser_type(
    browser: Browser, browser_type: BrowserType
) -> None:
    assert browser.browser_type is browser_type


def test_bind_should_return_endpoint_and_allow_unbind(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = browser_type.launch(**launch_arguments)
    try:
        result = browser.bind("test-server")
        assert "endpoint" in result
        assert isinstance(result["endpoint"], str)
        assert len(result["endpoint"]) > 0
        browser.unbind()
    finally:
        browser.close()


def test_should_fire_context_event_on_new_context(browser: Browser) -> None:
    events = []
    browser.on("context", lambda ctx: events.append(ctx))
    context = browser.new_context()
    try:
        assert events == [context]
    finally:
        context.close()
