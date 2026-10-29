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

"""Port of tests/page/page-aria-snapshot-ai.spec.ts."""

import asyncio
import base64
import re
from typing import Optional

import pytest

from playwright.async_api import Error, Page, expect
from tests.helpers.aria_snapshot import assert_contains_yaml, unshift
from tests.server import Server, TestServerRequest, reactor


async def snapshot_for_ai(
    page: Page, depth: Optional[int] = None, timeout: Optional[float] = None
) -> str:
    return await page.aria_snapshot(mode="ai", depth=depth, timeout=timeout)


def serve_html(server: Server, path: str, body: str) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(body.encode())
        request.finish()

    server.set_route(path, handler)


async def test_AR_048_should_generate_refs(page: Page) -> None:
    await page.set_content(
        """
    <button>One</button>
    <button>Two</button>
    <button>Three</button>
  """
    )

    snapshot1 = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot1,
        """
    - generic [active] [ref=e1]:
      - button "One" [ref=e2]
      - button "Two" [ref=e3]
      - button "Three" [ref=e4]
  """,
    )
    await expect(page.get_by_ref("e2")).to_have_text("One")
    await expect(page.get_by_ref("e3")).to_have_text("Two")
    await expect(page.get_by_ref("e4")).to_have_text("Three")

    await page.get_by_ref("e3").evaluate("e => { e.textContent = 'Not Two'; }")

    snapshot2 = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot2,
        """
    - generic [active] [ref=e1]:
      - button "One" [ref=e2]
      - button "Not Two" [ref=e5]
      - button "Three" [ref=e4]
  """,
    )


async def test_AR_049_should_list_iframes(page: Page) -> None:
    await page.set_content(
        """
    <h1>Hello</h1>
    <iframe name="foo" src="data:text/html,<h1>World</h1>">
  """
    )

    snapshot1 = await snapshot_for_ai(page)
    assert "- iframe" in snapshot1

    frame_snapshot = await page.frame_locator("iframe").locator("body").aria_snapshot()
    assert frame_snapshot == '- heading "World" [level=1]'


async def test_AR_050_should_snapshot_a_locator_inside_an_iframe(page: Page) -> None:
    await page.set_content(
        """
    <h1>Main Page</h1>
    <iframe srcdoc="<ul><li>Item 1</li><li>Item 2</li></ul>"></iframe>
  """
    )

    list_ = page.frames[1].locator("ul")
    snapshot = await list_.aria_snapshot(mode="ai")
    assert_contains_yaml(
        snapshot,
        """
    - list [ref=f1e1]:
      - listitem [ref=f1e2]: Item 1
      - listitem [ref=f1e3]: Item 2
  """,
    )


async def test_AR_051_should_limit_depth_across_iframe_boundary(page: Page) -> None:
    await page.set_content(
        """
    <nav>
      <iframe srcdoc="<ul><li><button>Deep</button></li></ul>"></iframe>
    </nav>
  """
    )

    snapshot = await snapshot_for_ai(page, depth=3)
    assert_contains_yaml(
        snapshot,
        """
    - navigation [ref=e2]:
      - iframe [ref=e3]:
        - list [ref=f1e2]:
          - listitem [ref=f1e3]
  """,
    )
    assert "button" not in snapshot


