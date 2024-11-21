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

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server


def test_select_option_should_select_single_option(server: Server, page: Page) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", "blue")
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]


def test_select_option_should_select_single_option_by_value(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", "blue")
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]


def test_select_option_should_select_single_option_by_label(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", label="Indigo")
    assert page.evaluate("result.onInput") == ["indigo"]
    assert page.evaluate("result.onChange") == ["indigo"]


def test_select_option_should_select_single_option_by_empty_label(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
        <select>
            <option value="indigo">Indigo</option>
            <option value="violet"></option>
        </select>
    """
    )
    assert page.locator("select").input_value() == "indigo"
    page.select_option("select", label="")
    assert page.locator("select").input_value() == "violet"


def test_select_option_should_select_single_option_by_handle(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", element=page.query_selector("[id=whiteOption]"))
    assert page.evaluate("result.onInput") == ["white"]
    assert page.evaluate("result.onChange") == ["white"]


def test_select_option_should_select_single_option_by_index(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", index=2)
    assert page.evaluate("result.onInput") == ["brown"]
    assert page.evaluate("result.onChange") == ["brown"]


def test_select_option_should_select_single_option_by_index_0(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", index=0)
    assert page.evaluate("result.onInput") == ["black"]


def test_select_option_should_select_only_first_option(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", ["blue", "green", "red"])
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]


def test_select_option_should_not_throw_when_select_causes_navigation(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.eval_on_selector(
        "select",
        "select => select.addEventListener('input', () => window.location = '/empty.html')",
    )
    with page.expect_navigation():
        page.select_option("select", "blue")
    assert "empty.html" in page.url


def test_select_option_should_select_multiple_options(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.evaluate("makeMultiple()")
    page.select_option("select", ["blue", "green", "red"])
    assert page.evaluate("result.onInput") == ["blue", "green", "red"]
    assert page.evaluate("result.onChange") == ["blue", "green", "red"]


def test_select_option_should_select_multiple_options_with_attributes(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.evaluate("makeMultiple()")
    page.select_option(
        "select",
        value="blue",
        label="Green",
        index=4,
    )
    assert page.evaluate("result.onInput") == ["blue", "gray", "green"]
    assert page.evaluate("result.onChange") == ["blue", "gray", "green"]


def test_select_option_should_select_option_with_empty_value(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
        <select>
            <option value="first">First</option>
            <option value="">Second</option>
        </select>
    """
    )
    assert page.locator("select").input_value() == "first"
    page.select_option("select", value="")
    assert page.locator("select").input_value() == ""


def test_select_option_should_respect_event_bubbling(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", "blue")
    assert page.evaluate("result.onBubblingInput") == ["blue"]
    assert page.evaluate("result.onBubblingChange") == ["blue"]


def test_select_option_should_throw_when_element_is_not_a__select_(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(Error) as exc_info:
        page.select_option("body", "")
    assert "Element is not a <select> element" in exc_info.value.message


def test_select_option_should_return_on_no_matched_values(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(Error) as exc_info:
        page.select_option("select", ["42", "abc"], timeout=1000)
    assert "Timeout 1000" in exc_info.value.message


def test_select_option_should_return_an_array_of_matched_values(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.evaluate("makeMultiple()")
    result = page.select_option("select", ["blue", "black", "magenta"])
    assert result == ["black", "blue", "magenta"]


def test_select_option_should_return_an_array_of_one_element_when_multiple_is_not_set(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    result = page.select_option("select", ["42", "blue", "black", "magenta"])
    assert len(result) == 1


def test_select_option_should_return_on_no_values(server: Server, page: Page) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    result = page.select_option("select", [])
    assert result == []


def test_select_option_should_unselect_with_null(server: Server, page: Page) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.evaluate("makeMultiple()")
    result = page.select_option("select", ["blue", "black", "magenta"])
    assert result == ["black", "blue", "magenta"]
    page.select_option("select", None)
    assert page.eval_on_selector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


def test_select_option_should_deselect_all_options_when_passed_no_values_for_a_multiple_select(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.evaluate("makeMultiple()")
    page.select_option("select", ["blue", "black", "magenta"])
    page.select_option("select", [])
    assert page.eval_on_selector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


def test_select_option_should_deselect_all_options_when_passed_no_values_for_a_select_without_multiple(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", ["blue", "black", "magenta"])
    page.select_option("select", [])
    assert page.eval_on_selector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


def test_select_option_should_work_when_re_defining_top_level_event_class(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.evaluate("window.Event = null")
    page.select_option("select", "blue")
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]


def test_select_options_should_fall_back_to_selecting_by_label(
    server: Server, page: Page
) -> None:
    page.goto(server.PREFIX + "/input/select.html")
    page.select_option("select", "Blue")
    assert page.evaluate("result.onInput") == ["blue"]
    assert page.evaluate("result.onChange") == ["blue"]
