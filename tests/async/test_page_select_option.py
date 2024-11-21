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

from playwright.async_api import Error, Page, TimeoutError
from tests.server import Server


async def test_select_option_should_select_single_option(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_option_should_select_single_option_by_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_option_should_select_single_option_by_label(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", label="Indigo")
    assert await page.evaluate("result.onInput") == ["indigo"]
    assert await page.evaluate("result.onChange") == ["indigo"]


async def test_select_option_should_select_single_option_by_empty_label(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
        <select>
            <option value="indigo">Indigo</option>
            <option value="violet"></option>
        </select>
    """
    )
    assert await page.locator("select").input_value() == "indigo"
    await page.select_option("select", label="")
    assert await page.locator("select").input_value() == "violet"


async def test_select_option_should_select_single_option_by_handle(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option(
        "select", element=await page.query_selector("[id=whiteOption]")
    )
    assert await page.evaluate("result.onInput") == ["white"]
    assert await page.evaluate("result.onChange") == ["white"]


async def test_select_option_should_select_single_option_by_index(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", index=2)
    assert await page.evaluate("result.onInput") == ["brown"]
    assert await page.evaluate("result.onChange") == ["brown"]


async def test_select_option_should_select_single_option_by_index_0(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", index=0)
    assert await page.evaluate("result.onInput") == ["black"]


async def test_select_option_should_select_only_first_option(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", ["blue", "green", "red"])
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_option_should_not_throw_when_select_causes_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.eval_on_selector(
        "select",
        "select => select.addEventListener('input', () => window.location = '/empty.html')",
    )
    async with page.expect_navigation():
        await page.select_option("select", "blue")
    assert "empty.html" in page.url


async def test_select_option_should_select_multiple_options(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    await page.select_option("select", ["blue", "green", "red"])
    assert await page.evaluate("result.onInput") == ["blue", "green", "red"]
    assert await page.evaluate("result.onChange") == ["blue", "green", "red"]


async def test_select_option_should_select_multiple_options_with_attributes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    await page.select_option(
        "select",
        value="blue",
        label="Green",
        index=4,
    )
    assert await page.evaluate("result.onInput") == ["blue", "gray", "green"]
    assert await page.evaluate("result.onChange") == ["blue", "gray", "green"]


async def test_select_option_should_select_option_with_empty_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <select>
            <option value="first">First</option>
            <option value="">Second</option>
        </select>
    """
    )
    assert await page.locator("select").input_value() == "first"
    await page.select_option("select", value="")
    assert await page.locator("select").input_value() == ""


async def test_select_option_should_respect_event_bubbling(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "blue")
    assert await page.evaluate("result.onBubblingInput") == ["blue"]
    assert await page.evaluate("result.onBubblingChange") == ["blue"]


async def test_select_option_should_throw_when_element_is_not_a__select_(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(Error) as exc_info:
        await page.select_option("body", "")
    assert "Element is not a <select> element" in exc_info.value.message


async def test_select_option_should_return_on_no_matched_values(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(TimeoutError) as exc_info:
        await page.select_option("select", ["42", "abc"], timeout=1000)
    assert "Timeout 1000" in exc_info.value.message


async def test_select_option_should_return_an_array_of_matched_values(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    result = await page.select_option("select", ["blue", "black", "magenta"])
    assert result == ["black", "blue", "magenta"]


async def test_select_option_should_return_an_array_of_one_element_when_multiple_is_not_set(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.select_option("select", ["42", "blue", "black", "magenta"])
    assert len(result) == 1


async def test_select_option_should_return_on_no_values(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.select_option("select", [])
    assert result == []


async def test_select_option_should_not_allow_null_items(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    with pytest.raises(Error) as exc_info:
        await page.select_option("select", ["blue", None, "black", "magenta"])  # type: ignore
    assert "expected string, got object" in exc_info.value.message


async def test_select_option_should_unselect_with_null(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    result = await page.select_option("select", ["blue", "black", "magenta"])
    assert result == ["black", "blue", "magenta"]
    await page.select_option("select", None)
    assert await page.eval_on_selector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


async def test_select_option_should_deselect_all_options_when_passed_no_values_for_a_multiple_select(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    await page.select_option("select", ["blue", "black", "magenta"])
    await page.select_option("select", [])
    assert await page.eval_on_selector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


async def test_select_option_should_deselect_all_options_when_passed_no_values_for_a_select_without_multiple(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", ["blue", "black", "magenta"])
    await page.select_option("select", [])
    assert await page.eval_on_selector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


async def test_select_option_should_work_when_re_defining_top_level_event_class(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("window.Event = null")
    await page.select_option("select", "blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_options_should_fall_back_to_selecting_by_label(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "Blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]
