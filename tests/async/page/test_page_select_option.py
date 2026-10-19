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

"""Port of tests/page/page-select-option.spec.ts."""

import asyncio
from typing import Any, List, cast

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server

from ..utils import Utils


async def give_it_a_chance_to_resolve(utils: Utils, page: Page) -> None:
    await utils.rafraf(page, 5)


async def test_SO_001_should_select_single_option_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "blue")
    assert await page.evaluate("() => window['result'].onInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onChange") == ["blue"]


async def test_SO_002_should_select_single_option_by_value(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    # Python's value= is upstream's { value }: it matches the value or the label.
    await page.select_option("select", value="blue")
    assert await page.evaluate("() => window['result'].onInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onChange") == ["blue"]


async def test_SO_003_should_fall_back_to_selecting_by_label(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "Blue")
    assert await page.evaluate("() => window['result'].onInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onChange") == ["blue"]


async def test_SO_004_should_select_single_option_by_label(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", label="Indigo")
    assert await page.evaluate("() => window['result'].onInput") == ["indigo"]
    assert await page.evaluate("() => window['result'].onChange") == ["indigo"]


async def test_SO_005_should_select_single_option_by_label_with_html_whitespace(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", label="HTML")
    assert await page.evaluate("() => window['result'].onInput") == ["html"]
    assert await page.evaluate("() => window['result'].onChange") == ["html"]


async def test_SO_006_should_select_single_option_by_handle(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option(
        "select", element=await page.query_selector("[id=whiteOption]")
    )
    assert await page.evaluate("() => window['result'].onInput") == ["white"]
    assert await page.evaluate("() => window['result'].onChange") == ["white"]


async def test_SO_007_should_select_single_option_by_index(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", index=2)
    assert await page.evaluate("() => window['result'].onInput") == ["brown"]
    assert await page.evaluate("() => window['result'].onChange") == ["brown"]


async def test_SO_008_should_select_single_option_by_multiple_attributes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    # Python has no option object with several attributes: value= and label= are
    # separate options, and both match the green option.
    await page.select_option("select", value="green", label="Green")
    assert await page.evaluate("() => window['result'].onInput") == ["green"]
    assert await page.evaluate("() => window['result'].onChange") == ["green"]


async def test_SO_010_should_select_only_first_option(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", ["blue", "green", "red"])
    assert await page.evaluate("() => window['result'].onInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onChange") == ["blue"]


async def test_SO_011_should_not_throw_when_select_causes_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.eval_on_selector(
        "select",
        "select => select.addEventListener('input', () => window.location.href = '/empty.html')",
    )
    async with page.expect_navigation():
        await page.select_option("select", "blue")
    assert "empty.html" in page.url


async def test_SO_012_should_select_multiple_options(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    await page.select_option("select", ["blue", "green", "red"])
    assert await page.evaluate("() => window['result'].onInput") == [
        "blue",
        "green",
        "red",
    ]
    assert await page.evaluate("() => window['result'].onChange") == [
        "blue",
        "green",
        "red",
    ]


async def test_SO_013_should_select_multiple_options_with_attributes(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    await page.select_option("select", value="blue", label="Green", index=4)
    assert await page.evaluate("() => window['result'].onInput") == [
        "blue",
        "gray",
        "green",
    ]
    assert await page.evaluate("() => window['result'].onChange") == [
        "blue",
        "gray",
        "green",
    ]


async def test_SO_014_should_respect_event_bubbling(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", "blue")
    assert await page.evaluate("() => window['result'].onBubblingInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onBubblingChange") == ["blue"]


async def test_SO_015_should_throw_when_element_is_not_a_select(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(Error) as exc_info:
        await page.select_option("body", "")
    assert "Element is not a <select> element" in exc_info.value.message


async def test_SO_016_should_return_on_no_matched_values(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.select_option("select", [])
    assert result == []


async def test_SO_017_should_return_an_array_of_matched_values(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    result = await page.select_option("select", ["blue", "black", "magenta"])
    assert all(value in ["blue", "black", "magenta"] for value in result) is True


async def test_SO_018_should_return_an_array_of_one_element_when_multiple_is_not_set(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.select_option("select", ["42", "blue", "black", "magenta"])
    assert len(result) == 1


async def test_SO_019_should_return_on_no_values(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.select_option("select", [])
    assert result == []


async def test_SO_020_should_not_allow_null_items(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    with pytest.raises(Error) as exc_info:
        await page.select_option(
            "select", cast(Any, ["blue", None, "black", "magenta"])
        )
    assert "options[1]: expected object, got null" in exc_info.value.message


async def test_SO_021_should_unselect_with_null(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    result = await page.select_option("select", ["blue", "black", "magenta"])
    assert all(value in ["blue", "black", "magenta"] for value in result) is True
    await page.select_option("select", None)
    assert (
        await page.eval_on_selector(
            "select",
            "select => Array.from(select.options).every(option => !option.selected)",
        )
        is True
    )


async def test_SO_022_should_deselect_all_options_when_passed_no_values_for_a_multiple_select(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    await page.select_option("select", ["blue", "black", "magenta"])
    await page.select_option("select", [])
    assert (
        await page.eval_on_selector(
            "select",
            "select => Array.from(select.options).every(option => !option.selected)",
        )
        is True
    )


async def test_SO_023_should_deselect_all_options_when_passed_no_values_for_a_select_without_multiple(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.select_option("select", ["blue", "black", "magenta"])
    await page.select_option("select", [])
    assert (
        await page.eval_on_selector(
            "select",
            "select => Array.from(select.options).every(option => !option.selected)",
        )
        is True
    )


async def test_SO_024_should_throw_if_passed_wrong_types(page: Page) -> None:
    await page.set_content('<select><option value="12"/></select>')

    # The Python client sends each value as an option object ({ valueOrLabel },
    # { label }, { index }), so the driver names the field of that object.
    with pytest.raises(Error) as exc_info:
        await page.select_option("select", cast(Any, 12))
    assert (
        "options[0].valueOrLabel: expected string, got number" in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        await page.select_option("select", value=cast(Any, 12))
    assert (
        "options[0].valueOrLabel: expected string, got number" in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        await page.select_option("select", label=cast(Any, 12))
    assert "options[0].label: expected string, got number" in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        await page.select_option("select", index=cast(Any, "12"))
    assert "options[0].index: expected integer, got string" in exc_info.value.message


# @see https://github.com/GoogleChrome/puppeteer/issues/3327
async def test_SO_025_should_work_when_re_defining_top_level_event_class(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window.Event = null")
    await page.select_option("select", "blue")
    assert await page.evaluate("() => window['result'].onInput") == ["blue"]
    assert await page.evaluate("() => window['result'].onChange") == ["blue"]


async def test_SO_026_should_wait_for_option_to_be_present(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    did_select = False

    async def select() -> List[str]:
        nonlocal did_select
        result = await page.select_option("select", "scarlet")
        did_select = True
        return result

    select_promise = asyncio.create_task(select())
    await give_it_a_chance_to_resolve(utils, page)
    assert did_select is False
    await page.eval_on_selector(
        "select",
        """select => {
    const option = document.createElement('option');
    option.value = 'scarlet';
    option.textContent = 'Scarlet';
    select.appendChild(option);
  }""",
    )
    items = await select_promise
    assert items == ["scarlet"]


async def test_SO_027_should_wait_for_option_index_to_be_present(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    length = await page.eval_on_selector("select", "select => select.options.length")
    did_select = False

    async def select() -> List[str]:
        nonlocal did_select
        result = await page.select_option("select", index=length)
        did_select = True
        return result

    select_promise = asyncio.create_task(select())
    await give_it_a_chance_to_resolve(utils, page)
    assert did_select is False
    await page.eval_on_selector(
        "select",
        """select => {
    const option = document.createElement('option');
    option.value = 'scarlet';
    option.textContent = 'Scarlet';
    select.appendChild(option);
  }""",
    )
    items = await select_promise
    assert items == ["scarlet"]


async def test_SO_028_should_wait_for_multiple_options_to_be_present(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("() => window['makeMultiple']()")
    did_select = False

    async def select() -> List[str]:
        nonlocal did_select
        result = await page.select_option("select", ["green", "scarlet"])
        did_select = True
        return result

    select_promise = asyncio.create_task(select())
    await give_it_a_chance_to_resolve(utils, page)
    assert did_select is False
    await page.eval_on_selector(
        "select",
        """select => {
    const option = document.createElement('option');
    option.value = 'scarlet';
    option.textContent = 'Scarlet';
    select.appendChild(option);
  }""",
    )
    items = await select_promise
    assert items == ["green", "scarlet"]


async def test_SO_029_input_event_composed_should_be_true_and_cross_shadow_dom_boundary(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28726
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """<body><script>
  const div = document.createElement('div');
  const shadowRoot = div.attachShadow({mode: 'open'});
  shadowRoot.innerHTML = `<select>
    <option value="black">Black</option>
    <option value="blue">Blue</option>
  </select>`;
  document.body.appendChild(div);
</script></body>"""
    )
    await page.locator("body").evaluate(
        """select => {
    window.firedBodyEvents = [];
    for (const event of ['input', 'change']) {
      select.addEventListener(event, e => {
        window.firedBodyEvents.push(e.type + ':' + e.composed);
      }, false);
    }
  }"""
    )

    await page.locator("select").evaluate(
        """select => {
    window.firedEvents = [];
    for (const event of ['input', 'change']) {
      select.addEventListener(event, e => {
        window.firedEvents.push(e.type + ':' + e.composed);
      }, false);
    }
  }"""
    )
    await page.select_option("select", "blue")
    assert await page.evaluate("() => window['firedEvents']") == [
        "input:true",
        "change:false",
    ]
    assert await page.evaluate("() => window['firedBodyEvents']") == ["input:true"]


async def test_SO_030_should_wait_for_select_to_be_enabled(page: Page) -> None:
    await page.set_content(
        """
    <select disabled>
      <option>one</option>
      <option>two</option>
    </select>

    <script>
    function hydrate() {
      const select = document.querySelector('select');
      select.removeAttribute('disabled');
      select.addEventListener('change', () => {
        window['result'] = select.value;
      });
    }
    </script>
  """
    )

    async def select() -> None:
        await page.locator("select").select_option("two")

    select_promise = asyncio.create_task(select())
    await page.wait_for_timeout(1000)
    await page.evaluate("() => window.hydrate()")
    await select_promise
    assert await page.evaluate("() => window['result']") == "two"
    await expect(page.locator("select")).to_have_value("two")


async def test_SO_031_should_wait_for_option_to_be_enabled(page: Page) -> None:
    await page.set_content(
        """
    <select>
      <option>one</option>
      <option disabled id=myoption>two</option>
    </select>

    <script>
    function hydrate() {
      const option = document.querySelector('#myoption');
      option.removeAttribute('disabled');
      const select = document.querySelector('select');
      select.addEventListener('change', () => {
        window['result'] = select.value;
      });
    }
    </script>
  """
    )

    with pytest.raises(Error) as exc_info:
        await page.locator("select").select_option("two", timeout=1000)
    assert "option being selected is not enabled" in exc_info.value.message

    async def select() -> None:
        await page.locator("select").select_option("two")

    select_promise = asyncio.create_task(select())
    await page.wait_for_timeout(1000)
    await page.evaluate("() => window.hydrate()")
    await select_promise
    assert await page.evaluate("() => window['result']") == "two"
    await expect(page.locator("select")).to_have_value("two")


async def test_SO_032_should_wait_for_optgroup_to_be_enabled(page: Page) -> None:
    await page.set_content(
        """
    <select>
      <option>one</option>
      <optgroup label="Group" disabled id=mygroup>
        <option>two</option>
      </optgroup>
    </select>

    <script>
    function hydrate() {
      const group = document.querySelector('#mygroup');
      group.removeAttribute('disabled');
      const select = document.querySelector('select');
      select.addEventListener('change', () => {
        window['result'] = select.value;
      });
    }
    </script>
  """
    )

    with pytest.raises(Error) as exc_info:
        await page.locator("select").select_option("two", timeout=1000)
    assert "option being selected is not enabled" in exc_info.value.message

    async def select() -> None:
        await page.locator("select").select_option("two")

    select_promise = asyncio.create_task(select())
    await page.wait_for_timeout(1000)
    await page.evaluate("() => window.hydrate()")
    await select_promise
    assert await page.evaluate("() => window['result']") == "two"
    await expect(page.locator("select")).to_have_value("two")


async def test_SO_033_should_wait_for_select_to_be_swapped(page: Page) -> None:
    await page.set_content(
        """
    <select disabled>
      <option>one</option>
      <option>two</option>
    </select>

    <script>
    function hydrate() {
      const select = document.querySelector('select');
      select.remove();

      const newSelect = document.createElement('select');
      const option1 = document.createElement('option');
      option1.textContent = 'one';
      newSelect.appendChild(option1);
      const option2 = document.createElement('option');
      option2.textContent = 'two';
      newSelect.appendChild(option2);

      document.body.appendChild(newSelect);

      newSelect.addEventListener('change', () => {
        window['result'] = newSelect.value;
      });
    }
    </script>
  """
    )

    async def select() -> None:
        await page.locator("select").select_option("two")

    select_promise = asyncio.create_task(select())
    await page.wait_for_timeout(1000)
    await page.evaluate("() => window.hydrate()")
    await select_promise
    await expect(page.locator("select")).to_have_value("two")
    assert await page.evaluate("() => window['result']") == "two"
