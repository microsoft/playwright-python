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

"""Port of tests/library/browsertype-launch-selenium.spec.ts."""

import os
import socket
import time
from pathlib import Path
from typing import Callable, Dict, Generator, List

import pytest

from playwright.async_api import BrowserType, Error, async_playwright, expect
from tests.helpers.launch_test_hooks import launch_test_hook
from tests.helpers.remote_server import ChildProcess

CHROME_DRIVER = os.environ.get("PWTEST_CHROMEDRIVER")


@pytest.fixture(autouse=True)
def skip_without_chrome_driver() -> None:
    """Port of test.skip(!chromeDriver): the tests need a Selenium Grid and ChromeDriver."""
    if not CHROME_DRIVER:
        pytest.skip()


@pytest.fixture
def standalone_3_141_59() -> str:
    return os.path.join(
        os.environ["PWTEST_SELENIUM"], "selenium-server-standalone-3.141.59.jar"
    )


@pytest.fixture
def selenium_4_8_3() -> str:
    return os.path.join(os.environ["PWTEST_SELENIUM"], "selenium-server-4.8.3.jar")


@pytest.fixture
def broken_driver(assetdir: Path) -> Path:
    return assetdir / "selenium-grid" / "broken-selenium-driver.js"


@pytest.fixture
def worker_index() -> int:
    """Port of testInfo.workerIndex."""
    return int(os.environ.get("PYTEST_XDIST_WORKER", "gw0")[2:])


@pytest.fixture
def child_process() -> Generator[Callable[..., ChildProcess], None, None]:
    """Port of the childProcess fixture in tests/config/commonFixtures.ts."""
    processes: List[ChildProcess] = []

    def start(command: List[str]) -> ChildProcess:
        process = ChildProcess(command)
        processes.append(process)
        return process

    yield start
    for process in processes:
        process.kill()


def wait_for_port(port: int) -> None:
    """Port of the waitForPort fixture in tests/config/commonFixtures.ts."""
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return
        except OSError:
            time.sleep(0.1)


def write_selenium_config(tmp_path: Path, assetdir: Path, port: int) -> Path:
    template = assetdir / "selenium-grid" / "selenium-config-standalone.json"
    content = template.read_text(encoding="utf-8").replace("4444", str(port))
    file = tmp_path / "selenium-config-standalone.json"
    file.write_text(content, encoding="utf-8")
    return file


@pytest.mark.skip_protocol_check
async def test_BT_097_selenium_grid_3_141_59_standalone_chromium(
    browser_name: str,
    child_process: Callable[..., ChildProcess],
    browser_type: BrowserType,
    launch_arguments: Dict,
    standalone_3_141_59: str,
    worker_index: int,
    tmp_path: Path,
    assetdir: Path,
) -> None:
    if browser_name != "chromium":
        pytest.skip()

    port = (worker_index * 5) + 15123
    grid = child_process(
        [
            "java",
            f"-Dwebdriver.chrome.driver={CHROME_DRIVER}",
            "-jar",
            standalone_3_141_59,
            "-config",
            str(write_selenium_config(tmp_path, assetdir, port)),
        ]
    )
    wait_for_port(port)

    selenium_remote_url = f"http://127.0.0.1:{port}/wd/hub"
    with launch_test_hook(
        browser_type, "__testHookSeleniumRemoteURL", selenium_remote_url
    ):
        browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.set_content("<title>Hello world</title><div>Get Started</div>")
    await page.click("text=Get Started")
    await expect(page).to_have_title("Hello world")
    await browser.close()

    assert "Starting ChromeDriver" in grid.output
    assert "Started new session" in grid.output
    grid.wait_for_output("Removing session")


@pytest.mark.skip_protocol_check
async def test_BT_098_selenium_grid_3_141_59_hub_node_chromium(
    browser_name: str,
    child_process: Callable[..., ChildProcess],
    browser_type: BrowserType,
    launch_arguments: Dict,
    standalone_3_141_59: str,
    worker_index: int,
) -> None:
    if browser_name != "chromium":
        pytest.skip()

    port = (worker_index * 5) + 15123
    hub = child_process(
        ["java", "-jar", standalone_3_141_59, "-role", "hub", "-port", str(port)]
    )
    wait_for_port(port)

    node = child_process(
        [
            "java",
            f"-Dwebdriver.chrome.driver={CHROME_DRIVER}",
            "-jar",
            standalone_3_141_59,
            "-role",
            "node",
            "-host",
            "127.0.0.1",
            "-hub",
            f"http://127.0.0.1:{port}/grid/register",
        ]
    )
    node.wait_for_output("The node is registered to the hub and ready to use")
    hub.wait_for_output("Registered a node")

    selenium_remote_url = f"http://127.0.0.1:{port}/wd/hub"
    with launch_test_hook(
        browser_type, "__testHookSeleniumRemoteURL", selenium_remote_url
    ):
        browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.set_content("<title>Hello world</title><div>Get Started</div>")
    await page.click("text=Get Started")
    await expect(page).to_have_title("Hello world")
    await browser.close()

    assert "Got a request to create a new session" in hub.output
    assert "Starting ChromeDriver" in node.output
    assert "Started new session" in node.output
    node.wait_for_output("Removing session")


