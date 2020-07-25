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

import asyncio
import sys

import pytest

import playwright

from .server import test_server
from .utils import utils as utils_object


# Will mark all the tests as async
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.asyncio)


def pytest_generate_tests(metafunc):
    if "browser_name" in metafunc.fixturenames:
        browsers = metafunc.config.option.browser or ["chromium", "firefox", "webkit"]
        metafunc.parametrize("browser_name", browsers, scope="session")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def selectors():
    return playwright.selectors.as_async()


@pytest.fixture(scope="session")
def browser_type(browser_name: str):
    if browser_name == "chromium":
        return playwright.chromium.as_async()
    if browser_name == "firefox":
        return playwright.firefox.as_async()
    if browser_name == "webkit":
        return playwright.webkit.as_async()


@pytest.fixture(scope="session")
def launch_arguments(pytestconfig):
    return {
        "headless": not pytestconfig.getoption("--headful"),
        "chromiumSandbox": False,
    }


@pytest.fixture(scope="session")
async def browser_factory(launch_arguments, browser_type):
    async def launch(**kwargs):
        return await browser_type.launch(**launch_arguments, **kwargs)

    return launch


@pytest.fixture(scope="session")
async def browser(browser_factory):
    browser = await browser_factory()
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
    yield test_server.server


@pytest.fixture
def https_server():
    yield test_server.https_server


@pytest.fixture
def utils():
    yield utils_object


@pytest.fixture(autouse=True, scope="session")
async def start_server():
    test_server.start()
    yield
    test_server.stop()


@pytest.fixture(autouse=True)
def after_each_hook():
    yield
    test_server.reset()


@pytest.fixture(scope="session")
def browser_name(pytestconfig):
    return pytestconfig.getoption("browser")


@pytest.fixture(scope="session")
def is_webkit(browser_name):
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name):
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name):
    return browser_name == "chromium"


@pytest.fixture(scope="session")
def is_win():
    return sys.platform == "win32"


@pytest.fixture(scope="session")
def is_linux():
    return sys.platform == "linux"


@pytest.fixture(scope="session")
def is_mac():
    return sys.platform == "darwin"


def _get_skiplist(request, values, value_name):
    skipped_values = []
    # Allowlist
    only_marker = request.node.get_closest_marker(f"only_{value_name}")
    if only_marker:
        skipped_values = values
        skipped_values.remove(only_marker.args[0])

    # Denylist
    skip_marker = request.node.get_closest_marker(f"skip_{value_name}")
    if skip_marker:
        skipped_values.append(skip_marker.args[0])

    return skipped_values


@pytest.fixture(autouse=True)
def skip_by_browser(request, browser_name):
    skip_browsers_names = _get_skiplist(
        request, ["chromium", "firefox", "webkit"], "browser"
    )

    if browser_name in skip_browsers_names:
        pytest.skip("skipped for this browser: {}".format(browser_name))


@pytest.fixture(autouse=True)
def skip_by_platform(request):
    skip_platform_names = _get_skiplist(
        request, ["win32", "linux", "darwin"], "platform"
    )

    if sys.platform in skip_platform_names:
        pytest.skip("skipped on this platform: {}".format(sys.platform))


def pytest_addoption(parser):
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--browser",
        action="append",
        default=[],
        help="Browsers which should be used. By default on all the browsers.",
    )
    parser.addoption(
        "--headful",
        action="store_true",
        default=False,
        help="Run tests in headful mode.",
    )