async def test_AR_052_should_stitch_all_frame_snapshots(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - iframe [ref=e2]:
        - generic [ref=f1e1]:
          - iframe [ref=f1e2]:
            - generic [ref=f3e1]: Hi, I'm frame
          - iframe [ref=f1e3]:
            - generic [ref=f4e1]: Hi, I'm frame
      - iframe [ref=e3]:
        - generic [ref=f2e1]: Hi, I'm frame
  """,
    )

    href = await page.get_by_ref("e1").evaluate(
        "e => e.ownerDocument.defaultView.location.href"
    )
    assert href == server.PREFIX + "/frames/nested-frames.html"

    href2 = await page.get_by_ref("f1e2").evaluate(
        "e => e.ownerDocument.defaultView.location.href"
    )
    assert href2 == server.PREFIX + "/frames/two-frames.html"

    href3 = await page.get_by_ref("f4e2").evaluate(
        "e => e.ownerDocument.defaultView.location.href"
    )
    assert href3 == server.PREFIX + "/frames/frame.html"

    resolved = await page.get_by_ref("e1").normalize()
    assert str(resolved) == 'locator("body")'

    resolved = await page.get_by_ref("f4e2").normalize()
    assert (
        str(resolved)
        == 'locator("iframe[name=\\"2frames\\"]").content_frame.locator("iframe[name=\\"dos\\"]").content_frame.get_by_text("Hi, I\'m frame")'
    )

    # Should tolerate .describe().
    resolved = await page.get_by_ref("f3e2").describe("foo bar").normalize()
    assert (
        str(resolved)
        == 'locator("iframe[name=\\"2frames\\"]").content_frame.locator("iframe[name=\\"uno\\"]").content_frame.get_by_text("Hi, I\'m frame")'
    )

    with pytest.raises(Error) as exc_info:
        await page.get_by_ref("e1000").normalize()
    assert "No element matching aria-ref=e1000" in exc_info.value.message

    await page.locator("iframe").evaluate_all(
        """iframes => {
            for (const iframe of iframes)
                iframe.textContent = 'Your browser does not support frames';
        }"""
    )
    assert await snapshot_for_ai(page) == snapshot


async def test_AR_053_should_re_number_refs_across_navigations_but_not_same_document_navigations(
    page: Page, server: Server
) -> None:
    serve_html(server, "/one.html", "<button>One</button>")
    serve_html(server, "/two.html", "<button>Two</button>")

    # The first committed document keeps the base seq, so the main frame has no prefix.
    await page.goto(server.PREFIX + "/one.html")
    one_match = re.search(r'button "One" \[ref=(e\d+)\]', await snapshot_for_ai(page))
    assert one_match
    one_ref = one_match[1]
    await expect(page.get_by_ref(one_ref)).to_have_text("One")

    # Cross-document navigation re-numbers the main frame, so its refs gain a frame prefix.
    await page.goto(server.PREFIX + "/two.html")
    two_match = re.search(
        r'button "Two" \[ref=(f\d+e\d+)\]', await snapshot_for_ai(page)
    )
    assert two_match
    two_ref = two_match[1]
    await expect(page.get_by_ref(two_ref)).to_have_text("Two")

    # The stale ref from the previous document must not resolve against the new one.
    with pytest.raises(Error) as exc_info:
        await page.get_by_ref(one_ref).normalize()
    assert f"No element matching aria-ref={one_ref}" in exc_info.value.message

    # Same-document navigation keeps refs intact.
    await page.evaluate("() => history.pushState({}, '', '/pushed.html')")
    assert f'button "Two" [ref={two_ref}]' in await snapshot_for_ai(page)
    await expect(page.get_by_ref(two_ref)).to_have_text("Two")


async def test_AR_054_should_persist_iframe_references(page: Page) -> None:
    await page.set_content(
        """
    <ul>
      <li><iframe srcdoc="<button>button1</button>"></iframe></li>
      <li><iframe srcdoc="<button>button2</button>"></iframe></li>
    </ul>
  """
    )
    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - list [ref=e2]:
      - listitem [ref=e3]:
        - iframe [ref=e4]:
          - button "button1" [ref=f1e2]
      - listitem [ref=e5]:
        - iframe [ref=e6]:
          - button "button2" [ref=f2e2]
  """,
    )

    await page.evaluate("() => document.querySelector('iframe').remove()")
    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - list [ref=e2]:
      - listitem [ref=e3]
      - listitem [ref=e5]:
        - iframe [ref=e6]:
          - button "button2" [ref=f2e2]
  """,
    )
    await expect(page.get_by_ref("f2e2")).to_have_text("button2")

    await page.evaluate(
        """() => {
    const frame = document.createElement('iframe');
    frame.setAttribute('srcdoc', '<button>button1</button>');
    document.querySelector('li').appendChild(frame);
  }"""
    )
    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - list [ref=e2]:
      - listitem [ref=e3]:
        - iframe [ref=e7]:
          - button "button1" [ref=f3e2]
      - listitem [ref=e5]:
        - iframe [ref=e6]:
          - button "button2" [ref=f2e2]
  """,
    )
    await expect(page.get_by_ref("f3e2")).to_have_text("button1")
    await expect(page.get_by_ref("f2e2")).to_have_text("button2")


async def test_AR_055_should_not_generate_refs_for_elements_with_pointer_events_none(
    page: Page,
) -> None:
    await page.set_content(
        """
    <button style="pointer-events: none">no-ref</button>
    <div style="pointer-events: none">
      <button style="pointer-events: auto">with-ref</button>
    </div>
    <div style="pointer-events: none">
      <div style="pointer-events: initial">
        <button>with-ref</button>
      </div>
    </div>
    <div style="pointer-events: none">
      <div style="pointer-events: auto">
        <button>with-ref</button>
      </div>
    </div>
    <div style="pointer-events: auto">
      <div style="pointer-events: none">
        <button>no-ref</button>
      </div>
    </div>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - button "no-ref"
      - button "with-ref" [ref=e2]
      - button "with-ref" [ref=e4]
      - button "with-ref" [ref=e6]
      - generic [ref=e7]:
        - generic:
          - button "no-ref"
  """,
    )