@pytest.mark.skip_protocol_check
async def test_BT_099_selenium_grid_4_8_3_standalone_chromium(
    browser_name: str,
    child_process: Callable[..., ChildProcess],
    browser_type: BrowserType,
    launch_arguments: Dict,
    selenium_4_8_3: str,
    worker_index: int,
    tmp_path: Path,
    assetdir: Path,
) -> None:
    if browser_name != "chromium":
        pytest.skip()

    port = (worker_index * 5) + 15123
    grid = child_process(
        [
            "java",
            f"-Dwebdriver.chrome.driver={CHROME_DRIVER}",
            "-jar",
            selenium_4_8_3,
            "standalone",
            "--config",
            str(write_selenium_config(tmp_path, assetdir, port)),
        ]
    )
    wait_for_port(port)

    selenium_remote_url = f"http://127.0.0.1:{port}/"
    with launch_test_hook(
        browser_type, "__testHookSeleniumRemoteURL", selenium_remote_url
    ):
        browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.set_content("<title>Hello world</title><div>Get Started</div>")
    await page.click("text=Get Started")
    await expect(page).to_have_title("Hello world")
    await browser.close()

    assert "Starting ChromeDriver" in grid.output
    assert "Session created" in grid.output
    grid.wait_for_output("Deleted session")


@pytest.mark.skip_protocol_check
async def test_BT_100_selenium_grid_4_8_3_hub_node_chromium(
    browser_name: str,
    child_process: Callable[..., ChildProcess],
    browser_type: BrowserType,
    launch_arguments: Dict,
    selenium_4_8_3: str,
    worker_index: int,
) -> None:
    if browser_name != "chromium":
        pytest.skip()

    port = (worker_index * 5) + 15123
    hub = child_process(["java", "-jar", selenium_4_8_3, "hub", "--port", str(port)])
    wait_for_port(port)
    selenium_remote_url = f"http://127.0.0.1:{port}/"

    node = child_process(
        [
            "java",
            f"-Dwebdriver.chrome.driver={CHROME_DRIVER}",
            "-jar",
            selenium_4_8_3,
            "node",
            "--grid-url",
            f"http://127.0.0.1:{port}",
            "--port",
            str(port + 1),
        ]
    )
    node.wait_for_output("Node has been added")
    hub.wait_for_output("from DOWN to UP")

    with launch_test_hook(
        browser_type, "__testHookSeleniumRemoteURL", selenium_remote_url
    ):
        browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.set_content("<title>Hello world</title><div>Get Started</div>")
    await page.click("text=Get Started")
    await expect(page).to_have_title("Hello world")
    await browser.close()

    assert "session request received by the distributor" in hub.output.lower()
    assert "Starting ChromeDriver" in node.output
    hub.wait_for_output("Deleted session")


@pytest.mark.skip_protocol_check
async def test_BT_101_selenium_grid_4_8_3_standalone_chromium_broken_driver(
    browser_name: str,
    child_process: Callable[..., ChildProcess],
    browser_type: BrowserType,
    launch_arguments: Dict,
    selenium_4_8_3: str,
    broken_driver: Path,
    worker_index: int,
    tmp_path: Path,
    assetdir: Path,
) -> None:
    if browser_name != "chromium":
        pytest.skip()

    port = (worker_index * 5) + 15123
    grid = child_process(
        [
            "java",
            f"-Dwebdriver.chrome.driver={broken_driver}",
            "-jar",
            selenium_4_8_3,
            "standalone",
            "--config",
            str(write_selenium_config(tmp_path, assetdir, port)),
        ]
    )
    wait_for_port(port)

    selenium_remote_url = f"http://127.0.0.1:{port}/"
    with pytest.raises(Error) as exc_info:
        with launch_test_hook(
            browser_type, "__testHookSeleniumRemoteURL", selenium_remote_url
        ):
            await browser_type.launch(**launch_arguments)
    assert (
        f"Error connecting to Selenium at http://127.0.0.1:{port}/session: Could not start a new session"
        in exc_info.value.message
    )

    assert "Starting ChromeDriver" not in grid.output


@pytest.mark.skip_protocol_check
async def test_BT_102_selenium_grid_3_141_59_standalone_non_chromium(
    browser_name: str, browser_type: BrowserType, launch_arguments: Dict
) -> None:
    if browser_name == "chromium":
        pytest.skip()

    selenium_remote_url = "http://127.0.0.1:4444/wd/hub"
    with pytest.raises(Error) as exc_info:
        with launch_test_hook(
            browser_type, "__testHookSeleniumRemoteURL", selenium_remote_url
        ):
            await browser_type.launch(**launch_arguments)
    assert (
        "Connecting to SELENIUM_REMOTE_URL is only supported by Chromium"
        in exc_info.value.message
    )


async def test_BT_103_selenium_grid_3_141_59_standalone_chromium_through_run_driver(
    browser_name: str,
    child_process: Callable[..., ChildProcess],
    launch_arguments: Dict,
    standalone_3_141_59: str,
    worker_index: int,
    tmp_path: Path,
    assetdir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if browser_name != "chromium":
        pytest.skip()

    port = (worker_index * 5) + 15123
    grid = child_process(
        [
            "java",
            f"-Dwebdriver.chrome.driver={CHROME_DRIVER}",
            "-jar",
            standalone_3_141_59,
            "-config",
            str(write_selenium_config(tmp_path, assetdir, port)),
        ]
    )
    wait_for_port(port)

    # Port of oop.start({ SELENIUM_REMOTE_URL }): a new driver with that environment.
    monkeypatch.setenv("SELENIUM_REMOTE_URL", f"http://127.0.0.1:{port}/wd/hub")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**launch_arguments)
        page = await browser.new_page()
        await page.set_content("<title>Hello world</title><div>Get Started</div>")
        await page.click("text=Get Started")
        await expect(page).to_have_title("Hello world")
        # Note: it is important to stop the driver without explicitly closing the browser.
        # It should terminate selenium session in this case.

    assert "Starting ChromeDriver" in grid.output
    assert "Started new session" in grid.output
    # It is important that selenium session is terminated.
    grid.wait_for_output("Removing session")
