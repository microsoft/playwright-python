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

import playwright_web
import pytest


@pytest.fixture(scope='session')
def event_loop():
    loop = playwright_web.playwright.loop
    yield loop
    loop.close()


@pytest.fixture(scope='session')
async def browser():
    browser = await playwright_web.chromium.launch()
    yield browser
    await browser.close()


@pytest.fixture
async def context(browser):
    context = await browser.newContext()
    yield context
    await context.close()

@pytest.fixture
async def page(context):
    page = await context.newPage()
    yield page
    await page.close()
