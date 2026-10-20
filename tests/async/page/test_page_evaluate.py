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

"""Port of tests/page/page-evaluate.spec.ts."""

import asyncio
import datetime
import math
import re
import struct
from typing import Any, Awaitable, Callable, List
from urllib.parse import urlparse

import pytest

from playwright.async_api import Error, Frame, Page
from tests.server import Server, TestServerRequest

from ..utils import Utils


def object_is(a: Any, b: Any) -> bool:
    """Port of Object.is(): NaN is NaN, and -0 is not 0."""
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return a == b and math.copysign(1.0, a) == math.copysign(1.0, b)
    return type(a) is type(b) and a == b


def assert_numbers_equal(result: Any, expected: Any) -> None:
    """Port of toEqual() on an object of numbers: compares them with Object.is()."""
    assert isinstance(result, dict)
    assert result.keys() == expected.keys()
    for key in expected:
        assert object_is(result[key], expected[key]), key


def float32(*values: float) -> List[float]:
    """The values that a Float32Array holds for the given numbers."""
    return list(
        struct.unpack(f"<{len(values)}f", struct.pack(f"<{len(values)}f", *values))
    )


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


async def test_EV_001_should_work_smoke(page: Page) -> None:
    result = await page.evaluate("() => 7 * 3")
    assert result == 21


async def test_EV_002_should_transfer_na_n(page: Page) -> None:
    result = await page.evaluate("a => a", float("nan"))
    assert object_is(result, float("nan")) is True


async def test_EV_003_should_transfer_0(page: Page) -> None:
    result = await page.evaluate("a => a", -0.0)
    assert object_is(result, -0.0) is True


async def test_EV_004_should_transfer_infinity(page: Page) -> None:
    result = await page.evaluate("a => a", float("inf"))
    assert object_is(result, float("inf")) is True


async def test_EV_005_should_transfer_infinity(page: Page) -> None:
    result = await page.evaluate("a => a", float("-inf"))
    assert object_is(result, float("-inf")) is True


async def test_EV_006_should_roundtrip_unserializable_values(page: Page) -> None:
    value = {
        "infinity": float("inf"),
        "nInfinity": float("-inf"),
        "nZero": -0.0,
        "nan": float("nan"),
    }
    result = await page.evaluate("value => value", value)
    assert_numbers_equal(result, value)


async def test_EV_007_should_roundtrip_promise_to_value(page: Page) -> None:
    result = await page.evaluate("value => Promise.resolve(value)", None)
    assert result is None
    result = await page.evaluate("value => Promise.resolve(value)", float("inf"))
    assert result == float("inf")
    result = await page.evaluate("value => Promise.resolve(value)", -0.0)
    assert result == -0.0
    # Python has no undefined: an absent argument is the closest.
    result = await page.evaluate("value => Promise.resolve(value)")
    assert result is None


async def test_EV_008_should_roundtrip_promise_to_unserializable_values(
    page: Page,
) -> None:
    value = {
        "infinity": float("inf"),
        "nInfinity": float("-inf"),
        "nZero": -0.0,
        "nan": float("nan"),
    }
    result = await page.evaluate("value => Promise.resolve(value)", value)
    assert_numbers_equal(result, value)


async def test_EV_009_should_transfer_arrays(page: Page) -> None:
    result = await page.evaluate("a => a", [1, 2, 3])
    assert result == [1, 2, 3]


async def test_EV_010_should_transfer_arrays_as_arrays_not_objects(
    page: Page,
) -> None:
    result = await page.evaluate("a => Array.isArray(a)", [1, 2, 3])
    assert result is True


