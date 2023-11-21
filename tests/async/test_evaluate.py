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

import math
from datetime import datetime
from urllib.parse import ParseResult, urlparse

from playwright.async_api import Error, Page


async def test_evaluate_work(page):
    result = await page.evaluate("7 * 3")
    assert result == 21


async def test_evaluate_return_none_for_null(page):
    result = await page.evaluate("a => a", None)
    assert result is None


async def test_evaluate_transfer_nan(page):
    result = await page.evaluate("a => a", float("nan"))
    assert math.isnan(result)


async def test_evaluate_transfer_neg_zero(page):
    result = await page.evaluate("a => a", -0)
    assert result == float("-0")


async def test_evaluate_transfer_infinity(page):
    result = await page.evaluate("a => a", float("Infinity"))
    assert result == float("Infinity")


async def test_evaluate_transfer_neg_infinity(page):
    result = await page.evaluate("a => a", float("-Infinity"))
    assert result == float("-Infinity")


async def test_evaluate_roundtrip_unserializable_values(page):
    value = {
        "infinity": float("Infinity"),
        "nInfinity": float("-Infinity"),
        "nZero": float("-0"),
    }
    result = await page.evaluate("a => a", value)
    assert result == value


async def test_evaluate_transfer_arrays(page):
    result = await page.evaluate("a => a", [1, 2, 3])
    assert result == [1, 2, 3]


async def test_evaluate_transfer_bigint(page: Page) -> None:
    assert await page.evaluate("() => 42n") == 42
    assert await page.evaluate("a => a", 17) == 17


async def test_evaluate_return_undefined_for_objects_with_symbols(page):
    assert await page.evaluate('[Symbol("foo4")]') == [None]
    assert (
        await page.evaluate(
            """() => {
                const a = { };
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


async def test_evaluate_work_with_unicode_chars(page):
    result = await page.evaluate('a => a["中文字符"]', {"中文字符": 42})
    assert result == 42


async def test_evaluate_throw_when_evaluation_triggers_reload(page):
    error = None
    try:
        await page.evaluate(
            "() => { location.reload(); return new Promise(() => {}); }"
        )
    except Error as e:
        error = e
    assert "navigation" in error.message


async def test_evaluate_work_with_exposed_function(page):
    await page.expose_function("callController", lambda a, b: a * b)
    result = await page.evaluate("callController(9, 3)")
    assert result == 27


async def test_evaluate_reject_promise_with_exception(page):
    error = None
    try:
        await page.evaluate("not_existing_object.property")
    except Error as e:
        error = e
    assert "not_existing_object" in error.message


async def test_evaluate_support_thrown_strings(page):
    error = None
    try:
        await page.evaluate('throw "qwerty"')
    except Error as e:
        error = e
    assert "qwerty" in error.message


async def test_evaluate_support_thrown_numbers(page):
    error = None
    try:
        await page.evaluate("throw 100500")
    except Error as e:
        error = e
    assert "100500" in error.message


async def test_evaluate_return_complex_objects(page):
    obj = {"foo": "bar!"}
    result = await page.evaluate("a => a", obj)
    assert result == obj


async def test_evaluate_accept_none_as_one_of_multiple_parameters(page):
    result = await page.evaluate(
        '({ a, b }) => Object.is(a, null) && Object.is(b, "foo")',
        {"a": None, "b": "foo"},
    )
    assert result


async def test_evaluate_properly_serialize_none_arguments(page):
    assert await page.evaluate("x => ({a: x})", None) == {"a": None}


async def test_should_alias_window_document_and_node(page):
    object = await page.evaluate("[window, document, document.body]")
    assert object == ["ref: <Window>", "ref: <Document>", "ref: <Node>"]


async def test_evaluate_should_work_for_circular_object(page):
    a = await page.evaluate(
        """() => {
                const a = {x: 47};
                const b = {a};
                a.b = b;
                return a;
            }"""
    )

    assert a["b"]["a"]["b"]["a"]["x"] == 47
    assert a["b"]["a"] == a


async def test_evaluate_accept_string(page):
    assert await page.evaluate("1 + 2") == 3


async def test_evaluate_accept_element_handle_as_an_argument(page):
    await page.set_content("<section>42</section>")
    element = await page.query_selector("section")
    text = await page.evaluate("e => e.textContent", element)
    assert text == "42"


async def test_evaluate_throw_if_underlying_element_was_disposed(page):
    await page.set_content("<section>39</section>")
    element = await page.query_selector("section")
    await element.dispose()
    error = None
    try:
        await page.evaluate("e => e.textContent", element)
    except Error as e:
        error = e
    assert "no object with guid" in error.message


async def test_evaluate_evaluate_exception(page):
    error = await page.evaluate('new Error("error message")')
    assert "Error: error message" in error


async def test_evaluate_evaluate_date(page):
    result = await page.evaluate(
        '() => ({ date: new Date("2020-05-27T01:31:38.506Z") })'
    )
    assert result == {"date": datetime.fromisoformat("2020-05-27T01:31:38.506")}


async def test_evaluate_roundtrip_date(page):
    date = datetime.fromisoformat("2020-05-27T01:31:38.506")
    result = await page.evaluate("date => date", date)
    assert result == date


async def test_evaluate_jsonvalue_date(page):
    date = datetime.fromisoformat("2020-05-27T01:31:38.506")
    result = await page.evaluate(
        '() => ({ date: new Date("2020-05-27T01:31:38.506Z") })'
    )
    assert result == {"date": date}


async def test_should_evaluate_url(page):
    out = await page.evaluate(
        "() => ({ someKey: new URL('https://user:pass@example.com/?foo=bar#hi') })"
    )
    assert out["someKey"] == ParseResult(
        scheme="https",
        netloc="user:pass@example.com",
        path="/",
        query="foo=bar",
        params="",
        fragment="hi",
    )


async def test_should_roundtrip_url(page):
    in_ = urlparse("https://user:pass@example.com/?foo=bar#hi")
    out = await page.evaluate("url => url", in_)
    assert in_ == out


async def test_should_roundtrip_complex_url(page):
    in_ = urlparse(
        "https://user:password@www.contoso.com:80/Home/Index.htm?q1=v1&q2=v2#FragmentName"
    )
    out = await page.evaluate("url => url", in_)
    assert in_ == out


async def test_evaluate_jsonvalue_url(page):
    url = urlparse("https://example.com/")
    result = await page.evaluate('() => ({ someKey: new URL("https://example.com/") })')
    assert result == {"someKey": url}
