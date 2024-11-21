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
import re
from pathlib import Path
from typing import Dict, List

from playwright.async_api import Browser, BrowserContext, BrowserType, Page, Response
from tests.server import Server
from tests.utils import get_trace_actions, parse_trace


async def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = await browser.new_context()
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    await context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()


async def test_start_stop(browser: Browser) -> None:
    context = await browser.new_context()
    await context.tracing.start()
    await context.tracing.stop()
    await context.close()


async def test_browser_context_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext, server: Server, tmp_path: Path
) -> None:
    await context.tracing.stop()


async def test_browser_context_output_trace_chunk(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = await browser.new_context()
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/grid.html")
    button = page.locator(".box").first

    await context.tracing.start_chunk(title="foo")
    await button.click()
    await context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert Path(tmp_path / "trace1.zip").exists()

    await context.tracing.start_chunk(title="foo")
    await button.click()
    await context.tracing.stop_chunk(path=tmp_path / "trace2.zip")
    assert Path(tmp_path / "trace2.zip").exists()


async def test_should_collect_sources(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(sources=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click("button")
    path = tmp_path / "trace.zip"
    await context.tracing.stop(path=path)

    (resources, events) = parse_trace(path)
    current_file_content = Path(__file__).read_bytes()
    found_current_file = False
    for name, resource in resources.items():
        if resource == current_file_content:
            found_current_file = True
            break
    assert found_current_file


async def test_should_collect_trace_with_resources_but_no_js(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.PREFIX + "/frames/frame.html")
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await page.mouse.move(20, 20)
    await page.mouse.dblclick(30, 30)
    await page.keyboard.insert_text("abc")
    await page.wait_for_timeout(2000)  # Give it some time to produce screenshots.
    await page.route(
        "**/empty.html", lambda route: route.continue_()
    )  # should produce a route.continue_ entry.
    await page.goto(server.EMPTY_PAGE)
    await page.goto(
        server.PREFIX + "/one-style.html"
    )  # should not produce a route.continue_ entry since we continue all routes if no match.
    await page.close()
    trace_file_path = tmpdir / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert events[0]["type"] == "context-options"
    assert get_trace_actions(events) == [
        "Page.goto",
        "Page.set_content",
        "Page.click",
        "Mouse.move",
        "Mouse.dblclick",
        "Keyboard.insert_text",
        "Page.wait_for_timeout",
        "Page.route",
        "Page.goto",
        "Page.goto",
        "Page.close",
    ]

    assert len(list(filter(lambda e: e["type"] == "frame-snapshot", events))) >= 1
    assert len(list(filter(lambda e: e["type"] == "screencast-frame", events))) >= 1
    style = list(
        filter(
            lambda e: e["type"] == "resource-snapshot"
            and e["snapshot"]["request"]["url"].endswith("style.css"),
            events,
        )
    )[0]
    assert style
    assert style["snapshot"]["response"]["content"]["_sha1"]
    script = list(
        filter(
            lambda e: e["type"] == "resource-snapshot"
            and e["snapshot"]["request"]["url"].endswith("script.js"),
            events,
        )
    )[0]
    assert script
    assert script["snapshot"]["response"]["content"].get("_sha1") is None


async def test_should_correctly_determine_sync_apiname(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)

    received_response: "asyncio.Future[None]" = asyncio.Future()

    async def _handle_response(response: Response) -> None:
        await response.request.all_headers()
        await response.text()
        received_response.set_result(None)

    page.once("response", _handle_response)
    await page.goto(server.PREFIX + "/grid.html")
    await received_response
    await page.close()
    trace_file_path = tmpdir / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert events[0]["type"] == "context-options"
    assert get_trace_actions(events) == [
        "Page.goto",
        "Request.all_headers",
        "Response.text",
        "Page.close",
    ]


async def test_should_collect_two_traces(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    tracing1_path = tmpdir / "trace1.zip"
    await context.tracing.stop(path=tracing1_path)

    await context.tracing.start(screenshots=True, snapshots=True)
    await page.dblclick('"Click"')
    await page.close()
    tracing2_path = tmpdir / "trace2.zip"
    await context.tracing.stop(path=tracing2_path)

    (_, events) = parse_trace(tracing1_path)
    assert events[0]["type"] == "context-options"
    assert get_trace_actions(events) == [
        "Page.goto",
        "Page.set_content",
        "Page.click",
    ]

    (_, events) = parse_trace(tracing2_path)
    assert events[0]["type"] == "context-options"
    assert get_trace_actions(events) == ["Page.dblclick", "Page.close"]


async def test_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    await context.tracing.stop()


async def test_should_work_with_playwright_context_managers(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    async with page.expect_console_message() as message_info:
        await page.evaluate('() => console.log("hello")')
        await page.click('"Click"')
    assert (await message_info.value).text == "hello"

    async with page.expect_popup():
        await page.evaluate("window._popup = window.open(document.location.href)")
    trace_file_path = tmpdir / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert events[0]["type"] == "context-options"
    assert get_trace_actions(events) == [
        "Page.goto",
        "Page.set_content",
        "Page.expect_console_message",
        "Page.evaluate",
        "Page.click",
        "Page.expect_popup",
        "Page.evaluate",
    ]


async def test_should_display_wait_for_load_state_even_if_did_not_wait_for_it(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)

    await page.goto(server.EMPTY_PAGE)
    await page.wait_for_load_state("load")
    await page.wait_for_load_state("load")

    trace_file_path = tmpdir / "trace.zip"
    await context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert get_trace_actions(events) == [
        "Page.goto",
        "Page.wait_for_load_state",
        "Page.wait_for_load_state",
    ]


async def test_should_respect_traces_dir_and_name(
    browser_type: BrowserType,
    server: Server,
    tmpdir: Path,
    launch_arguments: Dict,
) -> None:
    traces_dir = tmpdir / "traces"
    browser = await browser_type.launch(traces_dir=traces_dir, **launch_arguments)
    context = await browser.new_context()
    page = await context.new_page()

    await context.tracing.start(name="name1", snapshots=True)
    await page.goto(server.PREFIX + "/one-style.html")
    await context.tracing.stop_chunk(path=tmpdir / "trace1.zip")
    assert (traces_dir / "name1.trace").exists()
    assert (traces_dir / "name1.network").exists()

    await context.tracing.start_chunk(name="name2")
    await page.goto(server.PREFIX + "/har.html")
    await context.tracing.stop(path=tmpdir / "trace2.zip")
    assert (traces_dir / "name2.trace").exists()
    assert (traces_dir / "name2.network").exists()

    await browser.close()

    def resource_names(resources: Dict[str, bytes]) -> List[str]:
        return sorted(
            [
                re.sub(r"^resources/.*\.(html|css)$", r"resources/XXX.\g<1>", file)
                for file in resources.keys()
            ]
        )

    (resources, events) = parse_trace(tmpdir / "trace1.zip")
    assert get_trace_actions(events) == ["Page.goto"]
    assert resource_names(resources) == [
        "resources/XXX.css",
        "resources/XXX.html",
        "trace.network",
        "trace.stacks",
        "trace.trace",
    ]

    (resources, events) = parse_trace(tmpdir / "trace2.zip")
    assert get_trace_actions(events) == ["Page.goto"]
    assert resource_names(resources) == [
        "resources/XXX.css",
        "resources/XXX.html",
        "resources/XXX.html",
        "trace.network",
        "trace.stacks",
        "trace.trace",
    ]


async def test_should_show_tracing_group_in_action_list(
    context: BrowserContext, tmp_path: Path
) -> None:
    await context.tracing.start()
    page = await context.new_page()

    await context.tracing.group("outer group")
    await page.goto("data:text/html,<!DOCTYPE html><body><div>Hello world</div></body>")
    await context.tracing.group("inner group 1")
    await page.locator("body").click()
    await context.tracing.group_end()
    await context.tracing.group("inner group 2")
    await page.get_by_text("Hello").is_visible()
    await context.tracing.group_end()
    await context.tracing.group_end()

    trace_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_path)

    (resources, events) = parse_trace(trace_path)
    actions = get_trace_actions(events)

    assert actions == [
        "BrowserContext.new_page",
        "outer group",
        "Page.goto",
        "inner group 1",
        "Locator.click",
        "inner group 2",
        "Locator.is_visible",
    ]