async def test_AR_056_emit_generic_roles_for_nodes_w_o_roles(page: Page) -> None:
    await page.set_content(
        """
    <style>
    input {
      width: 0;
      height: 0;
      opacity: 0;
    }
    </style>
    <div>
      <label>
        <span>
          <input type="radio" value="Apple" checked="">
        </span>
        <span>Apple</span>
      </label>
      <label>
        <span>
          <input type="radio" value="Pear">
        </span>
        <span>Pear</span>
      </label>
      <label>
        <span>
          <input type="radio" value="Orange">
        </span>
        <span>Orange</span>
      </label>
    </div>
  """
    )

    snapshot = await snapshot_for_ai(page)

    assert_contains_yaml(
        snapshot,
        """
    - generic [ref=e2]:
      - generic [ref=e3]:
        - generic [ref=e4]:
          - radio "Apple" [checked]
        - text: Apple
      - generic [ref=e5]:
        - generic [ref=e6]:
          - radio "Pear"
        - text: Pear
      - generic [ref=e7]:
        - generic [ref=e8]:
          - radio "Orange"
        - text: Orange
  """,
    )


async def test_AR_057_should_collapse_generic_nodes(page: Page) -> None:
    await page.set_content(
        """
    <div>
      <div>
        <div>
          <button>Button</button>
        </div>
      </div>
    </div>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - button "Button" [ref=e5]
  """,
    )


async def test_AR_058_should_include_cursor_pointer_hint(page: Page) -> None:
    await page.set_content(
        """
    <button style="cursor: pointer">Button</button>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - button "Button" [ref=e2] [cursor=pointer]
  """,
    )


async def test_AR_059_should_not_nest_cursor_pointer_hints(page: Page) -> None:
    await page.set_content(
        """
    <a style="cursor: pointer" href="about:blank">
      Link with a button
      <button style="cursor: pointer">Button</button>
    </a>
  """
    )

    snapshot = await snapshot_for_ai(page)
    # The link's name is redundant - "Link with a button" prints as text and "Button" as the button -
    # so it is dropped even though the node is clickable.
    assert_contains_yaml(
        snapshot,
        """
    - link [ref=e2] [cursor=pointer]:
      - /url: about:blank
      - text: Link with a button
      - button "Button" [ref=e3]
  """,
    )


async def test_AR_060_should_omit_names_that_just_repeat_printed_descendant_nodes(
    page: Page,
) -> None:
    await page.set_content(
        """
    <h3><a style="cursor: pointer" href="/issues/1">Clipboard API</a></h3>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - heading [level=3] [ref=e2]:
      - link "Clipboard API" [ref=e3] [cursor=pointer]:
        - /url: /issues/1
  """,
    )


async def test_AR_061_should_omit_redundant_name_when_a_contributing_wrapper_is_collapsed(
    page: Page,
) -> None:
    # The flex span contributes to the heading's name, but is then removed from the tree as a
    # single-child generic wrapper. Its contribution is fully represented by the link, so the
    # heading's name is still redundant.
    await page.set_content(
        """
    <h3><span style="display: flex"><a style="cursor: pointer" href="/issues/1">Clipboard API</a></span></h3>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - heading [level=3] [ref=e2]:
      - link "Clipboard API" [ref=e4] [cursor=pointer]:
        - /url: /issues/1
  """,
    )


async def test_AR_062_should_omit_redundant_name_when_a_contributor_is_a_skipped_leaf_generic(
    page: Page,
) -> None:
    # The outer span is not collapsed (its child is an element, not text), so it becomes a leaf
    # generic node that contributes to both names. The link's rendered name covers it, which in turn
    # makes the heading's name redundant.
    await page.set_content(
        """
    <h3><a style="cursor: pointer" href="/issues/1"><span><span>Clipboard API</span></span></a></h3>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - heading [level=3] [ref=e2]:
      - link "Clipboard API" [ref=e3] [cursor=pointer]:
        - /url: /issues/1
  """,
    )