async def test_EV_011_should_transfer_typed_arrays(page: Page) -> None:
    # Python has no typed arrays to pass as an argument: the page makes them,
    # and they come back as lists.
    test_cases = [
        ("new Int8Array([1, 2, 3])", [1, 2, 3]),
        ("new Uint8Array([1, 2, 3])", [1, 2, 3]),
        ("new Uint8ClampedArray([1, 2, 3])", [1, 2, 3]),
        ("new Int16Array([1, 2, 3])", [1, 2, 3]),
        ("new Uint16Array([1, 2, 3])", [1, 2, 3]),
        ("new Int32Array([1, 2, 3])", [1, 2, 3]),
        ("new Uint32Array([1, 2, 3])", [1, 2, 3]),
        ("new Float32Array([1.1, 2.2, 3.3])", float32(1.1, 2.2, 3.3)),
        ("new Float64Array([1.1, 2.2, 3.3])", [1.1, 2.2, 3.3]),
        ("new BigInt64Array([1n, 2n, 3n])", [1, 2, 3]),
        ("new BigUint64Array([1n, 2n, 3n])", [1, 2, 3]),
    ]
    for typed_array, expected in test_cases:
        result = await page.evaluate(f"() => {typed_array}")
        assert result == expected, typed_array


async def test_EV_012_should_transfer_bigint(page: Page) -> None:
    assert await page.evaluate("() => 42n") == 42
    assert await page.evaluate("a => a", 17) == 17


async def test_EV_013_should_transfer_maps_as_empty_objects(page: Page) -> None:
    # Python has no Map to pass as an argument.
    assert await page.evaluate("() => new Map([[1, 2]])") == {}


async def test_EV_014_should_transfer_sets_as_empty_objects(page: Page) -> None:
    # A Python set is not a JavaScript Set: it can not be passed as an argument.
    assert await page.evaluate("() => new Set([1, 2])") == {}


async def test_EV_015_should_modify_global_environment(page: Page) -> None:
    await page.evaluate("() => window['globalVar'] = 123")
    assert await page.evaluate("globalVar") == 123


