# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

from playwright import sync_playwright


@pytest.fixture
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture
def browser(playwright, browser_name, launch_arguments):
    browser_type = None
    if browser_name == "chromium":
        browser_type = playwright.chromium
    elif browser_name == "firefox":
        browser_type = playwright.firefox
    elif browser_name == "webkit":
        browser_type = playwright.webkit
    browser = browser_type.launch(**launch_arguments)
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    context = browser.newContext()
    yield context
    context.close()


@pytest.fixture
def page(context):
    page = context.newPage()
    yield page
    page.close()
