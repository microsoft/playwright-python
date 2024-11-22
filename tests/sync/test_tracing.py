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

import re
import threading
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import Browser, BrowserContext, BrowserType, Page, Response
from tests.server import Server
from tests.utils import get_trace_actions, parse_trace


def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()


def test_browser_context_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    context.tracing.stop()


def test_browser_context_output_trace_chunk(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    button = page.locator(".box").first

    context.tracing.start_chunk(title="foo")
    button.click()
    context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert Path(tmp_path / "trace1.zip").exists()

    context.tracing.start_chunk(title="foo")
    button.click()
    context.tracing.stop_chunk(path=tmp_path / "trace2.zip")
    assert Path(tmp_path / "trace2.zip").exists()


def test_should_collect_sources(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    context.tracing.start(sources=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click("button")
    path = tmp_path / "trace.zip"
    context.tracing.stop(path=path)

    (resources, events) = parse_trace(path)
    current_file_content = Path(__file__).read_bytes()
    found_current_file = False
    for name, resource in resources.items():
        if resource == current_file_content:
            found_current_file = True
            break
    assert found_current_file


def test_should_collect_trace_with_resources_but_no_js(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.PREFIX + "/frames/frame.html")
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    page.mouse.move(20, 20)
    page.mouse.dblclick(30, 30)
    page.keyboard.insert_text("abc")
    page.wait_for_timeout(2000)  # Give it some time to produce screenshots.
    page.route(
        "**/empty.html", lambda route: route.continue_()
    )  # should produce a route.continue_ entry.
    page.goto(server.EMPTY_PAGE)
    page.goto(
        server.PREFIX + "/one-style.html"
    )  # should not produce a route.continue_ entry since we continue all routes if no match.
    page.close()
    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

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


def test_should_correctly_determine_sync_apiname(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    received_response = threading.Event()

    def _handle_response(response: Response) -> None:
        response.request.all_headers()
        response.text()
        received_response.set()

    page.once("response", _handle_response)
    page.goto(server.PREFIX + "/grid.html")
    received_response.wait()

    page.close()
    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert events[0]["type"] == "context-options"
    assert get_trace_actions(events) == [
        "Page.goto",
        "Request.all_headers",
        "Response.text",
        "Page.close",
    ]


def test_should_collect_two_traces(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    tracing1_path = tmpdir / "trace1.zip"
    context.tracing.stop(path=tracing1_path)

    context.tracing.start(screenshots=True, snapshots=True)
    page.dblclick('"Click"')
    page.close()
    tracing2_path = tmpdir / "trace2.zip"
    context.tracing.stop(path=tracing2_path)

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


def test_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    context.tracing.stop()


def test_should_work_with_playwright_context_managers(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    with page.expect_console_message() as message_info:
        page.evaluate('() => console.log("hello")')
        page.click('"Click"')
    assert (message_info.value).text == "hello"

    with page.expect_popup():
        page.evaluate("window._popup = window.open(document.location.href)")
    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

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


def test_should_display_wait_for_load_state_even_if_did_not_wait_for_it(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)

    page.goto(server.EMPTY_PAGE)
    page.wait_for_load_state("load")
    page.wait_for_load_state("load")

    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert get_trace_actions(events) == [
        "Page.goto",
        "Page.wait_for_load_state",
        "Page.wait_for_load_state",
    ]


def test_should_respect_traces_dir_and_name(
    browser_type: BrowserType,
    server: Server,
    tmpdir: Path,
    launch_arguments: Any,
) -> None:
    traces_dir = tmpdir / "traces"
    browser = browser_type.launch(traces_dir=traces_dir, **launch_arguments)
    context = browser.new_context()
    page = context.new_page()

    context.tracing.start(name="name1", snapshots=True)
    page.goto(server.PREFIX + "/one-style.html")
    context.tracing.stop_chunk(path=tmpdir / "trace1.zip")
    assert (traces_dir / "name1.trace").exists()
    assert (traces_dir / "name1.network").exists()

    context.tracing.start_chunk(name="name2")
    page.goto(server.PREFIX + "/har.html")
    context.tracing.stop(path=tmpdir / "trace2.zip")
    assert (traces_dir / "name2.trace").exists()
    assert (traces_dir / "name2.network").exists()

    browser.close()

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


def test_should_show_tracing_group_in_action_list(
    context: BrowserContext, tmp_path: Path
) -> None:
    context.tracing.start()
    page = context.new_page()

    context.tracing.group("outer group")
    page.goto("data:text/html,<!DOCTYPE html><body><div>Hello world</div></body>")
    context.tracing.group("inner group 1")
    page.locator("body").click()
    context.tracing.group_end()
    context.tracing.group("inner group 2")
    page.get_by_text("Hello").is_visible()
    context.tracing.group_end()
    context.tracing.group_end()

    trace_path = tmp_path / "trace.zip"
    context.tracing.stop(path=trace_path)

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
