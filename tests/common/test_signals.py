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
import asyncio
import multiprocessing
import os
import signal
import sys
from typing import Any, Dict

import pytest

from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright


def _test_signals_async(
    browser_name: str, launch_arguments: Dict, wait_queue: "multiprocessing.Queue[str]"
) -> None:
    os.setpgrp()
    sigint_received = False

    def my_sig_handler(signum: int, frame: Any) -> None:
        nonlocal sigint_received
        sigint_received = True

    signal.signal(signal.SIGINT, my_sig_handler)

    async def main() -> None:
        playwright = await async_playwright().start()
        browser = await playwright[browser_name].launch(
            **launch_arguments,
            handle_sigint=False,
        )
        context = await browser.new_context()
        page = await context.new_page()
        notified = False
        try:
            nonlocal sigint_received
            while not sigint_received:
                if not notified:
                    wait_queue.put("ready")
                    notified = True
                await page.wait_for_timeout(100)
        finally:
            wait_queue.put("close context")
            await context.close()
            wait_queue.put("close browser")
            await browser.close()
            wait_queue.put("close playwright")
            await playwright.stop()
            wait_queue.put("all done")

    asyncio.run(main())


def _test_signals_sync(
    browser_name: str, launch_arguments: Dict, wait_queue: "multiprocessing.Queue[str]"
) -> None:
    os.setpgrp()
    sigint_received = False

    def my_sig_handler(signum: int, frame: Any) -> None:
        nonlocal sigint_received
        sigint_received = True

    signal.signal(signal.SIGINT, my_sig_handler)

    playwright = sync_playwright().start()
    browser = playwright[browser_name].launch(
        **launch_arguments,
        handle_sigint=False,
    )
    context = browser.new_context()
    page = context.new_page()
    notified = False
    try:
        while not sigint_received:
            if not notified:
                wait_queue.put("ready")
                notified = True
            page.wait_for_timeout(100)
    finally:
        wait_queue.put("close context")
        context.close()
        wait_queue.put("close browser")
        browser.close()
        wait_queue.put("close playwright")
        playwright.stop()
        wait_queue.put("all done")


def _create_signals_test(
    target: Any, browser_name: str, launch_arguments: Dict
) -> None:
    wait_queue: "multiprocessing.Queue[str]" = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=target, args=[browser_name, launch_arguments, wait_queue]
    )
    process.start()
    assert process.pid is not None
    logs = [wait_queue.get()]
    os.killpg(os.getpgid(process.pid), signal.SIGINT)
    process.join()
    while not wait_queue.empty():
        logs.append(wait_queue.get())
    assert logs == [
        "ready",
        "close context",
        "close browser",
        "close playwright",
        "all done",
    ]
    assert process.exitcode == 0


@pytest.mark.skipif(sys.platform == "win32", reason="there is no SIGINT on Windows")
def test_signals_sync(browser_name: str, launch_arguments: Dict) -> None:
    _create_signals_test(_test_signals_sync, browser_name, launch_arguments)


@pytest.mark.skipif(sys.platform == "win32", reason="there is no SIGINT on Windows")
def test_signals_async(browser_name: str, launch_arguments: Dict) -> None:
    _create_signals_test(_test_signals_async, browser_name, launch_arguments)