async def test_AR_063_should_keep_the_name_when_the_contributing_wrapper_collapses_into_repeating_text(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/41985
    # https://github.com/microsoft/playwright/issues/43315
    # The outer span is marked as represented while it still wraps the icon. Once the nameless
    # image is dropped, the span collapses into a lone text repeating the button's name and removes
    # itself, so the button must keep the name derived from it.
    # A wrapper that only adds whitespace to the name - a stray text node, or the spacing around an
    # inline-block icon - is not where the name comes from.
    await page.set_content(
        """
    <button>
      <span>
        <span>
          <svg focusable="false" tabindex="-1" aria-hidden="true" viewBox="0 0 448 512">
            <path d="M416 208H272V64c0-17.67-14.33-32-32-32h-32c-17.67 0-32 14.33-32 32v144H32c-17.67 0-32 14.33-32 32v32c0 17.67 14.33 32 32 32h144v144c0 17.67 14.33 32 32 32h32c17.67 0 32-14.33 32-32V304h144c17.67 0 32-14.33 32-32v-32c0-17.67-14.33-32-32-32z"/>
          </svg>
        </span>
        <span>Add New Item</span>
      </span>
    </button>
    <button><span>\n  <svg aria-hidden="true"></svg></span>New survey</button>
    <button><span><svg aria-hidden="true" style="width: 1em; height: 1em; display: inline-block"></svg></span>Edit survey</button>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - button "Add New Item" [ref=e2]
      - button "New survey" [ref=e7]
      - button "Edit survey" [ref=e10]
  """,
    )


async def test_AR_064_should_keep_names_not_derived_from_printed_nodes(
    page: Page,
) -> None:
    await page.set_content(
        """
    <h3 aria-label="Clipboard API issue"><a style="cursor: pointer" href="/issues/1">Clipboard API</a></h3>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - heading "Clipboard API issue" [level=3] [ref=e2]:
      - link "Clipboard API" [ref=e3] [cursor=pointer]:
        - /url: /issues/1
  """,
    )


async def test_AR_065_should_omit_images_without_an_accessible_name(
    page: Page,
) -> None:
    await page.set_content(
        """
    <img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=">
    <img alt="A cat" src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=">
    <img style="cursor: pointer" src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=">
  """
    )

    snapshot = await snapshot_for_ai(page)
    # A nameless image that cannot be clicked carries no information and is omitted.
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - img "A cat" [ref=e3]
      - img [ref=e4] [cursor=pointer]
  """,
    )
    assert "[ref=e2]" not in snapshot


async def test_AR_066_should_omit_a_nameless_image_nested_inside_a_link(
    page: Page,
) -> None:
    # The decorative image has no name, so it is dropped even though it sits inside a clickable link.
    await page.set_content(
        """
    <a style="cursor: pointer" href="/issue/1">Open issue <img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA="></a>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - link "Open issue" [ref=e2] [cursor=pointer]:
      - /url: /issue/1
  """,
    )
    assert "img" not in snapshot


async def test_AR_067_should_keep_icon_only_clickable_elements(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/42013
    icon = '<svg viewBox="0 0 1024 1024"><use xlink:href="#icon"></use></svg>'
    await page.set_content(
        f"""
    <div style="cursor: pointer" aria-haspopup="true"><i>{icon}</i></div>
    <img style="cursor: pointer" src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=">
    <a style="cursor: pointer" href="/target">{icon}</a>
    <div onclick="void 0">{icon}</div>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - generic [ref=e2] [cursor=pointer]
      - img [ref=e5] [cursor=pointer]
      - link [ref=e6] [cursor=pointer]:
        - /url: /target
  """,
    )


async def test_AR_068_should_omit_leaf_generic_whose_text_is_already_in_an_ancestor_name(
    page: Page,
) -> None:
    # The inner element is block so it survives as its own generic node (an inline single-text span
    # would be collapsed into the link instead). It inherits the link's pointer cursor.
    await page.set_content(
        """
    <a style="cursor: pointer" href="/issues/15860"><div>[Feature] a dedicated clipboard API</div></a>
  """
    )

    snapshot = await snapshot_for_ai(page)
    # The link keeps its name, and the inner leaf generic that the name was computed from is dropped
    # because its text is already shown by the name.
    assert_contains_yaml(
        snapshot,
        """
    - link "[Feature] a dedicated clipboard API" [ref=e2] [cursor=pointer]:
      - /url: /issues/15860
  """,
    )
    assert "[ref=e3]" not in snapshot


async def test_AR_069_should_omit_name_repeating_generic_behind_a_wrapper(
    page: Page,
) -> None:
    # The leaf generic that repeats the link's name sits inside a nameless wrapper. Its text is
    # first inlined into the wrapper, which then faces the link and removes itself.
    await page.set_content(
        """
    <a style="cursor: pointer" href="/labels"><span style="display: inline-block"><span style="display: inline-block"><span>P3-collecting-feedback</span></span></span></a>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - link "P3-collecting-feedback" [ref=e2] [cursor=pointer]:
      - /url: /labels
  """,
    )
    assert len(snapshot.split("P3-collecting-feedback")) == 2


async def test_AR_070_should_resolve_refs_of_distilled_away_nodes(page: Page) -> None:
    await page.set_content(
        """
    <a style="cursor: pointer" href="/issues/15860"><div>[Feature] a dedicated clipboard API</div></a>
  """
    )

    snapshot = await snapshot_for_ai(page)
    # The inner leaf generic is distilled away, but its ref still resolves to the element.
    assert "[ref=e3]" not in snapshot
    await expect(page.get_by_ref("e3")).to_have_text(
        "[Feature] a dedicated clipboard API"
    )


async def test_AR_071_should_not_distill_snapshots_outside_of_ai_mode(
    page: Page,
) -> None:
    await page.set_content(
        """
    <h3><a href="/issues/1">Clipboard API</a></h3>
  """
    )

    # The heading name would be dropped as redundant in ai mode; matching mode keeps it.
    await expect(page.locator("body")).to_match_aria_snapshot(
        """
    - heading "Clipboard API" [level=3]:
      - link "Clipboard API":
        - /url: /issues/1
  """
    )


async def test_AR_072_should_truncate_data_url_in_link(page: Page) -> None:
    b64 = base64.b64encode(b"<p>hello</p>").decode()
    await page.set_content(f'<a href="data:text/html;base64,{b64}">a link</a>')
    snapshot = await snapshot_for_ai(page)
    assert "/url: data:text/html;base64,…" in snapshot
    assert b64 not in snapshot


async def test_AR_073_should_gracefully_fallback_when_child_frame_cant_be_captured(
    page: Page, server: Server
) -> None:
    await page.set_content(
        f"""
    <p>Test</p>
    <iframe src="{server.PREFIX}/redirectloop1.html#depth=100000"></iframe>
  """,
        wait_until="domcontentloaded",
    )
    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - paragraph [ref=e2]: Test
      - iframe [ref=e3]
  """,
    )


