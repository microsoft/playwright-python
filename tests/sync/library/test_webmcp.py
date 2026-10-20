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

"""Port of tests/library/webmcp.spec.ts."""

from typing import Any, Callable, Dict, Generator

import pytest

from playwright.sync_api import Browser, BrowserType, Error, Page
from tests.server import Server, TestServerRequest

pytestmark = pytest.mark.skip_browser("webkit")


@pytest.fixture(scope="module")
def browser(
    browser_name: str, browser_type: BrowserType, launch_arguments: Dict
) -> Generator[Browser, None, None]:
    # Port of test.use({ launchOptions }) that enables WebMCP.
    if browser_name == "webkit":
        pytest.skip("WebKit does not implement WebMCP")
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
    yield browser
    browser.close()


def register_script(tools: str) -> str:
    return f"""<script>
    const modelContext = document.modelContext || navigator.modelContext;
    {tools}
  </script>"""


ADD = """
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


def serve(server: Server, path: str, body: str) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(f"<title>WebMCP</title>{body}".encode())
        request.finish()

    server.set_route(path, handle)


def register_echo(text: str) -> str:
    return register_script(
        f"""
    modelContext.registerTool({{
      name: 'echo',
      description: 'Echoes',
      async execute() {{ return {{ content: [{{ type: 'text', text: '{text}' }}] }}; }},
    }});
  """
    )


def register_named_echo(text: str) -> str:
    return register_script(
        f"""
    modelContext.registerTool({{
      name: 'echo-{text}',
      description: 'Echoes {text}',
      async execute() {{ return {{ content: [{{ type: 'text', text: '{text}' }}] }}; }},
    }});
  """
    )


def test_WM_001_should_list_tools_registered_by_the_page(
    page: Page, server: Server
) -> None:
    serve(
        server,
        "/",
        register_script(
            ADD
            + """
    modelContext.registerTool({
      name: 'noop',
      description: 'Does nothing',
      async execute() {},
    });
  """
        ),
    )
    page.goto(server.PREFIX + "/")

    # Browsers list tools in their own order.
    tools = sorted(page.webmcp.tools(), key=lambda tool: tool["name"])
    assert tools == [
        {
            "name": "add",
            "description": "Adds two numbers",
            "inputSchema": ADD_SCHEMA,
            "annotations": {"readOnly": True},
        },
        {
            "name": "noop",
            "description": "Does nothing",
        },
    ]


def test_WM_002_should_report_no_tools_when_the_page_registers_none(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert page.webmcp.tools() == []


def test_WM_003_should_call_a_tool(page: Page, server: Server) -> None:
    serve(server, "/", register_script(ADD))
    page.goto(server.PREFIX + "/")

    assert page.webmcp.call_tool("add", {"a": 2, "b": 40}) == {
        "content": [{"type": "text", "text": "42"}]
    }


def test_WM_004_should_return_is_error_results_as_is(
    page: Page, server: Server
) -> None:
    serve(
        server,
        "/",
        register_script(
            """
    modelContext.registerTool({
      name: 'broken',
      description: 'Always fails',
      async execute() { return { content: [{ type: 'text', text: 'nope' }], isError: true }; },
    });
  """
        ),
    )
    page.goto(server.PREFIX + "/")

    assert page.webmcp.call_tool("broken") == {
        "content": [{"type": "text", "text": "nope"}],
        "isError": True,
    }


def test_WM_005_should_throw_when_the_tool_throws(
    page: Page, server: Server, browser_name: str
) -> None:
    serve(
        server,
        "/",
        register_script(
            """
    modelContext.registerTool({
      name: 'throwing',
      description: 'Throws',
      async execute() { throw new Error('boom'); },
    });
  """
        ),
    )
    page.goto(server.PREFIX + "/")

    with pytest.raises(Error) as exc_info:
        page.webmcp.call_tool("throwing")
    # Chromium does not report the error that the tool threw.
    assert (
        "the invocation failed" if browser_name == "chromium" else "boom"
    ) in exc_info.value.message


def test_WM_006_should_throw_for_an_unknown_tool(page: Page, server: Server) -> None:
    serve(server, "/", register_script(ADD))
    page.goto(server.PREFIX + "/")

    with pytest.raises(Error) as exc_info:
        page.webmcp.call_tool("missing")
    assert 'No WebMCP tool named "missing"' in exc_info.value.message
    assert "Available tools: add" in exc_info.value.message


def test_WM_007_should_time_out_when_the_tool_does_not_settle(
    page: Page, server: Server
) -> None:
    serve(
        server,
        "/",
        register_script(
            """
    modelContext.registerTool({
      name: 'stuck',
      description: 'Never resolves',
      execute() { return new Promise(() => {}); },
    });
  """
        ),
    )
    page.goto(server.PREFIX + "/")

    with pytest.raises(Error) as exc_info:
        page.webmcp.call_tool("stuck", {}, timeout=500)
    assert "Timeout 500ms exceeded" in exc_info.value.message


def test_WM_008_should_drop_tools_after_navigation(page: Page, server: Server) -> None:
    serve(server, "/", register_script(ADD))
    page.goto(server.PREFIX + "/")
    assert len(page.webmcp.tools()) == 1

    page.goto(server.EMPTY_PAGE)
    assert page.webmcp.tools() == []
    with pytest.raises(Error) as exc_info:
        page.webmcp.call_tool("add", {"a": 1, "b": 1})
    assert "The frame does not register any WebMCP tools" in exc_info.value.message


def test_WM_009_should_list_a_tool_registered_after_load(
    page: Page, server: Server
) -> None:
    serve(server, "/", register_script(ADD))
    page.goto(server.PREFIX + "/")
    assert len(page.webmcp.tools()) == 1

    page.evaluate(
        """() => {
      const modelContext = document.modelContext || navigator.modelContext;
      modelContext.registerTool({ name: 'late', description: 'Registered later', async execute() {} });
    }"""
    )
    tools = sorted(page.webmcp.tools(), key=lambda tool: tool["name"])
    assert [tool["name"] for tool in tools] == ["add", "late"]


def test_WM_010_should_list_tools_while_a_tool_is_running(
    page: Page, server: Server, sync_gather: Callable[..., Any]
) -> None:
    serve(
        server,
        "/",
        register_script(
            ADD
            + """
    modelContext.registerTool({
      name: 'gated',
      description: 'Resolves when released',
      execute() { return new Promise(resolve => window.release = () => resolve({ content: [{ type: 'text', text: 'released' }] })); },
    });
  """
        ),
    )
    page.goto(server.PREFIX + "/")

    def list_tools_and_release() -> None:
        page.wait_for_function("() => !!window.release")
        assert len(page.webmcp.tools()) == 2
        page.evaluate("() => window.release()")

    [result, _] = sync_gather(
        lambda: page.webmcp.call_tool("gated"), list_tools_and_release
    )
    assert result == {"content": [{"type": "text", "text": "released"}]}


def test_WM_011_should_list_declarative_tools(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name != "chromium":
        pytest.skip("Only Chromium implements declarative tools")
    serve(
        server,
        "/",
        """
    <form toolname="subscribe" tooldescription="Subscribes to the newsletter">
      <input name="email" type="email">
      <button>Subscribe</button>
    </form>
  """,
    )
    page.goto(server.PREFIX + "/")

    tools = page.webmcp.tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "subscribe"
    assert tools[0]["description"] == "Subscribes to the newsletter"
    input_schema = tools[0]["inputSchema"]
    assert input_schema
    assert input_schema["type"] == "object"
    assert input_schema["properties"] == {"email": {"type": "string"}}

    # A declarative tool waits for the user to submit the form.
    with pytest.raises(Error) as exc_info:
        page.webmcp.call_tool("subscribe", {"email": "me@example.com"}, timeout=500)
    assert "Timeout 500ms exceeded" in exc_info.value.message


def test_WM_012_should_scope_tools_to_their_frame(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "Firefox does not support registering WebMCP tools in iframes yet, https://bugzilla.mozilla.org/show_bug.cgi?id=2019743"
        )
    serve(server, "/", register_script(ADD) + '<iframe src="/frame.html"></iframe>')
    serve(
        server,
        "/frame.html",
        register_script(
            """
    modelContext.registerTool({
      name: 'subscribe',
      description: 'Subscribes to the newsletter',
      async execute() { return { content: [{ type: 'text', text: 'subscribed' }] }; },
    });
  """
        ),
    )
    page.goto(server.PREFIX + "/")

    child_frame = page.frames[1]
    main_tools = page.webmcp.tools()
    assert len(main_tools) == 1
    assert main_tools[0]["name"] == "add"
    child_tools = child_frame.webmcp.tools()
    assert len(child_tools) == 1
    assert child_tools[0]["name"] == "subscribe"
    assert child_frame.webmcp.call_tool("subscribe") == {
        "content": [{"type": "text", "text": "subscribed"}]
    }

    with pytest.raises(Error) as exc_info:
        page.webmcp.call_tool("subscribe")
    assert 'No WebMCP tool named "subscribe"' in exc_info.value.message
    assert "Available tools: add" in exc_info.value.message


def test_WM_013_should_call_same_name_tools_in_their_own_frame(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "Firefox does not support registering WebMCP tools in iframes yet, https://bugzilla.mozilla.org/show_bug.cgi?id=2019743"
        )
    serve(server, "/", register_echo("main") + '<iframe src="/frame.html"></iframe>')
    serve(server, "/frame.html", register_echo("frame"))
    page.goto(server.PREFIX + "/")
    child_frame = page.frames[1]

    assert page.webmcp.call_tool("echo") == {
        "content": [{"type": "text", "text": "main"}]
    }
    assert child_frame.webmcp.call_tool("echo") == {
        "content": [{"type": "text", "text": "frame"}]
    }


def test_WM_014_should_list_and_call_tools_in_cross_origin_and_nested_frames(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "Firefox does not support registering WebMCP tools in iframes yet, https://bugzilla.mozilla.org/show_bug.cgi?id=2019743"
        )
    serve(
        server,
        "/",
        register_named_echo("main")
        + f'<iframe allow="tools" src="{server.CROSS_PROCESS_PREFIX}/frame.html"></iframe>',
    )
    serve(
        server,
        "/frame.html",
        register_named_echo("frame") + '<iframe src="/nested.html"></iframe>',
    )
    serve(server, "/nested.html", register_named_echo("nested"))
    page.goto(server.PREFIX + "/")

    [main_frame, frame, nested] = page.frames
    assert main_frame.webmcp.tools() == [
        {"name": "echo-main", "description": "Echoes main"}
    ]
    assert frame.webmcp.tools() == [
        {"name": "echo-frame", "description": "Echoes frame"}
    ]
    assert nested.webmcp.tools() == [
        {"name": "echo-nested", "description": "Echoes nested"}
    ]
    assert frame.webmcp.call_tool("echo-frame") == {
        "content": [{"type": "text", "text": "frame"}]
    }
    assert nested.webmcp.call_tool("echo-nested") == {
        "content": [{"type": "text", "text": "nested"}]
    }
