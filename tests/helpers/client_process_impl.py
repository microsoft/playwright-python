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

"""A Python script that uses the Python client: the child process of client_process.py.

Port of tests/config/remote-server-impl.js for the Python client. Upstream runs a
Node.js process that launches the browser; this script launches it with the sync or
async API of the Python client, then waits idle (outside any Playwright call) until
the test sends it a signal. It prints "(key=>value)" lines, like upstream:
(tempDir=>...), (ready=>true), (closed=>success).

It runs as a standalone script (python -I client_process_impl.py '<json options>'),
so it imports nothing from the tests package.
"""

import asyncio
import glob
import http.server
import json
import os
import sys
import time
from typing import Any, Dict

OPTIONS: Dict[str, Any] = json.loads(sys.argv[1])


def out(key: str, value: str) -> None:
    print(f"({key}=>{value})", flush=True)


def report_temp_dir() -> None:
    # The test points TMPDIR to a directory of its own, where the driver creates the
    # browser's user data dir.
    profiles = glob.glob(
        os.path.join(os.environ["TMPDIR"], "playwright_*dev_profile-*")
    )
    out("tempDir", profiles[0] if len(profiles) == 1 else "unknown")


def should_exit() -> bool:
    exit_on_file = OPTIONS.get("exitOnFile")
    return bool(exit_on_file and os.path.exists(exit_on_file))


def run_sync() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser_type = playwright[OPTIONS["browserTypeName"]]
        if OPTIONS.get("startStopAndRunHttp"):
            browser = browser_type.launch(**OPTIONS["launchOptions"])
            browser.close()
            out("closed", "success")
            http.server.HTTPServer(
                ("127.0.0.1", 0), http.server.BaseHTTPRequestHandler
            ).serve_forever()
            return
        browser = browser_type.launch(**OPTIONS["launchOptions"])
        report_temp_dir()
        if OPTIONS.get("url"):
            browser.new_page().goto(OPTIONS["url"])
        out("ready", "true")
        while True:
            time.sleep(0.1)
            if should_exit():
                sys.exit(42)


async def run_async() -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser_type = playwright[OPTIONS["browserTypeName"]]
        if OPTIONS.get("startStopAndRunHttp"):
            browser = await browser_type.launch(**OPTIONS["launchOptions"])
            await browser.close()
            out("closed", "success")
            server = await asyncio.start_server(
                lambda reader, writer: writer.close(), "127.0.0.1", 0
            )
            await server.serve_forever()
            return
        browser = await browser_type.launch(**OPTIONS["launchOptions"])
        report_temp_dir()
        if OPTIONS.get("url"):
            page = await browser.new_page()
            await page.goto(OPTIONS["url"])
        out("ready", "true")
        while True:
            await asyncio.sleep(0.1)
            if should_exit():
                sys.exit(42)


if __name__ == "__main__":
    if OPTIONS["flavor"] == "sync":
        run_sync()
    else:
        asyncio.run(run_async())