async def test_AR_074_should_auto_wait_for_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/frame.html")
    _, snapshot = await asyncio.gather(
        page.evaluate("() => window.location.reload()"),
        snapshot_for_ai(page),
    )
    # The snapshot races the reload, which may re-number the main frame, so accept any ref.
    assert re.search(
        r"- generic \[active\] \[ref=(?:f\d+)?e\d+\]: Hi, I'm frame", snapshot
    )


async def test_AR_075_should_auto_wait_for_blocking_css(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")

        def finish() -> None:
            request.write(b"body { monospace }")
            request.finish()

        reactor.callLater(1, finish)

    server.set_route("/css", handler)
    await page.set_content(
        f"""
    <script src="{server.PREFIX}/css"></script>
    <p>Hello World</p>
  """,
        wait_until="commit",
    )
    assert_contains_yaml(await snapshot_for_ai(page), "Hello World")


async def test_AR_076_should_show_visible_children_of_hidden_elements(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36296
    await page.set_content(
        """
    <div style="visibility: hidden">
      <div style="visibility: visible">
        <button>Visible</button>
      </div>
      <div style="visibility: hidden">
        <button style="visibility: visible">Visible</button>
      </div>
      <div>
        <div style="visibility: visible">
          <button style="visibility: hidden">Hidden</button>
        </div>
        <button>Hidden</button>
      </div>
    </div>
  """
    )

    assert await snapshot_for_ai(page) == unshift(
        """
    - generic [active] [ref=e1]:
      - button "Visible" [ref=e3]
      - button "Visible" [ref=e4]
  """
    )


async def test_AR_077_should_include_active_element_information(page: Page) -> None:
    await page.set_content(
        """
    <button id="btn1">Button 1</button>
    <button id="btn2" autofocus>Button 2</button>
    <div>Not focusable</div>
  """
    )

    # Wait for autofocus to take effect
    await page.wait_for_function("() => document.activeElement?.id === 'btn2'")

    snapshot = await snapshot_for_ai(page)

    assert_contains_yaml(
        snapshot,
        """
    - generic [ref=e1]:
      - button "Button 1" [ref=e2]
      - button "Button 2" [active] [ref=e3]
      - generic [ref=e4]: Not focusable
  """,
    )


async def test_AR_078_should_update_active_element_on_focus(page: Page) -> None:
    await page.set_content(
        """
    <input id="input1" placeholder="First input">
    <input id="input2" placeholder="Second input">
  """
    )

    # Initially there shouldn't be an active element on the inputs
    initial_snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        initial_snapshot,
        """
    - generic [active] [ref=e1]:
      - textbox "First input" [ref=e2]
      - textbox "Second input" [ref=e3]
  """,
    )

    # Focus the second input
    await page.locator("#input2").focus()

    # After focus, the second input should be active
    after_focus_snapshot = await snapshot_for_ai(page)

    assert_contains_yaml(
        after_focus_snapshot,
        """
    - generic [ref=e1]:
      - textbox "First input" [ref=e2]
      - textbox "Second input" [active] [ref=e3]
  """,
    )


async def test_AR_079_should_mark_iframe_as_active_when_it_contains_focused_element(
    page: Page,
) -> None:
    # Create a simple HTML file for the iframe
    await page.set_content(
        """
    <input id="regular-input" placeholder="Regular input">
    <iframe src="data:text/html,<input id='iframe-input' placeholder='Input in iframe'>" tabindex="0"></iframe>
  """
    )

    # Test 1: Focus the input inside the iframe
    await page.frame_locator("iframe").locator("#iframe-input").focus()
    input_in_iframe_focused_snapshot = await snapshot_for_ai(page)

    # The iframe should be marked as active when it contains a focused element
    assert_contains_yaml(
        input_in_iframe_focused_snapshot,
        """
    - generic [ref=e1]:
      - textbox "Regular input" [ref=e2]
      - iframe [active] [ref=e3]:
        - textbox "Input in iframe" [active] [ref=f1e2]
  """,
    )


async def test_AR_080_return_empty_snapshot_when_iframe_is_not_loaded(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/pull/36710
    await page.set_content(
        f"""
    <div style="height: 5000px;">Test</div>
    <iframe loading="lazy" src="{server.PREFIX}/frame.html"></iframe>
  """
    )

    # Wait for the iframe to load
    await page.wait_for_selector("iframe")

    # Get the snapshot of the page
    snapshot = await snapshot_for_ai(page, timeout=3000)

    # The iframe should be present but empty
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - generic [ref=e2]: Test
      - iframe [ref=e3]
  """,
    )


async def test_AR_081_should_support_many_properties_on_iframes(page: Page) -> None:
    await page.set_content(
        """
    <input id="regular-input" placeholder="Regular input">
    <iframe style='cursor: pointer' src="data:text/html,<input id='iframe-input' placeholder='Input in iframe'/>" tabindex="0"></iframe>
  """
    )

    # Test 1: Focus the input inside the iframe
    await page.frame_locator("iframe").locator("#iframe-input").focus()
    input_in_iframe_focused_snapshot = await snapshot_for_ai(page)

    assert_contains_yaml(
        input_in_iframe_focused_snapshot,
        """
    - generic [ref=e1]:
      - textbox "Regular input" [ref=e2]
      - iframe [active] [ref=e3] [cursor=pointer]:
        - textbox "Input in iframe" [active] [ref=f1e2]
  """,
    )


async def test_AR_082_should_snapshot_frameset_pages(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/41784
    serve_html(
        server,
        "/frameset.html",
        '<frameset rows="50%,50%"><frameset cols="50%,50%"><frame src="/frame-one.html"><frame src="/frame-two.html"></frameset><frame src="/frame-three.html"></frameset>',
    )
    for name in ["one", "two", "three"]:
        serve_html(server, f"/frame-{name}.html", f"<button>Button {name}</button>")
    await page.goto(server.PREFIX + "/frameset.html")

    snapshot = await snapshot_for_ai(page, timeout=3000)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - generic [ref=e2]:
        - iframe [ref=e3]:
          - button "Button one" [ref=f1e2]
        - iframe [ref=e4]:
          - button "Button two" [ref=f2e2]
      - iframe [ref=e5]:
        - button "Button three" [ref=f3e2]
  """,
    )
    await expect(page.get_by_ref("f2e2")).to_have_text("Button two")


async def test_AR_083_should_snapshot_a_locator_inside_a_frameset_frame(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/frameset.html")

    snapshot = await page.frames[1].locator("body").aria_snapshot(mode="ai")
    assert_contains_yaml(
        snapshot,
        """
    - generic [ref=f1e1]: Hi, I'm frame
  """,
    )

    await expect(page.get_by_ref("f1e1")).to_have_text("Hi, I'm frame")
    resolved = await page.get_by_ref("f1e1").normalize()
    assert str(resolved) == 'locator("frame").first.content_frame.locator("body")'


async def test_AR_084_should_stitch_iframes_inside_a_frameset_frame(
    page: Page, server: Server
) -> None:
    serve_html(
        server,
        "/frameset-with-iframe.html",
        '<frameset><frame src="/frame-with-iframe.html"></frameset>',
    )
    serve_html(
        server,
        "/frame-with-iframe.html",
        '<button>In frame</button><iframe srcdoc="<button>In iframe</button>"></iframe>',
    )
    await page.goto(server.PREFIX + "/frameset-with-iframe.html")

    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - iframe [ref=e2]:
      - generic [ref=f1e1]:
        - button "In frame" [ref=f1e2]
        - iframe [ref=f1e3]:
          - button "In iframe" [ref=f2e2]
  """,
    )
    await expect(page.get_by_ref("f1e2")).to_have_text("In frame")
    await expect(page.get_by_ref("f2e2")).to_have_text("In iframe")

    resolved = await page.get_by_ref("f2e2").normalize()
    assert (
        str(resolved)
        == 'locator("frame").content_frame.locator("iframe").content_frame.get_by_role("button", name="In iframe")'
    )


async def test_AR_085_should_stitch_nested_frameset_documents(
    page: Page, server: Server
) -> None:
    serve_html(
        server,
        "/outer-frameset.html",
        '<frameset><frame src="/inner-frameset.html"></frameset>',
    )
    serve_html(
        server,
        "/inner-frameset.html",
        '<frameset><frameset><frame src="/leaf.html"></frameset></frameset>',
    )
    serve_html(server, "/leaf.html", "<button>Leaf button</button>")
    await page.goto(server.PREFIX + "/outer-frameset.html")

    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - iframe [ref=e2]:
      - iframe [ref=f1e3]:
        - button "Leaf button" [ref=f2e2]
  """,
    )
    await expect(page.get_by_ref("f2e2")).to_have_text("Leaf button")


async def test_AR_086_should_collapse_inline_generic_nodes(page: Page) -> None:
    await page.set_content(
        """
    <ul>
      <li><b>3</b> <abbr>bds</abbr></li>
      <li><b>2</b> <abbr>ba</abbr></li>
      <li><b>1,200</b> <abbr>sqft</abbr></li>
    </ul>
    <ul>
      <li><div>3</div></li>
      <li><div>2</div></li>
      <li><div>1,200</div></li>
    </ul>"""
    )

    snapshot1 = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot1,
        """
    - generic [active] [ref=e1]:
      - list [ref=e2]:
        - listitem [ref=e3]: 3 bds
        - listitem [ref=e4]: 2 ba
        - listitem [ref=e5]: 1,200 sqft
      - list [ref=e6]:
        - listitem [ref=e7]:
          - generic [ref=e8]: "3"
        - listitem [ref=e9]:
          - generic [ref=e10]: "2"
        - listitem [ref=e11]:
          - generic [ref=e12]: 1,200
  """,
    )


