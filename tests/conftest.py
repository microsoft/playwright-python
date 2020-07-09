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

import os
import pytest
import playwright
import threading
import time

from twisted.internet import reactor
from twisted.web.static import File
from twisted.web import server as web_server, resource

from .server import server as server_object
from .utils import utils as utils_object

# Will mark all the tests as async
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.asyncio)

def pytest_generate_tests(metafunc):
    if 'browser_name' in metafunc.fixturenames:
        browsers = metafunc.config.option.browser or ['chromium', 'firefox', 'webkit']
        metafunc.parametrize("browser_name", browsers, scope='session')

@pytest.fixture(scope='session')
def event_loop():
    loop = playwright.playwright.loop
    yield loop
    loop.close()


@pytest.fixture(scope='session')
async def browser(browser_name):
    browser = await playwright.browser_types[browser_name].launch()
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


@pytest.fixture
def server():
    yield server_object


@pytest.fixture
def utils():
    yield utils_object


@pytest.fixture(autouse=True, scope='session')
async def start_http_server():
    static_path=os.path.join(os.path.dirname(__file__), 'assets')
    resource = File(static_path)
    site = web_server.Site(resource)
    reactor.listenTCP(server_object.PORT, site)
    t = threading.Thread(target=reactor.run)
    t.start()
    yield
    reactor.stop()
    t.join()


@pytest.fixture(scope="session")
def browser_name(pytestconfig):
    return pytestconfig.getoption('browser')


@pytest.fixture(scope="session")
def is_webkit(browser_name):
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name):
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name):
    return browser_name == "chromium"


@pytest.fixture(autouse=True)
def skip_by_browser(request, browser_name):
    if request.node.get_closest_marker('skip_browser'):
        if request.node.get_closest_marker('skip_browser').args[0] == browser_name:
            pytest.skip('skipped on this platform: {}'.format(browser_name))


def pytest_addoption(parser):
    group = parser.getgroup('playwright', 'Playwright')
    group.addoption(
        '--browser',
        action='append',
        default=[],
        help='Browsers which should be used. By default on all the browsers.',
    )
