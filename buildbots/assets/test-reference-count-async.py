import asyncio
import gc

import objgraph
import pandas as pd

from playwright.async_api import async_playwright


def print_memory_objects() -> None:
    gc.collect()

    df_dicts = pd.DataFrame()
    df_dicts["dicts"] = objgraph.by_type("dict")
    df_dicts["pw_types"] = df_dicts["dicts"].apply(lambda x: x.get("_type"))

    head = df_dicts["pw_types"].value_counts().head(20)

    for class_name, reference_count in head.items():
        print(class_name, reference_count)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example.com")

        page.on("dialog", lambda dialog: dialog.dismiss())
        for _ in range(100):
            await page.evaluate("""async () => alert()""")

        await page.route("**/", lambda route, request: route.fulfill(body="OK"))

        for i in range(100):
            response = await page.evaluate("""async () => (await fetch("/")).text()""")
            assert response == "OK"

        await browser.close()
    print_memory_objects()

    print("PW-OK")


asyncio.run(main())
