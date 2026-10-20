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

"""Port of tests/page/to-match-aria-snapshot.spec.ts."""

import pytest

from playwright.async_api import Page, expect


def yaml_error_message(expected: str, error: str) -> str:
    """The message of expect(page).to_match_aria_snapshot() for a template that does not parse."""
    return (
        f"Page expected to match Aria snapshot '{expected}'\n"
        "Actual value: None\n"
        f"Error: {error} \n"
        "Call log:\n"
        '  - Expect "to_match_aria_snapshot" with timeout 5000ms\n'
    )


async def test_AR_107_should_match_page(page: Page) -> None:
    await page.set_content("<h1>title</h1>")
    await expect(page).to_match_aria_snapshot(
        """
    - heading "title"
  """
    )


async def test_AR_108_should_match_page_complex(page: Page) -> None:
    await page.set_content(
        """
    <h1>Microsoft</h1>
    <div>Open source projects and samples from Microsoft</div>
    <ul>
      <li>
        <a href="about:blank">Playwright</a>
      </li>
    </ul>"""
    )

    await expect(page).to_match_aria_snapshot(
        """
    - heading "Microsoft"
    - text: Open source projects and samples from Microsoft
    - list:
      - listitem:
        - link "Playwright"
  """
    )


async def test_AR_109_should_match_page_with_not(page: Page) -> None:
    await page.set_content("<h1>title</h1>")
    await expect(page).not_to_match_aria_snapshot(
        """
    - heading "wrong"
  """
    )


