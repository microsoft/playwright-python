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

"""Port of tests/library/browsertype-launch.spec.ts."""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest

from playwright.sync_api import Browser, BrowserContext, BrowserType, Error, Page
from tests.utils import TARGET_CLOSED_ERROR_MESSAGE


def test_BT_004_should_reject_all_promises_when_browser_is_closed(
    browser_type: BrowserType, launch_arguments: Dict, sync_gather: Callable
) -> None:
    browser = browser_type.launch(**launch_arguments)
    page = (browser.new_context()).new_page()

    def close() -> None:
        page.evaluate("() => new Promise(f => window.builtins.setTimeout(f, 0))")
        browser.close()

    with pytest.raises(Error) as exc_info:
        sync_gather(
            lambda: page.evaluate("() => new Promise(r => {})"),
            close,
        )
    # WebKit under task-set -c 1 is giving browser, rest are giving target.
    assert " closed" in exc_info.value.message


def test_BT_006_should_throw_if_user_data_dir_is_passed_as_an_argument(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    with pytest.raises(Error) as exc_info:
        browser_type.launch(
            **launch_arguments,
            args=["--user-data-dir=random-path", "--profile=random-path"],
        )
    # The driver words the error for the client's language.
    assert (
        "Pass user_data_dir parameter to 'browser_type.launch_persistent_context"
        in exc_info.value.message
    )


def test_BT_009_should_throw_if_page_argument_is_passed(
    browser_type: BrowserType, browser_name: str, launch_arguments: Dict
) -> None:
    if browser_name == "firefox":
        pytest.skip()

    with pytest.raises(Error) as exc_info:
        browser_type.launch(**launch_arguments, args=["http://example.com"])
    assert "can not specify page" in exc_info.value.message


def test_BT_010_should_reject_if_launched_browser_fails_immediately(
    browser_type: BrowserType,
    launch_arguments: Dict,
    assetdir: Path,
    browser_channel: Optional[str],
) -> None:
    with pytest.raises(Error) as exc_info:
        browser_type.launch(
            **launch_arguments,
            executable_path=assetdir / "dummy_bad_browser_executable.js",
        )
    if browser_channel == "webkit-wsl":
        assert "Failed to launch" in exc_info.value.message
    else:
        assert re.search(
            r"browserType\.launch(.|\n)*(spawn UNKNOWN|spawn EFTYPE|Browser logs:)",
            exc_info.value.message,
            re.IGNORECASE | re.MULTILINE,
        )


def test_BT_011_should_reject_if_executable_path_is_invalid(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    with pytest.raises(Error) as exc_info:
        browser_type.launch(**launch_arguments, executable_path="random-invalid-path")
    assert "Failed to launch" in exc_info.value.message


def test_BT_015_should_fire_close_event_for_all_contexts(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    browser = browser_type.launch(**launch_arguments)
    context = browser.new_context()
    closed: List[bool] = []
    context.on("close", lambda _: closed.append(True))
    browser.close()
    assert closed == [True]


def test_BT_016_should_be_callable_twice(
    browser_type: BrowserType, launch_arguments: Dict, sync_gather: Callable
) -> None:
    browser = browser_type.launch(**launch_arguments)
    sync_gather(
        lambda: browser.close(),
        lambda: browser.close(),
    )
    browser.close()


def test_BT_017_should_allow_await_using(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    # Python's counterpart of `await using` is `with`.
    b: Browser
    c: BrowserContext
    p: Page
    with browser_type.launch(**launch_arguments) as browser:
        b = browser
        with browser.new_context() as context:
            c = context
            with context.new_page() as page:
                p = page
            assert p.is_closed()
        with pytest.raises(Error) as exc_info:
            c.clear_cookies()
        assert TARGET_CLOSED_ERROR_MESSAGE in exc_info.value.message
    assert not b.is_connected()