async def test_AR_087_should_inline_single_leaf_generic_child_into_parent_generic(
    page: Page,
) -> None:
    # The nameless images are distilled away, so each wrapper is left with a single leaf generic
    # child, whose text is inlined into the wrapper - recursively for the second one.
    await page.set_content(
        """
    <div><img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA="><div>Status: Open.</div></div>
    <div><img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA="><div><img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA="><div>Nested twice.</div></div></div>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - generic [ref=e2]: "Status: Open."
      - generic [ref=e5]: Nested twice.
  """,
    )


async def test_AR_088_should_inline_a_deeply_nested_generic(page: Page) -> None:
    # Every wrapper contains a nameless image (distilled away) plus a single generic child, so the
    # text bubbles up the whole chain - all the way into the body.
    img = '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=">'
    await page.set_content(
        f"""
    <div>{img}<div>{img}<div>{img}<div>{img}<div>Deeply nested.</div></div></div></div></div>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]: Deeply nested.
  """,
    )
    assert "img" not in snapshot


async def test_AR_089_should_not_remove_generic_nodes_with_title(page: Page) -> None:
    await page.set_content('<div title="Element title">Element content</div>')

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic "Element title" [ref=e2]
  """,
    )


async def test_AR_090_should_limit_depth(page: Page) -> None:
    await page.set_content(
        """
    <ul>
      <li>item1</li>
      <a href="about:blank" style="cursor:pointer">link</a>
      <li>
        <ul id=target>
          <li>item2</li>
          <li>
            <ul>
              <li>item3</li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>
  """
    )

    snapshot1 = await snapshot_for_ai(page, depth=1)
    assert_contains_yaml(
        snapshot1,
        """
    - list [ref=e2]:
      - listitem [ref=e3]: item1
      - link "link" [ref=e4] [cursor=pointer]:
        - /url: about:blank
      - listitem [ref=e5]
  """,
    )

    snapshot2 = await snapshot_for_ai(page, depth=3)
    assert_contains_yaml(
        snapshot2,
        """
    - list [ref=e2]:
      - listitem [ref=e3]: item1
      - link "link" [ref=e4] [cursor=pointer]:
        - /url: about:blank
      - listitem [ref=e5]:
        - list [ref=e6]:
          - listitem [ref=e7]: item2
          - listitem [ref=e8]
  """,
    )

    snapshot3 = await snapshot_for_ai(page, depth=100)
    assert_contains_yaml(
        snapshot3,
        """
    - list [ref=e2]:
      - listitem [ref=e3]: item1
      - link "link" [ref=e4] [cursor=pointer]:
        - /url: about:blank
      - listitem [ref=e5]:
        - list [ref=e6]:
          - listitem [ref=e7]: item2
          - listitem [ref=e8]:
            - list [ref=e9]:
              - listitem [ref=e10]: item3
  """,
    )

    snapshot4 = await page.locator("#target").aria_snapshot(mode="ai", depth=1)
    assert_contains_yaml(
        snapshot4,
        """
    - list [ref=e6]:
      - listitem [ref=e7]: item2
      - listitem [ref=e8]
  """,
    )


async def test_AR_091_should_annotate_aria_hidden_elements(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/42223
    await page.set_content(
        """
    <h2>Visible heading</h2>
    <div aria-hidden="true">
      <h1>Hidden heading</h1>
      <p>Hidden content</p>
    </div>
    <h2>After hidden</h2>
  """
    )

    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - generic [active] [ref=e1]:
      - heading "Visible heading" [level=2] [ref=e2]
      - generic [aria-hidden] [ref=e3]:
        - heading [level=1] [ref=e4]: Hidden heading
        - paragraph [ref=e5]: Hidden content
      - heading "After hidden" [level=2] [ref=e6]
  """,
    )

    # Default snapshot excludes aria-hidden elements entirely.
    default_snapshot = await page.locator("body").aria_snapshot()
    assert "Hidden content" not in default_snapshot