async def test_AR_110_should_fail_page_with_timeout(page: Page) -> None:
    await page.set_content("<h1>title</h1>")
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - heading "wrong"
  """,
            timeout=2000,
        )
    message = str(exc_info.value)
    assert "Page expected to match Aria snapshot" in message
    assert 'Expect "to_match_aria_snapshot" with timeout 2000ms' in message
    assert "Locator" not in message


async def test_AR_111_should_match(page: Page) -> None:
    await page.set_content("<h1>title</h1>")
    await expect(page).to_match_aria_snapshot(
        """
    - heading "title"
  """
    )


async def test_AR_112_should_match_in_list(page: Page) -> None:
    await page.set_content(
        """
    <h1>title</h1>
    <h1>title 2</h1>
  """
    )
    await expect(page).to_match_aria_snapshot(
        """
    - heading "title"
  """
    )


async def test_AR_113_should_match_list_with_accessible_name(page: Page) -> None:
    await page.set_content(
        """
    <ul aria-label="my list">
      <li>one</li>
      <li>two</li>
    </ul>
  """
    )
    await expect(page).to_match_aria_snapshot(
        """
    - list "my list":
      - listitem: "one"
      - listitem: "two"
  """
    )


async def test_AR_114_should_match_deep_item(page: Page) -> None:
    await page.set_content(
        """
    <div>
      <h1>title</h1>
      <h1>title 2</h1>
    </div>
  """
    )
    await expect(page).to_match_aria_snapshot(
        """
    - heading "title"
  """
    )


async def test_AR_115_should_match_complex(page: Page) -> None:
    await page.set_content(
        """
    <ul>
      <li>
        <a href='about:blank'>link</a>
      </li>
    </ul>
  """
    )
    await expect(page).to_match_aria_snapshot(
        """
    - list:
      - listitem:
        - link "link"
  """
    )


async def test_AR_116_should_match_regex(page: Page) -> None:
    await page.set_content("<h1>Issues 12</h1>")
    await expect(page).to_match_aria_snapshot(
        r"""
      - heading /Issues \d+/
    """
    )

    await page.set_content("<h1>Issues 1/2</h1>")
    await expect(page).to_match_aria_snapshot(
        r"""
      - heading /Issues 1[/]2/
    """
    )

    await page.set_content("<h1>Issues 1[</h1>")
    await expect(page).to_match_aria_snapshot(
        r"""
      - heading /Issues 1\[/
    """
    )

    await page.set_content("<h1>Issues 1]]2</h1>")
    await expect(page).to_match_aria_snapshot(
        r"""
      - heading /Issues 1[\]]]2/
    """
    )


async def test_AR_117_should_allow_text_nodes(page: Page) -> None:
    await page.set_content(
        """
    <h1>Microsoft</h1>
    <div>Open source projects and samples from Microsoft</div>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - heading "Microsoft"
    - text: "Open source projects and samples from Microsoft"
  """
    )


async def test_AR_118_details_visibility(page: Page) -> None:
    await page.set_content(
        """
    <details>
      <summary>Summary</summary>
      <div>Details</div>
    </details>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - group: "Summary"
  """
    )


async def test_AR_119_checked_attribute(page: Page) -> None:
    await page.set_content(
        """
    <input type='checkbox' checked />
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - checkbox
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - checkbox [checked]
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - checkbox [checked=true]
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - checkbox [checked=false]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - checkbox [checked=mixed]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - checkbox [checked=5]
    """,
            timeout=1000,
        )
    assert ' attribute must be a boolean or "mixed"' in str(exc_info.value)


async def test_AR_120_disabled_attribute(page: Page) -> None:
    await page.set_content(
        """
    <button disabled>Click me</button>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [disabled]
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [disabled=true]
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [disabled=false]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [disabled=invalid]
    """,
            timeout=1000,
        )
    assert " attribute must be a boolean" in str(exc_info.value)


async def test_AR_121_expanded_attribute(page: Page) -> None:
    await page.set_content(
        """
    <button aria-expanded="true">Toggle</button>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [expanded]
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [expanded=true]
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [expanded=false]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [expanded=invalid]
    """,
            timeout=1000,
        )
    assert " attribute must be a boolean" in str(exc_info.value)


async def test_AR_122_level_attribute(page: Page) -> None:
    await page.set_content(
        """
    <h2>Section Title</h2>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - heading
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - heading [level=2]
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - heading [level=3]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - heading [level=two]
    """,
            timeout=1000,
        )
    assert " attribute must be a number" in str(exc_info.value)


async def test_AR_123_pressed_attribute(page: Page) -> None:
    await page.set_content(
        """
    <button aria-pressed="true">Like</button>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [pressed]
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [pressed=true]
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [pressed=false]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    # Test for 'mixed' state
    await page.set_content(
        """
    <button aria-pressed="mixed">Like</button>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - button [pressed=mixed]
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [pressed=true]
    """,
            timeout=1000,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in str(exc_info.value)

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - button [pressed=5]
    """,
            timeout=1000,
        )
    assert ' attribute must be a boolean or "mixed"' in str(exc_info.value)


async def test_AR_124_selected_attribute(page: Page) -> None:
    await page.set_content(
        """
    <table>
      <tr aria-selected="true">
        <td>Row</td>
      </tr>
      <tr>
        <td>Row 2</td>
      </tr>
    </table>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - row
    - row
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - row [selected]
    - row
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - row [selected=true]
    - row [selected=false]
  """
    )

    await expect(page.locator("table")).to_match_aria_snapshot(
        """
    - table:
      - rowgroup:
        - row [selected=true]
        - row [selected=false]
  """
    )

    expected = """
      - row [selected=false]
      - row [selected=false]
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected, timeout=1000)
    message = str(exc_info.value)
    assert message.startswith(f"Page expected to match Aria snapshot '{expected}'\n")
    assert 'Expect "to_match_aria_snapshot" with timeout 1000ms' in message
    assert (
        """- table:
  - rowgroup:
    - row "Row" [selected]:
      - cell "Row"
    - row "Row 2":
      - cell "Row 2\""""
        in message
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
      - row [selected=invalid]
    """,
            timeout=1000,
        )
    assert " attribute must be a boolean" in str(exc_info.value)


async def test_AR_125_integration_test(page: Page) -> None:
    await page.set_content(
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

    await expect(page).to_match_aria_snapshot(
        """
    - heading "Microsoft"
    - text: Open source projects and samples from Microsoft
    - list:
      - listitem:
        - group: Verified
      - listitem:
        - link "Sponsor"
  """
    )


async def test_AR_126_integration_test_2(page: Page) -> None:
    await page.set_content(
        """
    <div>
      <header>
        <h1>todos</h1>
        <input placeholder="What needs to be done?">
      </header>
    </div>"""
    )
    await expect(page).to_match_aria_snapshot(
        """
    - heading "todos"
    - textbox "What needs to be done?"
  """
    )


async def test_AR_127_expected_formatter(page: Page) -> None:
    await page.set_content(
        """
    <div>
      <header>
        <h1>todos</h1>
        <input placeholder="What needs to be done?">
        <button>Time 15:30</button>
      </header>
    </div>"""
    )
    expected = """
    - heading "todos"
    - textbox "Wrong text"
  """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected, timeout=1)

    # Note that error message should not contain any regular expressions,
    # unlike the baseline generated by --update-snapshots.
    message = str(exc_info.value)
    assert message.startswith(f"Page expected to match Aria snapshot '{expected}'\n")
    assert 'Expect "to_match_aria_snapshot" with timeout 1ms' in message
    assert (
        """- banner:
  - heading "todos" [level=1]
  - textbox "What needs to be done?"
  - button "Time 15:30\""""
        in message
    )
    assert "/Time" not in message


