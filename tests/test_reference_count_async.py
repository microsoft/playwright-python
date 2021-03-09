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

import gc

import objgraph
import pandas as pd
import pytest

from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_memory_objects() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com")

        page.on("dialog", lambda dialog: dialog.dismiss())
        for _ in range(100):
            await page.evaluate("""async () => alert()""")

        await page.route("**/", lambda route, _: route.fulfill(body="OK"))

        for _ in range(100):
            response = await page.evaluate("""async () => (await fetch("/")).text()""")
            assert response == "OK"

        await browser.close()

    gc.collect()

    df_dicts = pd.DataFrame()
    df_dicts["dicts"] = objgraph.by_type("dict")
    df_dicts["pw_types"] = df_dicts["dicts"].apply(lambda x: x.get("_type"))

    head = df_dicts["pw_types"].value_counts().head(20)
    assert "Dialog" not in head.items()
    assert "Request" not in head.items()
    assert "Route" not in head.items()