async def test_AR_092_should_only_annotate_the_top_element_in_a_hidden_subtree(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42223
    await page.set_content(
        """
    <div aria-hidden="true">
      <h1>Heading</h1>
      <p>Paragraph</p>
    </div>
  """
    )

    # Only the element with aria-hidden="true" gets the annotation, not its descendants.
    assert_contains_yaml(
        await snapshot_for_ai(page),
        """
    - generic [aria-hidden] [ref=e2]:
      - heading [level=1] [ref=e3]: Heading
      - paragraph [ref=e4]: Paragraph
  """,
    )


async def test_AR_093_should_not_include_hidden_iframes(page: Page) -> None:
    await page.set_content(
        """
    <iframe name="visible" srcdoc="<button>Visible</button>"></iframe>
    <iframe name="hidden" style="visibility: hidden" srcdoc="<button>Hidden</button>"></iframe>
    <iframe name="none" style="display: none" srcdoc="<button>None</button>"></iframe>
  """
    )
    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - iframe [ref=e2]:
      - button "Visible" [ref=f1e2]
  """,
    )
    assert "Hidden" not in snapshot
    assert "None" not in snapshot


async def test_AR_094_should_not_generate_refs_for_inert_elements(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/36938
    await page.set_content(
        """
    <button>with-ref</button>
    <button inert>no-ref</button>
    <div inert>
      <button>no-ref</button>
    </div>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic [active] [ref=e1]:
      - button "with-ref" [ref=e2]
      - button: no-ref
      - generic:
        - button: no-ref
  """,
    )


async def test_AR_095_should_not_generate_refs_for_elements_outside_of_a_modal_dialog(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36938
    await page.set_content(
        """
    <button>Outside</button>
    <dialog id=dialog>
      <button>Inside</button>
    </dialog>
    <script>
      document.getElementById('dialog').showModal();
    </script>
  """
    )

    snapshot = await snapshot_for_ai(page)
    assert_contains_yaml(
        snapshot,
        """
    - generic:
      - button: Outside
      - dialog [ref=e1]:
        - button "Inside" [active] [ref=e2]
  """,
    )