async def test_AR_128_should_unpack_escaped_names(page: Page) -> None:
    await page.set_content(
        """
      <button>Click: me</button>
    """
    )
    await expect(page).to_match_aria_snapshot(
        """
      - 'button "Click: me"'
    """
    )
    await expect(page).to_match_aria_snapshot(
        """
      - 'button /Click: me/'
    """
    )

    await page.set_content(
        """
      <button>Click / me</button>
    """
    )
    await expect(page).to_match_aria_snapshot(
        """
      - button "Click / me"
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - button /Click \/ me/
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - 'button /Click \/ me/'
    """
    )

    await page.set_content(
        """
      <button>Click " me</button>
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - button "Click \" me"
    """
    )
    await expect(page).to_match_aria_snapshot(
        """
      - button /Click " me/
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - button /Click \" me/
    """
    )

    await page.set_content(
        r"""
      <button>Click \ me</button>
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - button "Click \\ me"
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - button /Click \\ me/
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - 'button /Click \\ me/'
    """
    )

    await page.set_content(
        """
      <button>Click ' me</button>
    """
    )
    await expect(page).to_match_aria_snapshot(
        """
      - 'button "Click '' me"'
    """
    )

    await page.set_content(
        """
      <h1>heading "name" [level=1]</h1>
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - heading "heading \"name\" [level=1]" [level=1]
    """
    )

    await page.set_content(
        r"""
      <h1>heading \" [level=2]</h1>
    """
    )
    await expect(page).to_match_aria_snapshot(
        r"""
      - |
          heading    "heading \\\" [level=2]" [
             level  =   1   ]
    """
    )


async def test_AR_129_should_report_error_in_yaml(page: Page) -> None:
    await page.set_content("<h1>title</h1>")

    expected = """
      heading "title"
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        'Aria snapshot must be a YAML sequence, elements starting with " -"',
    )

    expected = """
      - heading: a:
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Nested mappings are not allowed in compact mappings at line 2, column 18:

      - heading: a:
                 ^
""",
    )


async def test_AR_130_should_report_error_in_yaml_keys(page: Page) -> None:
    await page.set_content("<h1>title</h1>")

    expected = """
      - heading "title
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Unterminated string:

heading "title
              ^
""",
    )

    expected = """
      - heading /title
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Unterminated regex:

heading /title
              ^
""",
    )

    expected = """
      - heading [level=a]
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Value of "level" attribute must be a number:

heading [level=a]
               ^
""",
    )

    expected = """
      - heading [expanded=FALSE]
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Value of "expanded" attribute must be a boolean:

heading [expanded=FALSE]
                  ^
""",
    )

    expected = """
      - heading [checked=foo]
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Value of "checked" attribute must be a boolean or "mixed":

heading [checked=foo]
                 ^
""",
    )

    expected = """
      - heading [level=]
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Value of "level" attribute must be a number:

heading [level=]
               ^
""",
    )

    expected = """
      - heading [bogus]
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Unsupported attribute [bogus]:

heading [bogus]
         ^
""",
    )

    expected = """
      - heading invalid
    """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    assert str(exc_info.value) == yaml_error_message(
        expected,
        """Unexpected input:

heading invalid
        ^
""",
    )


async def test_AR_131_call_log_should_contain_actual_snapshot(page: Page) -> None:
    await page.set_content("<h1>todos</h1>")
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - heading "wrong"
  """,
            timeout=3000,
        )

    assert 'unexpected value "- heading "todos" [level=1]"' in str(exc_info.value)


async def test_AR_132_should_parse_attributes(page: Page) -> None:
    await page.set_content(
        """
      <button aria-pressed="mixed">hello world</button>
    """
    )
    await expect(page).to_match_aria_snapshot(
        """
      - button [pressed=mixed ]
    """
    )

    await page.set_content(
        """
      <h2>hello world</h2>
    """
    )
    await expect(page.locator("body")).not_to_match_aria_snapshot(
        """
      - heading [level =  -3 ]
    """
    )


