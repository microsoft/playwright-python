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

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict

from playwright.async_api import Page


async def test_jshandle_evaluate_work(page: Page) -> None:
    window_handle = await page.evaluate_handle("window")
    assert window_handle
    assert (
        repr(window_handle) == f"<JSHandle preview={window_handle._impl_obj._preview}>"
    )


async def test_jshandle_evaluate_accept_object_handle_as_argument(page: Page) -> None:
    navigator_handle = await page.evaluate_handle("navigator")
    text = await page.evaluate("e => e.userAgent", navigator_handle)
    assert "Mozilla" in text


async def test_jshandle_evaluate_accept_handle_to_primitive_types(page: Page) -> None:
    handle = await page.evaluate_handle("5")
    is_five = await page.evaluate("e => Object.is(e, 5)", handle)
    assert is_five


async def test_jshandle_evaluate_accept_nested_handle(page: Page) -> None:
    foo = await page.evaluate_handle('({ x: 1, y: "foo" })')
    result = await page.evaluate("({ foo }) => foo", {"foo": foo})
    assert result == {"x": 1, "y": "foo"}


async def test_jshandle_evaluate_accept_nested_window_handle(page: Page) -> None:
    foo = await page.evaluate_handle("window")
    result = await page.evaluate("({ foo }) => foo === window", {"foo": foo})
    assert result


async def test_jshandle_evaluate_accept_multiple_nested_handles(page: Page) -> None:
    foo = await page.evaluate_handle('({ x: 1, y: "foo" })')
    bar = await page.evaluate_handle("5")
    baz = await page.evaluate_handle('["baz"]')
    result = await page.evaluate(
        "x => JSON.stringify(x)",
        {"a1": {"foo": foo}, "a2": {"bar": bar, "arr": [{"baz": baz}]}},
    )
    assert json.loads(result) == {
        "a1": {"foo": {"x": 1, "y": "foo"}},
        "a2": {"bar": 5, "arr": [{"baz": ["baz"]}]},
    }


async def test_jshandle_evaluate_should_work_for_circular_objects(page: Page) -> None:
    a: Dict[str, Any] = {"x": 1}
    a["y"] = a
    result = await page.evaluate("a => { a.y.x += 1; return a; }", a)
    assert result["x"] == 2
    assert result["y"]["x"] == 2
    assert result == result["y"]


async def test_jshandle_evaluate_accept_same_nested_object_multiple_times(
    page: Page,
) -> None:
    foo = {"x": 1}
    assert await page.evaluate(
        "x => x", {"foo": foo, "bar": [foo], "baz": {"foo": foo}}
    ) == {"foo": {"x": 1}, "bar": [{"x": 1}], "baz": {"foo": {"x": 1}}}


async def test_jshandle_evaluate_accept_object_handle_to_unserializable_value(
    page: Page,
) -> None:
    handle = await page.evaluate_handle("() => Infinity")
    assert await page.evaluate("e => Object.is(e, Infinity)", handle)


async def test_jshandle_evaluate_pass_configurable_args(page: Page) -> None:
    result = await page.evaluate(
        """arg => {
            if (arg.foo !== 42)
            throw new Error('Not a 42');
            arg.foo = 17;
            if (arg.foo !== 17)
            throw new Error('Not 17');
            delete arg.foo;
            if (arg.foo === 17)
            throw new Error('Still 17');
            return arg;
        }""",
        {"foo": 42},
    )
    assert result == {}


async def test_jshandle_properties_get_property(page: Page) -> None:
    handle1 = await page.evaluate_handle(
        """() => ({
            one: 1,
            two: 2,
            three: 3
        })"""
    )
    handle2 = await handle1.get_property("two")
    assert await handle2.json_value() == 2


async def test_jshandle_properties_work_with_undefined_null_and_empty(
    page: Page,
) -> None:
    handle = await page.evaluate_handle(
        """() => ({
            undefined: undefined,
            null: null,
        })"""
    )
    undefined_handle = await handle.get_property("undefined")
    assert await undefined_handle.json_value() is None
    null_handle = await handle.get_property("null")
    assert await null_handle.json_value() is None
    empty_handle = await handle.get_property("empty")
    assert await empty_handle.json_value() is None


async def test_jshandle_properties_work_with_unserializable_values(page: Page) -> None:
    handle = await page.evaluate_handle(
        """() => ({
            infinity: Infinity,
            negInfinity: -Infinity,
            nan: NaN,
            negZero: -0
        })"""
    )
    infinity_handle = await handle.get_property("infinity")
    assert await infinity_handle.json_value() == float("inf")
    neg_infinity_handle = await handle.get_property("negInfinity")
    assert await neg_infinity_handle.json_value() == float("-inf")
    nan_handle = await handle.get_property("nan")
    assert math.isnan(await nan_handle.json_value()) is True
    neg_zero_handle = await handle.get_property("negZero")
    assert await neg_zero_handle.json_value() == float("-0")


async def test_jshandle_properties_get_properties(page: Page) -> None:
    handle = await page.evaluate_handle('() => ({ foo: "bar" })')
    properties = await handle.get_properties()
    assert "foo" in properties
    foo = properties["foo"]
    assert await foo.json_value() == "bar"


async def test_jshandle_properties_return_empty_map_for_non_objects(page: Page) -> None:
    handle = await page.evaluate_handle("123")
    properties = await handle.get_properties()
    assert properties == {}


async def test_jshandle_json_value_work(page: Page) -> None:
    handle = await page.evaluate_handle('() => ({foo: "bar"})')
    json = await handle.json_value()
    assert json == {"foo": "bar"}


async def test_jshandle_json_value_work_with_dates(page: Page) -> None:
    handle = await page.evaluate_handle('() => new Date("2020-05-27T01:31:38.506Z")')
    json = await handle.json_value()
    assert json == datetime.fromisoformat("2020-05-27T01:31:38.506").replace(
        tzinfo=timezone.utc
    )


async def test_jshandle_json_value_should_work_for_circular_object(page: Page) -> None:
    handle = await page.evaluate_handle("const a = {}; a.b = a; a")
    a: Dict[str, Any] = {}
    a["b"] = a
    result = await handle.json_value()
    # Node test looks like the below, but assert isn't smart enough to handle this:
    # assert await handle.json_value() == a
    assert result["b"] == result


async def test_jshandle_as_element_work(page: Page) -> None:
    handle = await page.evaluate_handle("document.body")
    element = handle.as_element()
    assert element is not None


async def test_jshandle_as_element_return_none_for_non_elements(page: Page) -> None:
    handle = await page.evaluate_handle("2")
    element = handle.as_element()
    assert element is None


async def test_jshandle_to_string_work_for_primitives(page: Page) -> None:
    number_handle = await page.evaluate_handle("2")
    assert str(number_handle) == "2"
    string_handle = await page.evaluate_handle('"a"')
    assert str(string_handle) == "a"


async def test_jshandle_to_string_work_for_complicated_objects(
    page: Page, browser_name: str
) -> None:
    handle = await page.evaluate_handle("window")
    if browser_name != "firefox":
        assert str(handle) == "Window"
    else:
        assert str(handle) == "JSHandle@object"


async def test_jshandle_to_string_work_for_promises(page: Page) -> None:
    handle = await page.evaluate_handle("({b: Promise.resolve(123)})")
    b_handle = await handle.get_property("b")
    assert str(b_handle) == "Promise"
