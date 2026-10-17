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

"""Port of tests/page/page-aria-snapshot.spec.ts."""

import re
from typing import Callable

import pytest

from playwright.sync_api import Locator, Page, expect
from tests.helpers.aria_snapshot import assert_contains_yaml, unshift
from tests.server import Server, TestServerRequest


def check_and_match_snapshot(locator: Locator, snapshot: str) -> None:
    assert locator.aria_snapshot() == unshift(snapshot)
    expect(locator).to_match_aria_snapshot(snapshot)


def serve_html(server: Server, path: str, body: str) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(body.encode())
        request.finish()

    server.set_route(path, handler)


def test_AR_001_should_snapshot(page: Page) -> None:
    page.set_content("<h1>title</h1>")
    check_and_match_snapshot(
        page.locator("body"),
        """
    - heading "title" [level=1]
  """,
    )


def test_AR_002_should_snapshot_list(page: Page) -> None:
    page.set_content(
        """
    <h1>title</h1>
    <h1>title 2</h1>
  """
    )
    check_and_match_snapshot(
        page.locator("body"),
        """
    - heading "title" [level=1]
    - heading "title 2" [level=1]
  """,
    )


def test_AR_003_should_snapshot_list_with_accessible_name(page: Page) -> None:
    page.set_content(
        """
    <ul aria-label="my list">
      <li>one</li>
      <li>two</li>
    </ul>
  """
    )
    check_and_match_snapshot(
        page.locator("body"),
        """
    - list "my list":
      - listitem: one
      - listitem: two
  """,
    )


def test_AR_004_should_quote_names_that_look_like_regexes(page: Page) -> None:
    page.set_content(
        """
    <nav>
      <a href="/">/</a>
      <a href="/docs/">/docs/</a>
      <a href="/a(b/">/a(b/</a>
    </nav>
  """
    )
    check_and_match_snapshot(
        page.locator("nav"),
        """
    - navigation:
      - link "/":
        - /url: /
      - link "/docs/":
        - /url: /docs/
      - link "/a(b/":
        - /url: /a(b/
  """,
    )


def test_AR_005_should_snapshot_complex(page: Page) -> None:
    page.set_content(
        """
    <ul>
      <li>
        <a href='about:blank'>link</a>
      </li>
    </ul>
  """
    )
    check_and_match_snapshot(
        page.locator("body"),
        """
    - list:
      - listitem:
        - link "link":
          - /url: about:blank
  """,
    )


def test_AR_006_should_allow_text_nodes(page: Page) -> None:
    page.set_content(
        """
    <h1>Microsoft</h1>
    <div>Open source projects and samples from Microsoft</div>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - heading "Microsoft" [level=1]
    - text: Open source projects and samples from Microsoft
  """,
    )


def test_AR_007_should_snapshot_details_visibility(page: Page) -> None:
    page.set_content(
        """
    <details>
      <summary>Summary</summary>
      <div>Details</div>
    </details>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - group: Summary
  """,
    )


