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

"""Python only: tests of behaviors that no upstream test covers."""

import datetime
import re

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server


async def test_assertions_page_to_have_title(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>new title</title>")
    await expect(page).to_have_title("new title")
    await expect(page).to_have_title(re.compile("new title"))
    with pytest.raises(AssertionError):
        await expect(page).to_have_title("not the current title", timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).to_have_title(
            re.compile("not the current title"), timeout=750
        )
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_title(re.compile("new title"), timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_title("new title", timeout=750)
    await expect(page).not_to_have_title("great title", timeout=750)
    await page.evaluate(
        """
        setTimeout(() => {
            document.title = 'great title';
        }, 2000);
    """
    )
    await expect(page).to_have_title("great title")
    await expect(page).to_have_title(re.compile("great title"))


async def test_assertions_page_to_have_url(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await expect(page).to_have_url(server.EMPTY_PAGE)
    await expect(page).to_have_url(re.compile(r".*/empty\.html"))
    with pytest.raises(AssertionError):
        await expect(page).to_have_url("nooooo", timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).to_have_url(re.compile("not-the-url"), timeout=750)
    await page.evaluate(
        """
        setTimeout(() => {
            window.location = window.location.origin + '/grid.html';
        }, 2000);
    """
    )
    await expect(page).to_have_url(server.PREFIX + "/grid.html")
    await expect(page).not_to_have_url(server.EMPTY_PAGE, timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_url(re.compile(r".*/grid\.html"), timeout=750)
    with pytest.raises(AssertionError):
        await expect(page).not_to_have_url(server.PREFIX + "/grid.html", timeout=750)
    await expect(page).to_have_url(re.compile(r".*/grid\.html"))
    await expect(page).not_to_have_url("**/empty.html", timeout=750)


async def test_assertions_locator_to_contain_class(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class='foo bar baz'></div>")
    locator = page.locator("div")
    await expect(locator).to_contain_class("")
    await expect(locator).to_contain_class("bar")
    await expect(locator).to_contain_class("baz bar")
    await expect(locator).to_contain_class("  bar   foo ")
    await expect(locator).not_to_contain_class(
        "  baz   not-matching "
    )  # Strip whitespace and match individual classes
    with pytest.raises(AssertionError) as excinfo:
        await expect(locator).to_contain_class("does-not-exist", timeout=100)

    assert excinfo.match("Locator expected to contain class 'does-not-exist'")
    assert excinfo.match("Actual value: foo bar baz")
    assert excinfo.match(
        'Expect "to_contain_class" locator\\("div"\\) with timeout 100ms'
    )

    await page.set_content(
        '<div class="foo"></div><div class="hello bar"></div><div class="baz"></div>'
    )
    await expect(locator).to_contain_class(["foo", "hello", "baz"])
    await expect(locator).not_to_contain_class(["not-there", "hello", "baz"])
    await expect(locator).not_to_contain_class(["foo", "hello"])


async def test_assertions_locator_to_have_css(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        "<div class=foobar style='color: rgb(234, 74, 90);'>kek</div>"
    )
    await expect(page.locator("div.foobar")).to_have_css("color", "rgb(234, 74, 90)")
    await expect(page.locator("div.foobar")).not_to_have_css(
        "color", "rgb(42, 42, 42)", timeout=100
    )
    with pytest.raises(AssertionError):
        await expect(page.locator("div.foobar")).to_have_css(
            "color", "rgb(42, 42, 42)", timeout=100
        )


async def test_assertions_locator_to_have_id(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div class=foobar id=kek>kek</div>")
    await expect(page.locator("div.foobar")).to_have_id("kek")
    await expect(page.locator("div.foobar")).not_to_have_id("top", timeout=100)
    with pytest.raises(AssertionError):
        await expect(page.locator("div.foobar")).to_have_id("top", timeout=100)


async def test_assertions_locator_to_have_js_property(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div></div>")
    await page.eval_on_selector(
        "div", "e => e.foo = { a: 1, b: 'string', c: new Date(1627503992000) }"
    )
    await expect(page.locator("div")).to_have_js_property(
        "foo",
        {
            "a": 1,
            "b": "string",
            "c": datetime.datetime.fromtimestamp(1627503992000 / 1000),
        },
    )


async def test_assertions_locator_to_have_text(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<div id=foobar>kek</div>")
    await expect(page.locator("div#foobar")).to_have_text("kek")
    await expect(page.locator("div#foobar")).not_to_have_text("top", timeout=100)

    await page.set_content("<div>Text    \n1</div><div>Text   2a</div>")
    # Should only normalize whitespace in the first item.
    await expect(page.locator("div")).to_have_text(
        ["Text  1", re.compile(r"Text   \d+a")]
    )
    # Should work with a tuple
    await expect(page.locator("div")).to_have_text(
        ("Text  1", re.compile(r"Text   \d+a"))
    )


async def test_assertions_locator_to_have_value(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=text id=foo>")
    my_input = page.locator("#foo")
    await expect(my_input).to_have_value("")
    await expect(my_input).not_to_have_value("bar", timeout=100)
    await my_input.fill("kektus")
    await expect(my_input).to_have_value("kektus")


async def test_assertions_locator_to_be_disabled_enabled(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<input type=checkbox>")
    my_checkbox = page.locator("input")
    await expect(my_checkbox).not_to_be_disabled()
    await expect(my_checkbox).to_be_enabled()
    with pytest.raises(AssertionError):
        await expect(my_checkbox).to_be_disabled(timeout=100)
    await my_checkbox.evaluate("e => e.disabled = true")
    await expect(my_checkbox).to_be_disabled()
    with pytest.raises(AssertionError, match="Locator expected to be enabled"):
        await expect(my_checkbox).to_be_enabled(timeout=100)


async def test_assertions_locator_to_be_enabled_with_false_throws_good_exception(
    page: Page,
) -> None:
    await page.set_content("<button>Text</button>")
    with pytest.raises(AssertionError, match="Locator expected to be disabled"):
        await expect(page.locator("button")).to_be_enabled(enabled=False)


async def test_assertions_locator_to_be_editable_with_false_and_throw_good_exception(
    page: Page,
) -> None:
    await page.set_content("<input></input>")
    with pytest.raises(AssertionError, match="Locator expected to be readonly"):
        await expect(page.locator("input")).to_be_editable(editable=False)


async def test_assertions_locator_to_be_visible_with_false_throws_good_exception(
    page: Page,
) -> None:
    await page.set_content("<button>hello</button>")
    with pytest.raises(AssertionError, match="Locator expected to be hidden"):
        await expect(page.locator("button")).to_be_visible(visible=False)


async def test_should_print_response_with_text_content_type_if_to_be_ok_fails(
    page: Page, server: Server
) -> None:
    server.set_route(
        "/text-content-type",
        lambda r: (
            r.setResponseCode(404),
            r.setHeader("content-type", "text/plain"),
            r.write(b"Text error"),
            r.finish(),
        ),
    )
    server.set_route(
        "/no-content-type",
        lambda r: (
            r.setResponseCode(404),
            r.write(b"No content type error"),
            r.finish(),
        ),
    )
    server.set_route(
        "/binary-content-type",
        lambda r: (
            r.setResponseCode(404),
            r.setHeader("content-type", "image/bmp"),
            r.write(b"Image content type error"),
            r.finish(),
        ),
    )

    response = await page.request.get(server.PREFIX + "/text-content-type")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/text-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" in error_message
    assert "Text error" in error_message

    response = await page.request.get(server.PREFIX + "/no-content-type")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/no-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" not in error_message
    assert "No content type error" not in error_message

    response = await page.request.get(server.PREFIX + "/binary-content-type")
    with pytest.raises(AssertionError) as excinfo:
        await expect(response).to_be_ok()
    error_message = str(excinfo.value)
    assert ("→ GET " + server.PREFIX + "/binary-content-type") in error_message
    assert "← 404 Not Found" in error_message
    assert "Response Text:" not in error_message
    assert "Image content type error" not in error_message


async def test_should_print_users_message_for_page_based_assertion(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        await expect(page, "Title is not new").to_have_title("old title", timeout=100)
    assert "Title is not new" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        await expect(page).to_have_title("old title", timeout=100)
    assert "Page title expected to be" in str(excinfo.value)


async def test_should_print_expected_value_with_custom_message(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>new title</title>")
    with pytest.raises(AssertionError) as excinfo:
        await expect(page, "custom-message").to_have_title("old title", timeout=100)
    assert "custom-message" in str(excinfo.value)
    assert "Expected value: 'old title'" in str(excinfo.value)
    with pytest.raises(AssertionError) as excinfo:
        await expect(page.get_by_text("hello"), "custom-message").to_be_visible(
            timeout=100
        )
    assert "custom-message" in str(excinfo.value)
    assert "Expected value" not in str(excinfo.value)


async def test_should_be_attached_with_attached_false_and_throw_good_error(
    page: Page,
) -> None:
    await page.set_content("<button>hello</button>")
    locator = page.locator("button")
    with pytest.raises(AssertionError, match="Locator expected to be detached"):
        await expect(locator).to_be_attached(attached=False, timeout=1)


async def test_should_be_attached_fail(page: Page) -> None:
    await page.set_content("<button>Hello</button>")
    locator = page.locator("input")
    with pytest.raises(
        AssertionError, match="Locator expected to be attached"
    ) as exc_info:
        await expect(locator).to_be_attached(timeout=1000)
    assert "locator resolved to" not in exc_info.value.args[0]


async def test_should_be_able_to_set_custom_global_timeout(page: Page) -> None:
    try:
        expect.set_options(timeout=111)
        with pytest.raises(AssertionError) as exc_info:
            await expect(page.locator("#a1")).to_be_visible()
        assert 'Expect "to_be_visible" locator("#a1") with timeout 111ms' in str(
            exc_info.value
        )
    finally:
        expect.set_options(timeout=None)


async def test_soft_outside_scope_raises_runtime_error(
    page: Page, server: Server
) -> None:
    await page.set_content("<div>hello</div>")
    with pytest.raises(RuntimeError, match="pytest-playwright"):
        await expect.soft(page.locator("div")).to_have_text("nope", timeout=500)


async def test_soft_inside_scope_collects_failures(page: Page, server: Server) -> None:
    from playwright._impl._assertions import _soft_scope

    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>actual</title><div>hello</div>")

    with _soft_scope() as errors:
        # should collect, not raise
        await expect.soft(page).to_have_title("expected", timeout=500)
        await expect.soft(page.locator("div")).to_have_text("goodbye", timeout=500)
        # passing soft should not affect the collector
        await expect.soft(page.locator("div")).to_have_text("hello")
        # nested .not_ should still be soft
        await expect.soft(page.locator("div")).not_to_have_text("hello", timeout=500)

    assert len(errors) == 3
    assert all(isinstance(e, AssertionError) for e in errors)


async def test_soft_does_not_leak_between_scopes(page: Page, server: Server) -> None:
    from playwright._impl._assertions import _soft_scope

    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<title>actual</title>")

    with _soft_scope() as errors_a:
        await expect.soft(page).to_have_title("nope", timeout=500)
    assert len(errors_a) == 1

    with _soft_scope() as errors_b:
        pass
    assert errors_b == []

    # After scope ends, soft assertions raise RuntimeError again.
    await page.set_content("<div>hello</div>")
    with pytest.raises(RuntimeError, match="pytest-playwright"):
        await expect.soft(page.locator("div")).to_have_text("nope", timeout=500)


async def test_assertions_should_include_aria_snapshot_in_separate_section(
    page: Page,
) -> None:
    await page.set_content(
        """
        <div id="hidden" style="display: none"><span>secret</span></div>
        <main><h1>Page Heading</h1></main>
        """
    )
    with pytest.raises(AssertionError) as excinfo:
        await expect(page.locator("#hidden")).to_be_visible(timeout=500)
    message = str(excinfo.value)
    assert "Aria snapshot:" in message
    # The aria snapshot lives in its own section, not in the "Actual value" line.
    assert "Actual value: hidden" in message
    actual_line = message.split("\n")[1]
    assert 'heading "Page Heading"' not in actual_line
    assert message.index('heading "Page Heading"') > message.index("Aria snapshot:")


@pytest.mark.parametrize("timeout", [float("inf"), float("-inf"), float("nan")])
async def test_assertions_should_reject_non_finite_timeout(
    page: Page, timeout: float
) -> None:
    with pytest.raises(Error, match="Out of range float values are not JSON"):
        await expect(page.locator("div")).to_be_visible(timeout=timeout)
    # The driver connection must survive the rejected call.
    assert await page.evaluate("1 + 1") == 2
