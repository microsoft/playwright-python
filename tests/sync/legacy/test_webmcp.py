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

from typing import Dict, Generator

import pytest

from playwright.sync_api import BrowserType, Error, Page
from tests.server import Server, TestServerRequest

pytestmark = pytest.mark.skip_browser("webkit")

ADD_TOOL = """
  modelContext.registerTool({
    name: 'add',
    description: 'Adds two numbers',
    inputSchema: { type: 'object', properties: { a: { type: 'number' }, b: { type: 'number' } }, required: ['a', 'b'] },
    annotations: { readOnlyHint: true },
    async execute(input) { return { content: [{ type: 'text', text: String(input.a + input.b) }] }; },
  });
"""

ADD_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
    "required": ["a", "b"],
}


def serve_tools(server: Server, tools: str) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(
            f"""<title>WebMCP</title><script>
              const modelContext = document.modelContext || navigator.modelContext;
              {tools}
            </script>""".encode()
        )
        request.finish()

    server.set_route("/webmcp.html", handler)


@pytest.fixture
def page(
    browser_type: BrowserType, launch_arguments: Dict, browser_name: str
) -> Generator[Page, None, None]:
    options: Dict = (
        {
            "firefox_user_prefs": {
                "dom.modelcontext.enabled": True,
                "dom.modelcontext.testing.enabled": True,
            }
        }
        if browser_name == "firefox"
        else {"args": ["--enable-features=WebMCP"]}
    )
    browser = browser_type.launch(**launch_arguments, **options)
    page = browser.new_page()
    yield page
    browser.close()


def test_should_list_tools_registered_by_the_page(page: Page, server: Server) -> None:
    serve_tools(
        server,
        ADD_TOOL
        + """
          modelContext.registerTool({
            name: 'noop',
            description: 'Does nothing',
            async execute() {},
          });
        """,
    )
    page.goto(server.PREFIX + "/webmcp.html")
    # Browsers list tools in their own order.
    tools = sorted(page.webmcp.tools(), key=lambda tool: tool["name"])
    assert tools == [
        {
            "name": "add",
            "description": "Adds two numbers",
            "inputSchema": ADD_SCHEMA,
            "annotations": {"readOnly": True},
        },
        {"name": "noop", "description": "Does nothing"},
    ]
    assert page.main_frame.webmcp.tools() == page.webmcp.tools()


def test_should_report_no_tools_when_the_page_registers_none(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.webmcp.tools() == []


def test_should_call_a_tool(page: Page, server: Server) -> None:
    serve_tools(server, ADD_TOOL)
    page.goto(server.PREFIX + "/webmcp.html")
    assert page.webmcp.call_tool("add", {"a": 2, "b": 40}) == {
        "content": [{"type": "text", "text": "42"}]
    }


def test_should_return_is_error_results_as_is(page: Page, server: Server) -> None:
    serve_tools(
        server,
        """
          modelContext.registerTool({
            name: 'broken',
            description: 'Always fails',
            async execute() { return { content: [{ type: 'text', text: 'nope' }], isError: true }; },
          });
        """,
    )
    page.goto(server.PREFIX + "/webmcp.html")
    assert page.webmcp.call_tool("broken") == {
        "content": [{"type": "text", "text": "nope"}],
        "isError": True,
    }


def test_should_throw_when_the_tool_is_not_registered(
    page: Page, server: Server
) -> None:
    serve_tools(server, ADD_TOOL)
    page.goto(server.PREFIX + "/webmcp.html")
    with pytest.raises(Error, match='No WebMCP tool named "missing"'):
        page.webmcp.call_tool("missing")