def test_AR_008_should_not_snapshot_text_directly_inside_closed_details(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/43019
    page.set_content(
        """
    <details>
      <summary>Summary</summary>
      Details
    </details>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - group: Summary
  """,
    )

    page.eval_on_selector("details", "details => details.open = true")
    check_and_match_snapshot(
        page.locator("body"),
        """
    - group: Summary Details
  """,
    )


def test_AR_009_should_not_snapshot_text_that_is_not_assigned_to_a_slot(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/43019
    page.set_content(
        """
    <div role=button>Light</div>
    <script>
      document.querySelector('div').attachShadow({ mode: 'open' }).innerHTML = '<p>Shadow</p>';
    </script>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - button "Shadow":
      - paragraph: Shadow
  """,
    )
    expect(page.get_by_role("button", name="Shadow", exact=True)).to_be_visible()


def test_AR_010_should_snapshot_integration(page: Page) -> None:
    page.set_content(
        """
    <h1>Microsoft</h1>
    <div>Open source projects and samples from Microsoft</div>
    <ul>
      <li>
        <details>
          <summary>
            Verified
          </summary>
          <div>
            <div>
              <p>
                We've verified that the organization <strong>microsoft</strong> controls the domain:
              </p>
              <ul>
                <li class="mb-1">
                  <strong>opensource.microsoft.com</strong>
                </li>
              </ul>
              <div>
                <a href="about: blank">Learn more about verified organizations</a>
              </div>
            </div>
          </div>
        </details>
      </li>
      <li>
        <a href="about:blank">
          <summary title="Label: GitHub Sponsor">Sponsor</summary>
        </a>
      </li>
    </ul>"""
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - heading "Microsoft" [level=1]
    - text: Open source projects and samples from Microsoft
    - list:
      - listitem:
        - group: Verified
      - listitem:
        - link "Sponsor":
          - /url: about:blank
  """,
    )


def test_AR_011_should_support_multiline_text(page: Page) -> None:
    page.set_content(
        """
    <p>
      Line 1
      Line 2
      Line 3
    </p>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - paragraph: Line 1 Line 2 Line 3
  """,
    )
    expect(page.locator("body")).to_match_aria_snapshot(
        """
    - paragraph: |
          Line 1
          Line 2
          Line 3
  """
    )


def test_AR_012_should_concatenate_span_text(page: Page) -> None:
    page.set_content(
        """
    <span>One</span> <span>Two</span> <span>Three</span>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - text: One Two Three
  """,
    )


def test_AR_013_should_concatenate_span_text_2(page: Page) -> None:
    page.set_content(
        """
    <span>One </span><span>Two </span><span>Three</span>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - text: One Two Three
  """,
    )


def test_AR_014_should_concatenate_div_text_with_spaces(page: Page) -> None:
    page.set_content(
        """
    <div>One</div><div>Two</div><div>Three</div>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - text: One Two Three
  """,
    )


def test_AR_015_should_include_pseudo_in_text(page: Page) -> None:
    page.set_content(
        """
    <style>
      span:before {
        content: 'world';
      }
      div:after {
        content: 'bye';
      }
    </style>
    <a href="about:blank">
      <span>hello</span>
      <div>hello</div>
    </a>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "worldhello hellobye":
      - /url: about:blank
  """,
    )


def test_AR_016_should_not_include_hidden_pseudo_in_text(page: Page) -> None:
    page.set_content(
        """
    <style>
      span:before {
        content: 'world';
        display: none;
      }
      div:after {
        content: 'bye';
        visibility: hidden;
      }
    </style>
    <a href="about:blank">
      <span>hello</span>
      <div>hello</div>
    </a>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "hello hello":
      - /url: about:blank
  """,
    )


def test_AR_017_should_include_new_line_for_block_pseudo(page: Page) -> None:
    page.set_content(
        """
    <style>
      span:before {
        content: 'world';
        display: block;
      }
      div:after {
        content: 'bye';
        display: block;
      }
    </style>
    <a href="about:blank">
      <span>hello</span>
      <div>hello</div>
    </a>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "world hello hello bye":
      - /url: about:blank
  """,
    )


def test_AR_018_should_work_with_slots(page: Page) -> None:
    # Text "foo" is assigned to the slot, should not be used twice.
    page.set_content(
        """
    <button><div>foo</div></button>
    <script>
      (() => {
        const container = document.querySelector('div');
        const shadow = container.attachShadow({ mode: 'open' });
        const slot = document.createElement('slot');
        shadow.appendChild(slot);
      })();
    </script>
  """
    )
    check_and_match_snapshot(
        page.locator("body"),
        """
    - button "foo"
  """,
    )

    # Text "foo" is assigned to the slot, should be used instead of slot content.
    page.set_content(
        """
    <div>foo</div>
    <script>
      (() => {
        const container = document.querySelector('div');
        const shadow = container.attachShadow({ mode: 'open' });
        const button = document.createElement('button');
        shadow.appendChild(button);
        const slot = document.createElement('slot');
        button.appendChild(slot);
        const span = document.createElement('span');
        span.textContent = 'pre';
        slot.appendChild(span);
      })();
    </script>
  """
    )
    check_and_match_snapshot(
        page.locator("body"),
        """
    - button "foo"
  """,
    )

    # Nothing is assigned to the slot, should use slot content.
    page.set_content(
        """
    <div></div>
    <script>
      (() => {
        const container = document.querySelector('div');
        const shadow = container.attachShadow({ mode: 'open' });
        const button = document.createElement('button');
        shadow.appendChild(button);
        const slot = document.createElement('slot');
        button.appendChild(slot);
        const span = document.createElement('span');
        span.textContent = 'pre';
        slot.appendChild(span);
      })();
    </script>
  """
    )
    check_and_match_snapshot(
        page.locator("body"),
        """
    - button "pre"
  """,
    )


def test_AR_019_should_snapshot_inner_text(page: Page) -> None:
    page.set_content(
        """
    <div role="listitem">
      <div>
        <div>
          <span title="a.test.ts">a.test.ts</span>
        </div>
        <div>
          <button title="Run"></button>
          <button title="Show source"></button>
          <button title="Watch"></button>
        </div>
      </div>
    </div>
    <div role="listitem">
      <div>
        <div>
          <span title="snapshot">snapshot</span>
        </div>
        <div class="ui-mode-list-item-time">30ms</div>
        <div>
          <button title="Run"></button>
          <button title="Show source"></button>
          <button title="Watch"></button>
        </div>
      </div>
    </div>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - listitem:
      - text: a.test.ts
      - button "Run"
      - button "Show source"
      - button "Watch"
    - listitem:
      - text: snapshot 30ms
      - button "Run"
      - button "Show source"
      - button "Watch"
  """,
    )


def test_AR_020_should_include_pseudo_codepoints(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <link href="codicon.css" rel="stylesheet" />
    <p class='codicon codicon-check'>hello</p>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - paragraph: hello
  """,
    )


def test_AR_021_check_aria_hidden_text(page: Page) -> None:
    page.set_content(
        """
    <p>
      <span>hello</span>
      <span aria-hidden="true">world</span>
    </p>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - paragraph: hello
  """,
    )


def test_AR_022_should_ignore_presentation_and_none_roles(page: Page) -> None:
    page.set_content(
        """
    <ul>
      <li role='presentation'>hello</li>
      <li role='none'>world</li>
    </ul>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - list: hello world
  """,
    )


def test_AR_023_should_treat_input_value_as_text_in_templates_but_not_for_checkbox_radio_file(
    page: Page,
) -> None:
    page.set_content(
        """
    <input value='hello world'>
    <input type=file>
    <input type=checkbox checked>
    <input type=radio checked>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - textbox: hello world
    - button "Choose File"
    - checkbox [checked]
    - radio [checked]
  """,
    )


def test_AR_024_should_not_use_on_as_checkbox_value(page: Page) -> None:
    page.set_content(
        """
    <input type='checkbox'>
    <input type='radio'>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - checkbox
    - radio
  """,
    )


def test_AR_025_should_respect_aria_owns(page: Page) -> None:
    page.set_content(
        """
    <a href='about:blank' aria-owns='input p'>
      <div role='region'>Link 1</div>
    </a>
    <a href='about:blank' aria-owns='input p'>
      <div role='region'>Link 2</div>
    </a>
    <input id='input' value='Value'>
    <p id='p'>Paragraph</p>
  """
    )

    # - Different from Chrome DevTools which attributes ownership to the last element.
    # - CDT also does not include non-owned children in accessible name.
    # - Disregarding these as aria-owns can't suggest multiple parts by spec.
    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "Link 1 Value Paragraph":
      - /url: about:blank
      - region: Link 1
      - textbox: Value
      - paragraph: Paragraph
    - link "Link 2 Value Paragraph":
      - /url: about:blank
      - region: Link 2
  """,
    )


def test_AR_026_should_be_ok_with_circular_ownership(page: Page) -> None:
    page.set_content(
        """
    <a href='about:blank' id='parent'>
      <div role='region' aria-owns='parent'>Hello</div>
    </a>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "Hello":
      - /url: about:blank
      - region: Hello
  """,
    )


def test_AR_027_should_escape_yaml_text_in_text_nodes(page: Page) -> None:
    page.set_content(
        """
    <details>
      <summary>one: <a href="#">link1</a> "two <a href="#">link2</a> 'three <a href="#">link3</a> `four</summary>
    </details>
    <ul>
      <a href="#">one</a>,<a href="#">two</a>
      (<a href="#">three</a>)
      {<a href="#">four</a>}
      [<a href="#">five</a>]
    </ul>
    <div>[Select all]</div>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        r"""
    - group:
      - text: "one:"
      - link "link1":
        - /url: "#"
      - text: "\"two"
      - link "link2":
        - /url: "#"
      - text: "'three"
      - link "link3":
        - /url: "#"
      - text: "`four"
    - list:
      - link "one":
        - /url: "#"
      - text: ","
      - link "two":
        - /url: "#"
      - text: (
      - link "three":
        - /url: "#"
      - text: ") {"
      - link "four":
        - /url: "#"
      - text: "} ["
      - link "five":
        - /url: "#"
      - text: "]"
    - text: "[Select all]"
  """,
    )


def test_AR_028_should_normalize_whitespace(page: Page) -> None:
    page.set_content(
        """
    <details>
      <summary> one  \n two <a href="#"> link &nbsp;\n  1 </a> </summary>
    </details>
    <input value='  hello   &nbsp; world '>
    <button>hello­​world</button>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - group:
      - text: one two
      - link "link 1":
        - /url: "#"
    - textbox: hello world
    - button "helloworld"
  """,
    )

    # Weird whitespace in the template should be normalized.
    expect(page.locator("body")).to_match_aria_snapshot(
        """
    - group:
      - text: |
          one
          two
      - link "  link     1 ":
        - /url: "#"
    - textbox:        hello  world
    - button "he­lloworld​"
  """
    )


def test_AR_029_should_handle_long_strings(page: Page) -> None:
    s = "a" * 10000
    page.set_content(
        f"""
    <a href='about:blank'>
      <div role='region'>{s}</div>
    </a>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        f"""
    - link:
      - /url: about:blank
      - region: {s}
  """,
    )


def test_AR_030_should_escape_special_yaml_characters(page: Page) -> None:
    page.set_content(
        """
    <a href="#">@hello</a>@hello
    <a href="#">]hello</a>]hello
    <a href="#">hello\n</a>
    hello\n<a href="#">\n hello</a>\n hello
    <a href="#">#hello</a>#hello
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "@hello":
      - /url: "#"
    - text: "@hello"
    - link "]hello":
      - /url: "#"
    - text: "]hello"
    - link "hello":
      - /url: "#"
    - text: hello
    - link "hello":
      - /url: "#"
    - text: hello
    - link "#hello":
      - /url: "#"
    - text: "#hello"
  """,
    )


@pytest.mark.xfail(
    reason="driver: the bundled driver predates upstream #43469 (quote ~, .inf and .nan)",
    strict=True,
)
def test_AR_031_should_escape_special_yaml_values(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/43451
    page.set_content(
        """
    <a href="#">true</a>False
    <a href="#">NO</a>yes
    <a href="#">y</a>N
    <a href="#">on</a>Off
    <a href="#">null</a>NULL
    <a href="#">123</a>123
    <a href="#">-1.2</a>-1.2
    <a href="#">-</a>-
    <a href="#">~</a>~
    <a href="#">.inf</a>.NaN
    <input type=text value="555">
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "true":
      - /url: "#"
    - text: "False"
    - link "NO":
      - /url: "#"
    - text: "yes"
    - link "y":
      - /url: "#"
    - text: "N"
    - link "on":
      - /url: "#"
    - text: "Off"
    - link "null":
      - /url: "#"
    - text: "NULL"
    - link "123":
      - /url: "#"
    - text: "123"
    - link "-1.2":
      - /url: "#"
    - text: "-1.2"
    - link "-":
      - /url: "#"
    - text: "-"
    - link "~":
      - /url: "#"
    - text: "~"
    - link ".inf":
      - /url: "#"
    - text: ".NaN"
    - textbox: "555"
  """,
    )


def test_AR_032_should_not_report_textarea_text_content(page: Page) -> None:
    page.set_content("<textarea>Before</textarea>")
    check_and_match_snapshot(
        page.locator("body"),
        """
    - textbox: Before
  """,
    )
    page.evaluate("() => { document.querySelector('textarea').value = 'After'; }")
    check_and_match_snapshot(
        page.locator("body"),
        """
    - textbox: After
  """,
    )


def test_AR_033_should_not_show_visible_children_of_hidden_elements(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36296
    page.set_content(
        """
    <div style="visibility: hidden;">
      <div style="visibility: visible;">
        <button>Button</button>
      </div>
    </div>
  """
    )

    assert page.locator("body").aria_snapshot() == ""


def test_AR_034_should_not_show_unhidden_children_of_aria_hidden_elements(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36296
    page.set_content(
        """
    <div aria-hidden="true">
      <div aria-hidden="false">
        <button>Button</button>
      </div>
    </div>
  """
    )

    assert page.locator("body").aria_snapshot() == ""


def test_AR_035_should_snapshot_placeholder_when_different_from_the_name(
    page: Page,
) -> None:
    page.set_content(
        """
    <input placeholder="Placeholder">
  """
    )
    assert_contains_yaml(
        page.locator("body").aria_snapshot(),
        """
    - textbox "Placeholder"
  """,
    )

    page.set_content(
        """
    <input placeholder="Placeholder" aria-label="Label">
  """
    )
    assert_contains_yaml(
        page.locator("body").aria_snapshot(),
        """
    - textbox "Label":
      - /placeholder: Placeholder
  """,
    )


def test_AR_036_match_values_both_against_regex_and_string(page: Page) -> None:
    page.set_content('<a href="/auth?r=/">Log in</a>')
    check_and_match_snapshot(
        page.locator("body"),
        """
    - link "Log in":
      - /url: /auth?r=/
  """,
    )


def test_AR_037_auto_waits_the_locator_and_does_not_include_iframes(
    page: Page, sync_gather: Callable
) -> None:
    page.set_content(
        """
    <div>Hello</div>
  """
    )

    def set_target() -> None:
        page.wait_for_timeout(2000)
        page.set_content(
            """
    <div id=target>
      Hello
      <iframe srcdoc="<ul><li>Item 1</li><li>Item 2</li></ul>"></iframe>
    </div>
  """
        )

    snapshot, _ = sync_gather(
        lambda: page.locator("#target").aria_snapshot(), set_target
    )
    assert_contains_yaml(
        snapshot,
        """
    - text: Hello
  """,
    )


def test_AR_038_should_limit_depth(page: Page) -> None:
    page.set_content(
        """
    <ul id=target>
      <li>item2</li>
      <li>
        <ul>
          <li>item3</li>
        </ul>
      </li>
    </ul>
  """
    )

    snapshot = page.locator("#target").aria_snapshot(depth=1)
    assert_contains_yaml(
        snapshot,
        """
    - list:
      - listitem: item2
      - listitem
  """,
    )


def test_AR_039_should_snapshot_a_locator_inside_an_iframe(page: Page) -> None:
    page.set_content(
        """
    <h1>Main Page</h1>
    <iframe srcdoc="<ul><li>Item 1</li><li>Item 2</li></ul>"></iframe>
  """
    )

    list_ = page.frames[1].locator("ul")
    snapshot = list_.aria_snapshot()
    assert_contains_yaml(
        snapshot,
        """
    - list:
      - listitem: Item 1
      - listitem: Item 2
  """,
    )


def test_AR_040_should_include_frames_on_frameset_pages(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/41784
    serve_html(
        server,
        "/frameset.html",
        '<frameset cols="50%,50%"><frame src="/frames/frame.html"><frame src="/frames/frame.html"></frameset>',
    )
    page.goto(server.PREFIX + "/frameset.html")
    # Like iframes, frames are listed in the snapshot, but their content is not included.
    assert page.aria_snapshot(timeout=3000) == unshift(
        """
    - iframe
    - iframe
  """
    )


def test_AR_041_should_snapshot_a_locator_inside_a_frameset_frame(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/frameset.html")
    check_and_match_snapshot(
        page.frame_locator("frame").first.locator("body"),
        """
    - text: Hi, I'm frame
  """,
    )


def test_AR_042_should_snapshot_with_box_from_page(page: Page) -> None:
    page.set_content(
        """
    <button style="position:absolute;left:100px;top:50px;width:80px;height:40px;margin:0;padding:0;border:0;">click</button>
  """
    )

    snapshot = page.aria_snapshot(boxes=True)
    assert snapshot == '- button "click" [box=100,50,80,40]'


def test_AR_043_should_snapshot_with_box_from_locator(page: Page) -> None:
    page.set_content(
        """
    <div style="position:absolute;left:10px;top:20px;width:200px;height:100px;">
      <button style="position:absolute;left:5px;top:5px;width:60px;height:30px;margin:0;padding:0;border:0;">ok</button>
    </div>
  """
    )

    snapshot = page.locator("div").aria_snapshot(boxes=True)
    assert snapshot == '- button "ok" [box=15,25,60,30]'


def test_AR_044_should_not_include_box_when_option_is_omitted(
    page: Page,
) -> None:
    page.set_content("<button>click</button>")
    snapshot = page.aria_snapshot()
    assert not re.search(r"\[box=", snapshot)


def test_AR_045_should_not_include_hidden_iframes(page: Page) -> None:
    page.set_content(
        """
    <iframe name="visible" srcdoc="<button>Visible</button>"></iframe>
    <iframe name="hidden" style="visibility: hidden" srcdoc="<button>Hidden</button>"></iframe>
    <iframe name="none" style="display: none" srcdoc="<button>None</button>"></iframe>
  """
    )
    assert page.aria_snapshot() == unshift(
        """
    - iframe
  """
    )


def test_AR_046_should_not_include_inert_elements(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/36938
    page.set_content(
        """
    <button>Hi</button>
    <button inert>Hello</button>
    <div inert>
      <button>Yay</button>
      <p>Some text</p>
    </div>
    <p>Visible <span inert>inert</span> text</p>
    <button><span inert>Save</span></button>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - button "Hi"
    - paragraph: Visible text
    - button
  """,
    )


def test_AR_047_should_only_include_the_modal_dialog_content(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/36938
    page.set_content(
        """
    <h1>Title</h1>
    <button>Outside</button>
    <dialog id=dialog>
      <h2>Dialog</h2>
      <button>Inside</button>
      <div inert><button>Inert inside</button></div>
    </dialog>
    <script>
      document.getElementById('dialog').showModal();
    </script>
  """
    )

    check_and_match_snapshot(
        page.locator("body"),
        """
    - dialog:
      - heading "Dialog" [level=2]
      - button "Inside"
  """,
    )

    page.locator("#dialog").evaluate("e => e.close()")
    check_and_match_snapshot(
        page.locator("body"),
        """
    - heading "Title" [level=1]
    - button "Outside"
  """,
    )
