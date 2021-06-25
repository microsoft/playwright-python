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

from playwright.sync_api import Error


@pytest.mark.only_browser("chromium")
def test_should_work(page):
    client = page.context.new_cdp_session(page)
    events = []
    client.on("Runtime.consoleAPICalled", lambda params: events.append(params))
    client.send("Runtime.enable")
    result = client.send(
        "Runtime.evaluate",
        {"expression": "window.foo = 'bar'; console.log('log'); 'result'"},
    )
    assert result == {"result": {"type": "string", "value": "result"}}
    foo = page.evaluate("() => window.foo")
    assert foo == "bar"
    assert events[0]["args"][0]["value"] == "log"


@pytest.mark.only_browser("chromium")
def test_should_receive_events(page, server):
    client = page.context.new_cdp_session(page)
    client.send("Network.enable")
    events = []
    client.on("Network.requestWillBeSent", lambda event: events.append(event))
    page.goto(server.EMPTY_PAGE)
    assert len(events) == 1


@pytest.mark.only_browser("chromium")
def test_should_be_able_to_detach_session(page):
    client = page.context.new_cdp_session(page)
    client.send("Runtime.enable")
    eval_response = client.send(
        "Runtime.evaluate", {"expression": "1 + 2", "returnByValue": True}
    )
    assert eval_response["result"]["value"] == 3
    client.detach()
    with pytest.raises(Error) as exc_info:
        client.send("Runtime.evaluate", {"expression": "3 + 1", "returnByValue": True})
    assert "Target page, context or browser has been closed" in exc_info.value.message


@pytest.mark.only_browser("chromium")
def test_should_not_break_page_close(browser):
    context = browser.new_context()
    page = context.new_page()
    session = page.context.new_cdp_session(page)
    session.detach()
    page.close()
    context.close()


@pytest.mark.only_browser("chromium")
def test_should_detach_when_page_closes(browser):
    context = browser.new_context()
    page = context.new_page()
    session = context.new_cdp_session(page)
    page.close()
    with pytest.raises(Error):
        session.detach()
    context.close()