async def test_AR_133_should_not_unshift_actual_template_text(page: Page) -> None:
    await page.set_content(
        """
    <h1>title</h1>
    <h1>title 2</h1>
  """
    )
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
        - heading "title" [level=1]
    - heading "title 2" [level=1]
  """,
            timeout=1000,
        )
    assert """
        - heading "title" [level=1]
    - heading "title 2" [level=1]""" in str(
        exc_info.value
    )


async def test_AR_134_should_not_match_what_is_not_matched(page: Page) -> None:
    await page.set_content("<p>Text</p>")
    expected = """
    - paragraph:
      - button "bogus"
  """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected)
    message = str(exc_info.value)
    assert message.startswith(f"Page expected to match Aria snapshot '{expected}'\n")
    assert 'unexpected value "- paragraph: Text"' in message


async def test_AR_135_should_match_url(page: Page) -> None:
    await page.set_content(
        """
    <a href='https://example.com'>Link</a>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - link:
      - /url: /.*example.com/
  """
    )


async def test_AR_136_should_detect_unexpected_children_equal(page: Page) -> None:
    await page.set_content(
        """
    <ul>
      <li>One</li>
      <li>Two</li>
      <li>Three</li>
    </ul>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - list:
      - listitem: "One"
      - listitem: "Three"
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - list:
      - /children: equal
      - listitem: "One"
      - listitem: "Three"
  """,
            timeout=1000,
        )

    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert "\n  - listitem: Two" in str(exc_info.value)


async def test_AR_137_should_detect_unexpected_children_deep_equal(
    page: Page,
) -> None:
    await page.set_content(
        """
    <ul>
      <li>
        <ul>
          <li>1.1</li>
          <li>1.2</li>
        </ul>
      </li>
    </ul>
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - list:
      - listitem:
        - list:
          - listitem: 1.1
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - list:
      - /children: equal
      - listitem:
        - list:
          - listitem: 1.1
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - list:
      - /children: deep-equal
      - listitem:
        - list:
          - listitem: 1.1
  """,
            timeout=1000,
        )

    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert '\n      - listitem: "1.2"' in str(exc_info.value)


async def test_AR_138_should_allow_restoring_contain_mode_inside_deep_equal(
    page: Page,
) -> None:
    await page.set_content(
        """
    <ul>
      <li>
        <ul>
          <li>1.1</li>
          <li>1.2</li>
        </ul>
      </li>
    </ul>
  """
    )

    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - list:
      - /children: deep-equal
      - listitem:
        - list:
          - listitem: 1.1
  """,
            timeout=1000,
        )

    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert '\n      - listitem: "1.2"' in str(exc_info.value)

    await expect(page).to_match_aria_snapshot(
        """
    - list:
      - /children: deep-equal
      - listitem:
        - list:
          - /children: contain
          - listitem: 1.1
  """
    )


async def test_AR_139_top_level_deep_equal(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/36456
    await page.set_content(
        """
    <ul>
      <li>
        <ul>
          <li>1.1</li>
          <li>1.2</li>
        </ul>
      </li>
    </ul>
  """
    )

    expected = """
    - /children: deep-equal
    - list
  """
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(expected, timeout=1000)

    message = str(exc_info.value)
    assert message.startswith(f"Page expected to match Aria snapshot '{expected}'\n")
    assert (
        """- list:
  - listitem:
    - list:
      - listitem: "1.1"
      - listitem: "1.2\""""
        in message
    )


async def test_AR_140_generated_snapshot_includes_text_children_when_name_is_longer_than_text(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/40079
    await page.set_content(
        """
    <section>
      <div role="progressbar" aria-label="Alpha Beta" aria-valuenow="7" aria-valuemin="0" aria-valuemax="10">
        <span>Alpha</span>
        <span>7</span>
      </div>
    </section>
  """
    )
    await expect(page.locator("section")).to_match_aria_snapshot(
        """
    - /children: deep-equal
    - progressbar "Alpha Beta": Alpha 7
  """
    )


async def test_AR_141_treat_bad_regex_as_a_string(page: Page) -> None:
    await page.set_content('<a href="/foo">Log in</a>')
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - link "Log in":
      - /url: /[a/
  """,
            timeout=1,
        )
    assert "Page expected to match Aria snapshot" in str(exc_info.value)
    assert "  - /url: /[a/" in str(exc_info.value)
    assert "  - /url: /foo" in str(exc_info.value)


async def test_AR_142_invalid_attribute(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/34839
    await page.set_content(
        """
    <input type="text" aria-label="Email" aria-invalid="true" value="not-an-email">
    <input type="text" aria-label="Name" value="Alice">
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - textbox "Email" [invalid]: not-an-email
    - textbox "Name": Alice
  """
    )

    await expect(page).to_match_aria_snapshot(
        """
    - textbox "Email" [invalid=true]: not-an-email
    - textbox "Name" [invalid=false]: Alice
  """
    )

    # `aria-invalid="grammar"` and `aria-invalid="spelling"` surface their underlying value.
    await page.set_content(
        """
    <input type="text" aria-label="Bio" aria-invalid="grammar">
    <input type="text" aria-label="Note" aria-invalid="spelling">
  """
    )
    await expect(page).to_match_aria_snapshot(
        """
    - textbox "Bio" [invalid=grammar]
    - textbox "Note" [invalid=spelling]
  """
    )

    # A `grammar` value is distinct from a plain `true` invalid state.
    with pytest.raises(AssertionError) as exc_info:
        await expect(page).to_match_aria_snapshot(
            """
    - textbox "Bio" [invalid]
  """,
            timeout=1,
        )
    assert "[invalid=grammar]" in str(exc_info.value)

    # Any other non-false value falls back to `true`.
    await page.set_content(
        '<input type="text" aria-label="Zip" aria-invalid="garbage">'
    )
    await expect(page).to_match_aria_snapshot(
        """
    - textbox "Zip" [invalid]
  """
    )