async def test_EV_016_should_evaluate_in_the_page_context(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/global-var.html")
    assert await page.evaluate("globalVar") == 123


async def test_EV_017_should_return_undefined_for_objects_with_symbols(
    page: Page,
) -> None:
    assert await page.evaluate("() => [Symbol('foo4')]") == [None]
    assert (
        await page.evaluate(
            """() => {
                const a = {};
                a[Symbol('foo4')] = 42;
                return a;
            }"""
        )
        == {}
    )
    assert (
        await page.evaluate(
            """() => {
            return { foo: [{ a: Symbol('foo4') }] };
        }"""
        )
        == {"foo": [{"a": None}]}
    )


async def test_EV_019_should_work_with_unicode_chars(page: Page) -> None:
    result = await page.evaluate("a => a['中文字符']", {"中文字符": 42})
    assert result == 42


async def test_EV_020_should_work_with_large_strings(page: Page) -> None:
    expected = "x" * 40000
    assert await page.evaluate("data => data", expected) == expected


async def test_EV_021_should_work_with_large_unicode_strings(page: Page) -> None:
    expected = "🎭" * 10000
    assert await page.evaluate("data => data", expected) == expected


async def test_EV_022_should_throw_when_evaluation_triggers_reload(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """() => {
                location.reload();
                return new Promise(() => { });
            }"""
        )
    assert "navigation" in exc_info.value.message


async def test_EV_023_should_await_promise(page: Page) -> None:
    result = await page.evaluate("() => Promise.resolve(8 * 7)")
    assert result == 56


async def test_EV_024_should_work_right_after_framenavigated(
    page: Page, server: Server
) -> None:
    frame_evaluation: List["asyncio.Task[Any]"] = []

    def on_framenavigated(frame: Frame) -> None:
        frame_evaluation.append(asyncio.create_task(frame.evaluate("() => 6 * 7")))

    page.on("framenavigated", on_framenavigated)
    await page.goto(server.EMPTY_PAGE)
    assert await frame_evaluation[-1] == 42


async def test_EV_025_should_work_right_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame_evaluation: List["asyncio.Task[Any]"] = []

    def on_framenavigated(frame: Frame) -> None:
        frame_evaluation.append(asyncio.create_task(frame.evaluate("() => 6 * 7")))

    page.on("framenavigated", on_framenavigated)
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert await frame_evaluation[-1] == 42


async def test_EV_026_should_work_from_inside_an_exposed_function(
    page: Page,
) -> None:
    # Setup inpage callback, which calls Page.evaluate
    async def call_controller(a: int, b: int) -> Any:
        return await page.evaluate("({ a, b }) => a * b", {"a": a, "b": b})

    await page.expose_function("callController", call_controller)
    result = await page.evaluate(
        """async function() {
            return await window['callController'](9, 3);
        }"""
    )
    assert result == 27


async def test_EV_027_should_reject_promise_with_exception(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate("() => not_existing_object.property")
    assert exc_info.value
    assert "not_existing_object" in exc_info.value.message


async def test_EV_028_should_support_thrown_strings_as_error_messages(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate("() => { throw 'qwerty'; }")
    assert exc_info.value
    assert "qwerty" in exc_info.value.message


async def test_EV_029_should_support_thrown_numbers_as_error_messages(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate("() => { throw 100500; }")
    assert exc_info.value
    assert "100500" in exc_info.value.message


async def test_EV_030_should_reject_when_a_falsy_value_is_thrown(page: Page) -> None:
    for value in ["null", "undefined", "0", "''", "false", "NaN", "-0", "0n"]:
        with pytest.raises(Error):
            await page.evaluate(f"(() => {{ throw {value}; }})()")
        with pytest.raises(Error):
            await page.evaluate(f"Promise.reject({value})")


async def test_EV_031_should_include_a_non_error_rejection_value_in_the_error_message(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate("() => Promise.reject(7)")
    assert "7" in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        await page.evaluate("() => { throw null; }")
    assert "null" in exc_info.value.message


async def test_EV_032_should_return_complex_objects(page: Page) -> None:
    object = {"foo": "bar!"}
    result = await page.evaluate("a => a", object)
    assert result is not object
    assert result == object


async def test_EV_033_should_return_na_n(page: Page) -> None:
    result = await page.evaluate("() => NaN")
    assert object_is(result, float("nan")) is True


async def test_EV_034_should_return_0(page: Page) -> None:
    result = await page.evaluate("() => -0")
    assert object_is(result, -0.0) is True


async def test_EV_035_should_return_infinity(page: Page) -> None:
    result = await page.evaluate("() => Infinity")
    assert object_is(result, float("inf")) is True


async def test_EV_036_should_return_infinity(page: Page) -> None:
    result = await page.evaluate("() => -Infinity")
    assert object_is(result, float("-inf")) is True


async def test_EV_037_should_work_with_overwritten_promise(page: Page) -> None:
    await page.evaluate(
        """() => {
            const originalPromise = window.Promise;
            class Promise2 {
              static all(arg) {
                return wrap(originalPromise.all(arg));
              }
              static race(arg) {
                return wrap(originalPromise.race(arg));
              }
              static resolve(arg) {
                return wrap(originalPromise.resolve(arg));
              }
              constructor(f) {
                this._promise = new originalPromise(f);
              }
              then(f, r) {
                return wrap(this._promise.then(f, r));
              }
              catch(f) {
                return wrap(this._promise.catch(f));
              }
              finally(f) {
                return wrap(this._promise.finally(f));
              }
            }
            const wrap = p => {
              const result = new Promise2(() => { });
              result._promise = p;
              return result;
            };
            window.Promise = Promise2;
            window['__Promise2'] = Promise2;
        }"""
    )

    # Sanity check.
    assert (
        await page.evaluate(
            """() => {
                const p = Promise.all([Promise.race([]), new Promise(() => { }).then(() => { })]);
                return p instanceof window['__Promise2'];
            }"""
        )
        is True
    )

    # Now, the new promise should be awaitable.
    assert await page.evaluate("() => Promise.resolve(42)") == 42
    # No page timers below: the frozen-clock project never fires them.
    handle = await page.evaluate_handle(
        "() => new Promise(f => queueMicrotask(() => f(42)))"
    )
    assert await handle.json_value() == 42
    with pytest.raises(Error) as exc_info:
        await page.wait_for_function("() => false", timeout=500)
    assert "Timeout 500ms exceeded" in exc_info.value.message
    await page.evaluate("() => window.__done = true")
    await page.wait_for_function("() => window.__done")


async def test_EV_038_should_throw_when_passed_more_than_one_parameter(
    page: Page,
) -> None:
    # Python checks the number of arguments when the method is called.
    async def expect_throw(f: Callable[..., Awaitable[Any]], *args: Any) -> None:
        with pytest.raises(TypeError) as exc_info:
            await f(*args)
        assert "positional arguments" in str(exc_info.value)

    await expect_throw(page.evaluate, "(a, b) => false", 1, 2)
    await expect_throw(page.evaluate_handle, "(a, b) => false", 1, 2)
    await expect_throw(page.eval_on_selector, "sel", "(a, b) => false", 1, 2)
    await expect_throw(page.eval_on_selector_all, "sel", "(a, b) => false", 1, 2)
    await expect_throw(page.evaluate, "(a, b) => false", 1, 2)
    frame = page.main_frame
    await expect_throw(frame.evaluate, "(a, b) => false", 1, 2)
    await expect_throw(frame.evaluate_handle, "(a, b) => false", 1, 2)
    await expect_throw(frame.eval_on_selector, "sel", "(a, b) => false", 1, 2)
    await expect_throw(frame.eval_on_selector_all, "sel", "(a, b) => false", 1, 2)
    await expect_throw(frame.evaluate, "(a, b) => false", 1, 2)


async def test_EV_039_should_accept_undefined_as_one_of_multiple_parameters(
    page: Page,
) -> None:
    # Python has no undefined: None is serialized as null.
    result = await page.evaluate(
        "({ a, b }) => Object.is(a, null) && Object.is(b, 'foo')",
        {"a": None, "b": "foo"},
    )
    assert result is True


async def test_EV_040_should_properly_serialize_undefined_arguments(
    page: Page,
) -> None:
    assert await page.evaluate("x => ({ a: x })") == {"a": None}


async def test_EV_041_should_properly_serialize_undefined_fields(page: Page) -> None:
    assert await page.evaluate("() => ({ a: undefined })") == {"a": None}


async def test_EV_042_should_return_undefined_properties(page: Page) -> None:
    value = await page.evaluate("() => ({ a: undefined })")
    assert ("a" in value) is True


async def test_EV_043_should_properly_serialize_null_arguments(page: Page) -> None:
    assert await page.evaluate("x => x", None) is None


async def test_EV_044_should_properly_serialize_null_fields(page: Page) -> None:
    assert await page.evaluate("() => ({ a: null })") == {"a": None}


async def test_EV_045_should_properly_serialize_performance_measure_object(
    page: Page,
) -> None:
    result = await page.evaluate(
        """() => {
            window.builtins.performance.mark('start');
            window.builtins.performance.mark('end');
            window.builtins.performance.measure('my-measure', 'start', 'end');
            return window.builtins.performance.getEntriesByType('measure');
        }"""
    )
    assert len(result) == 1
    assert is_number(result[0]["duration"])
    assert result[0]["entryType"] == "measure"
    assert result[0]["name"] == "my-measure"
    assert is_number(result[0]["startTime"])


async def test_EV_046_should_properly_serialize_window_performance_object(
    page: Page,
) -> None:
    result = await page.evaluate("() => performance")
    assert result["navigation"].keys() == {"redirectCount", "type"}
    assert result["navigation"]["redirectCount"] == 0
    assert is_number(result["navigation"]["type"])
    assert is_number(result["timeOrigin"])
    assert result["timing"].keys() == {
        "connectEnd",
        "connectStart",
        "domComplete",
        "domContentLoadedEventEnd",
        "domContentLoadedEventStart",
        "domInteractive",
        "domLoading",
        "domainLookupEnd",
        "domainLookupStart",
        "fetchStart",
        "loadEventEnd",
        "loadEventStart",
        "navigationStart",
        "redirectEnd",
        "redirectStart",
        "requestStart",
        "responseEnd",
        "responseStart",
        "secureConnectionStart",
        "unloadEventEnd",
        "unloadEventStart",
    }
    for key, value in result["timing"].items():
        assert is_number(value), key


async def test_EV_047_should_return_undefined_for_non_serializable_objects(
    page: Page,
) -> None:
    assert await page.evaluate("() => function() {}") is None


async def test_EV_048_should_throw_for_too_deep_reference_chain(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "fixme: Firefox Juggler -> Playwright serialiser does not throw for deep references."
        )
    with pytest.raises(
        Error, match="Cannot serialize result: object reference chain is too long."
    ):
        await page.evaluate(
            """depth => {
                const obj = {};
                let temp = obj;
                for (let i = 0; i < depth; i++) {
                  temp[i] = {};
                  temp = temp[i];
                }
                return obj;
            }""",
            1000,
        )


@pytest.mark.only_browser("chromium")
async def test_EV_049_should_throw_for_too_deep_reference_chain_2(
    page: Page,
) -> None:
    with pytest.raises(
        Error, match="Cannot serialize result: object reference chain is too long."
    ):
        await page.evaluate(
            """depth => {
                let node = {};
                for (let i = 0; i < depth; i++)
                  node = { child: node };
                return node;
            }""",
            200,
        )


async def test_EV_050_should_throw_usable_message_for_unserializable_shallow_function(
    page: Page,
) -> None:
    with pytest.raises(Error, match=r"Attempting to serialize unexpected value: "):
        await page.evaluate("arg => arg", lambda: None)


async def test_EV_051_should_throw_usable_message_for_unserializable_object_one_deep_function(
    page: Page,
) -> None:
    with pytest.raises(
        Error,
        match=r'Attempting to serialize unexpected value at position "aProperty": ',
    ):
        await page.evaluate("arg => arg", {"aProperty": lambda: None})


async def test_EV_052_should_throw_usable_message_for_unserializable_object_nested_function(
    page: Page,
) -> None:
    with pytest.raises(
        Error,
        match=r'Attempting to serialize unexpected value at position "a\.inner\.property": ',
    ):
        await page.evaluate("arg => arg", {"a": {"inner": {"property": lambda: None}}})


async def test_EV_053_should_throw_usable_message_for_unserializable_array_nested_function(
    page: Page,
) -> None:
    with pytest.raises(
        Error,
        match=r'Attempting to serialize unexpected value at position "a\.inner\[1\]\.property": ',
    ):
        await page.evaluate(
            "arg => arg",
            {"a": {"inner": ["firstValue", {"property": lambda: None}]}},
        )


async def test_EV_054_should_alias_window_document_and_node(page: Page) -> None:
    object = await page.evaluate("[window, document, document.body]")
    assert object == ["ref: <Window>", "ref: <Document>", "ref: <Node>"]


async def test_EV_055_should_work_for_circular_object(page: Page) -> None:
    result = await page.evaluate(
        """() => {
            const a = {};
            a.b = a;
            return a;
        }"""
    )
    assert list(result.keys()) == ["b"]
    assert result["b"] is result


async def test_EV_056_should_be_able_to_throw_a_tricky_error(page: Page) -> None:
    window_handle = await page.evaluate_handle("() => window")
    try:
        error_text = await window_handle.json_value()
    except Error as e:
        error_text = e.message
    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """errorText => {
                throw new Error(errorText);
            }""",
            error_text,
        )
    assert error_text in exc_info.value.message


async def test_EV_057_should_accept_a_string(page: Page) -> None:
    result = await page.evaluate("1 + 2")
    assert result == 3


async def test_EV_058_should_accept_a_string_with_semi_colons(page: Page) -> None:
    result = await page.evaluate("1 + 5;")
    assert result == 6


async def test_EV_059_should_accept_a_string_with_comments(page: Page) -> None:
    result = await page.evaluate("2 + 5;\n// do some math!")
    assert result == 7


async def test_EV_060_should_accept_element_handle_as_an_argument(
    page: Page,
) -> None:
    await page.set_content("<section>42</section>")
    element = await page.query_selector("section")
    text = await page.evaluate("e => e.textContent", element)
    assert text == "42"


async def test_EV_061_should_throw_if_underlying_element_was_disposed(
    page: Page,
) -> None:
    await page.set_content("<section>39</section>")
    element = await page.query_selector("section")
    assert element
    await element.dispose()
    with pytest.raises(Error) as exc_info:
        await page.evaluate("e => e.textContent", element)
    assert "no object with guid" in exc_info.value.message


async def test_EV_062_should_simulate_a_user_gesture(page: Page) -> None:
    result = await page.evaluate(
        """() => {
            document.body.appendChild(document.createTextNode('test'));
            document.execCommand('selectAll');
            return document.execCommand('copy');
        }"""
    )
    assert result is True


async def test_EV_063_should_throw_a_nice_error_after_a_navigation(
    page: Page,
) -> None:
    async def wait_for_error() -> Error:
        with pytest.raises(Error) as exc_info:
            await page.evaluate("() => new Promise(f => window['__resolve'] = f)")
        return exc_info.value

    async def reload() -> None:
        async with page.expect_navigation():
            await page.evaluate(
                """() => {
                    window.location.reload();
                    setTimeout(() => window['__resolve'](42), 1000);
                }"""
            )

    error, _ = await asyncio.gather(wait_for_error(), reload())
    assert "navigation" in error.message


async def test_EV_064_should_not_throw_an_error_when_evaluation_does_a_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/one-style.html")
    result = await page.evaluate(
        """() => {
            window.location.href = '/empty.html';
            return [42];
        }"""
    )
    assert result == [42]


async def test_EV_065_should_not_throw_an_error_when_evaluation_does_a_synchronous_navigation_and_returns_an_object(
    page: Page,
) -> None:
    # It is important to be on about:blank for sync reload.
    result = await page.evaluate(
        """() => {
            window.location.reload();
            return { a: 42 };
        }"""
    )
    assert result == {"a": 42}


async def test_EV_066_should_not_throw_an_error_when_evaluation_does_a_synchronous_navigation_and_returns_undefined(
    page: Page,
) -> None:
    # It is important to be on about:blank for sync reload.
    result = await page.evaluate(
        """() => {
            window.location.reload();
            return undefined;
        }"""
    )
    assert result is None


async def test_EV_067_should_transfer_100_mb_of_data_from_page_to_node_js(
    page: Page,
) -> None:
    a = await page.evaluate("() => Array(100 * 1024 * 1024 + 1).join('a')")
    assert len(a) == 100 * 1024 * 1024


async def test_EV_068_should_throw_error_with_detailed_information_on_exception_inside_promise(
    page: Page,
) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """() => new Promise(() => {
                throw new Error('Error in promise');
            })"""
        )
    assert "Error in promise" in exc_info.value.message


async def test_EV_069_should_work_even_when_json_is_set_to_null(page: Page) -> None:
    await page.evaluate("() => { window.JSON.stringify = null; window.JSON = null; }")
    result = await page.evaluate("() => ({ abc: 123 })")
    assert result == {"abc": 123}


async def test_EV_070_should_await_promise_from_popup(
    page: Page, server: Server
) -> None:
    # Something is wrong about the way Firefox waits for the chained promise
    await page.goto(server.EMPTY_PAGE)
    result = await page.evaluate(
        """() => {
            const win = window.open('about:blank');
            return new win['Promise'](f => f(42));
        }"""
    )
    assert result == 42


async def test_EV_071_should_work_with_new_function_and_csp(
    page: Page, server: Server
) -> None:
    server.set_csp("/empty.html", "script-src " + server.PREFIX)
    await page.goto(server.PREFIX + "/empty.html")
    assert await page.evaluate("() => new Function('return true')()") is True


async def test_EV_072_should_work_with_non_strict_expressions(page: Page) -> None:
    assert (
        await page.evaluate(
            """() => {
                y = 3.14;
                return y;
            }"""
        )
        == 3.14
    )


async def test_EV_073_should_respect_use_strict_expression(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate(
            """() => {
                'use strict';
                variableY = 3.14;
                return variableY;
            }"""
        )
    assert "variableY" in exc_info.value.message


async def test_EV_074_should_not_leak_utility_script(page: Page) -> None:
    assert await page.evaluate("this === window") is True


async def test_EV_075_should_not_leak_handles(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.evaluate("handles.length")
    assert " handles" in exc_info.value.message


async def test_EV_076_should_work_with_csp(page: Page, server: Server) -> None:
    server.set_csp("/empty.html", "script-src 'self'")
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("() => 2 + 2") == 4


async def test_EV_077_should_evaluate_exception_with_a_function_on_the_stack(
    page: Page,
) -> None:
    error = await page.evaluate(
        """() => {
            return (function functionOnStack() {
              return new Error('error message');
            })();
        }"""
    )
    assert error.message == "error message"
    assert "functionOnStack" in error.stack


async def test_EV_078_should_evaluate_exception(page: Page) -> None:
    error = await page.evaluate(
        """() => {
            function innerFunction() {
              const e = new Error('error message');
              e.name = 'foobar';
              return e;
            }
            return innerFunction();
        }"""
    )
    assert isinstance(error, Error)
    assert error.message == "error message"
    assert error.name == "foobar"
    assert error.stack
    assert "innerFunction" in error.stack


async def test_EV_079_should_pass_exception_argument(page: Page) -> None:
    def inner_function() -> Exception:
        try:
            raise type("foobar", (Exception,), {})("error message")
        except Exception as e:
            return e

    received = await page.evaluate(
        """e => {
            return { message: e.message, name: e.name, stack: e.stack };
        }""",
        inner_function(),
    )
    assert received["message"] == "error message"
    assert received["name"] == "foobar"
    assert "inner_function" in received["stack"]


async def test_EV_080_should_evaluate_date(page: Page) -> None:
    result = await page.evaluate(
        "() => ({ date: new Date('2020-05-27T01:31:38.506Z') })"
    )
    assert result == {
        "date": datetime.datetime(
            2020, 5, 27, 1, 31, 38, 506000, tzinfo=datetime.timezone.utc
        )
    }


async def test_EV_081_should_roundtrip_date(page: Page) -> None:
    date = datetime.datetime(
        2020, 5, 27, 1, 31, 38, 506000, tzinfo=datetime.timezone.utc
    )
    result = await page.evaluate("date => date", date)
    assert result == date


async def test_EV_082_should_roundtrip_regex(page: Page) -> None:
    regex = re.compile("hello", re.IGNORECASE | re.MULTILINE)
    result = await page.evaluate("regex => regex", regex)
    assert result.pattern == regex.pattern
    assert result.flags == regex.flags


async def test_EV_083_should_json_value_date(page: Page) -> None:
    result_handle = await page.evaluate_handle(
        "() => ({ date: new Date('2020-05-27T01:31:38.506Z') })"
    )
    assert await result_handle.json_value() == {
        "date": datetime.datetime(
            2020, 5, 27, 1, 31, 38, 506000, tzinfo=datetime.timezone.utc
        )
    }


async def test_EV_084_should_evaluate_url(page: Page) -> None:
    result = await page.evaluate("() => ({ url: new URL('https://example.com') })")
    # new URL() normalizes the URL, so it ends with a slash.
    assert result == {"url": urlparse("https://example.com/")}


async def test_EV_085_should_roundtrip_url(page: Page) -> None:
    # new URL() normalizes the URL, so it ends with a slash.
    url = urlparse("https://example.com/")
    result = await page.evaluate("url => url", url)
    assert result == url


async def test_EV_086_should_json_value_url(page: Page) -> None:
    result_handle = await page.evaluate_handle(
        "() => ({ url: new URL('https://example.com') })"
    )
    assert await result_handle.json_value() == {"url": urlparse("https://example.com/")}


async def test_EV_087_should_not_use_to_json_when_evaluating(page: Page) -> None:
    result = await page.evaluate("() => ({ toJSON: () => 'string', data: 'data' })")
    assert result == {"data": "data", "toJSON": {}}


async def test_EV_088_should_not_use_array_prototype_to_json_when_evaluating(
    page: Page,
) -> None:
    result = await page.evaluate(
        """() => {
            Array.prototype.toJSON = () => 'busted';
            return [1, 2, 3];
        }"""
    )
    assert result == [1, 2, 3]


async def test_EV_089_should_not_add_a_to_json_property_to_newly_created_arrays_after_evaluation(
    page: Page,
) -> None:
    await page.evaluate("() => []")
    has_to_json_property = await page.evaluate("() => 'toJSON' in []")
    assert has_to_json_property is False


async def test_EV_090_should_not_use_to_json_in_json_value(page: Page) -> None:
    result_handle = await page.evaluate_handle(
        "() => ({ toJSON: () => 'string', data: 'data' })"
    )
    assert await result_handle.json_value() == {"data": "data", "toJSON": {}}


async def test_EV_091_should_ignore_buggy_to_json(page: Page) -> None:
    result = await page.evaluate(
        """() => {
            class Foo {
              toJSON() {
                throw new Error('Bad');
              }
            }
            class Bar {
              get toJSON() {
                throw new Error('Also bad');
              }
            }
            return { foo: new Foo(), bar: new Bar() };
        }"""
    )
    assert result == {"foo": {}, "bar": {}}


async def test_EV_092_should_not_expose_the_injected_script_export(
    page: Page,
) -> None:
    assert await page.evaluate('typeof pwExport === "undefined"') is True


async def test_EV_093_should_throw_when_frame_is_detached(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    frame = page.frames[1]

    async def evaluate_in_frame() -> Error:
        with pytest.raises(Error) as exc_info:
            await frame.evaluate("() => new Promise(() => {})")
        return exc_info.value

    async def detach() -> None:
        await utils.detach_frame(page, "frame1")

    error, _ = await asyncio.gather(evaluate_in_frame(), detach())
    assert error
    assert re.search(
        r"Frame.evaluate: (Frame was detached|Execution context was destroyed)",
        error.message,
    )


async def test_EV_094_should_work_with_overridden_object_define_property(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""<script>
    Object.create = null;
    Object.defineProperty = null;
    Object.getOwnPropertyDescriptor = null;
    Object.getOwnPropertyNames = null;
    Object.getPrototypeOf = null;
    Object.prototype.hasOwnProperty = null;
    </script>"""
        )
        request.finish()

    server.set_route("/test", handler)
    await page.goto(server.PREFIX + "/test")
    assert await page.evaluate("1+2") == 3


async def test_EV_095_should_work_with_busted_array_prototype_map_push(
    page: Page, server: Server
) -> None:
    def handler(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""<script>
      Array.prototype.map = null;
      Array.prototype.push = null;
    </script>"""
        )
        request.finish()

    server.set_route("/test", handler)
    await page.goto(server.PREFIX + "/test")
    assert await page.evaluate("1+2") == 3
    assert await (await page.evaluate_handle("1+2")).json_value() == 3


async def test_EV_096_should_work_with_overridden_global_this_window_document_node(
    page: Page, server: Server
) -> None:
    test_cases = [
        "() => globalThis.Window = {}",
        "() => globalThis.Document = {}",
        "() => globalThis.Node = {}",
        "() => globalThis.Window = null",
        "() => globalThis.Document = null",
        "() => globalThis.Node = null",
    ]
    for test_case in test_cases:
        await page.goto(server.EMPTY_PAGE)
        await page.evaluate(test_case)
        assert await page.evaluate("1+2") == 3, test_case
        assert await page.evaluate("() => ['foo']") == ["foo"], test_case


async def test_EV_097_should_work_with_overridden_url_date_reg_exp(
    page: Page, server: Server
) -> None:
    test_cases = [
        "() => globalThis.URL = 'foo'",
        "() => globalThis.RegExp = 'foo'",
        "() => globalThis.Date = 'foo'",
    ]
    for test_case in test_cases:
        await page.goto(server.EMPTY_PAGE)
        await page.evaluate(test_case)
        assert await page.evaluate("1+2") == 3, test_case
        assert await page.evaluate("() => ({ 'a': 2023 })") == {"a": 2023}, test_case


async def test_EV_098_should_work_with_array_from_map(page: Page) -> None:
    assert (
        await page.evaluate(
            """() => {
                const r = (str, amount) => Array.from(Array(amount)).map(() => str).join('');
                return r('([a-f0-9]{2})', 3);
            }"""
        )
        == "([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})"
    )


async def test_EV_099_should_work_with_a_using_declaration(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "webkit":
        pytest.skip("WebKit does not support using declarations")
    if browser_name == "chromium" and browser_major_version < 134:
        pytest.skip("Chromium supports using declarations since 134")
    disposed = await page.evaluate(
        """() => {
            let disposed = false;
            {
              using r = { [Symbol.dispose]: () => { disposed = true; } };
              void r;
            }
            return disposed;
        }"""
    )
    assert disposed is True


async def test_EV_100_should_ignore_dangerous_object_keys(page: Page) -> None:
    input = {"__proto__": {"polluted": True}, "safeKey": "safeValue"}
    result = await page.evaluate("arg => arg", input)
    assert result == {"safeKey": "safeValue"}
