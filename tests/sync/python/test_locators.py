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

import traceback

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def route_iframe(page: Page) -> None:
    page.route(
        "**/empty.html",
        lambda route: route.fulfill(
            body='<iframe src="iframe.html" name="frame1"></iframe>',
            content_type="text/html",
        ),
    )
    page.route(
        "**/iframe.html",
        lambda route: route.fulfill(
            body="""<html>
          <div>
            <button>Hello iframe</button>
            <iframe src="iframe-2.html"></iframe>
          </div>
          <span>1</span>
          <span>2</span>
        </html>""",
            content_type="text/html",
        ),
    )
    page.route(
        "**/iframe-2.html",
        lambda route: route.fulfill(
            body="<html><button>Hello nested iframe</button></html>",
            content_type="text/html",
        ),
    )


def test_locators_frame_should_work_with_iframe(page: Page, server: Server) -> None:
    route_iframe(page)
    page.goto(server.EMPTY_PAGE)
    button = page.frame_locator("iframe").locator("button")
    button.wait_for()
    assert button.inner_text() == "Hello iframe"
    button.click()
    assert (
        repr(page.frame_locator("iframe"))
        == f"<FrameLocator frame=<Frame name= url='{server.PREFIX}/empty.html'> selector='iframe'>"
    )


def test_locator_click_timeout_error_should_contain_call_log(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.get_by_role("button", name="Hello Python").click(timeout=42)
    formatted_exception = "".join(
        traceback.format_exception(type(exc_info.value), value=exc_info.value, tb=None)
    )
    assert "Locator.click: Timeout 42ms exceeded." in formatted_exception
    assert (
        'waiting for get_by_role("button", name="Hello Python")' in formatted_exception
    )
    assert (
        "During handling of the above exception, another exception occurred"
        not in formatted_exception
    )
