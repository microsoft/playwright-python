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

import re
from datetime import datetime, timedelta, timezone

import pytest

from playwright.async_api import Error, Page


async def test_evaluate_transfer_positive_zero_stays_positive(page: Page) -> None:
    result = await page.evaluate("a => Object.is(a, -0)", 0.0)
    assert result is False


async def test_should_pass_exception_argument(page: Page) -> None:
    def _raise_and_get_exception(exception: Exception) -> Exception:
        try:
            raise exception
        except Exception as e:
            return e

    error_for_roundtrip = Error("error message")
    error_for_roundtrip._name = "foobar"
    error_for_roundtrip._stack = "test stack"
    error = await page.evaluate(
        """e => {
            return { message: e.message, name: e.name, stack: e.stack };
        }""",
        error_for_roundtrip,
    )
    assert error["message"] == "error message"
    assert error["name"] == "foobar"
    assert "test stack" in error["stack"]

    error = await page.evaluate(
        """e => {
            return { message: e.message, name: e.name, stack: e.stack };
        }""",
        _raise_and_get_exception(Exception("error message")),
    )
    assert error["message"] == "error message"
    assert error["name"] == "Exception"
    assert "error message" in error["stack"]


async def test_evaluate_roundtrip_date_without_tzinfo(page: Page) -> None:
    date = datetime.fromisoformat("2020-05-27T01:31:38.506")
    result = await page.evaluate("date => date", date)
    assert result.timestamp() == date.timestamp()


async def test_evaluate_roundtrip_date_with_tzinfo(page: Page) -> None:
    date = datetime.fromisoformat("2020-05-27T01:31:38.506")
    date = date.astimezone(timezone(timedelta(hours=4)))
    result = await page.evaluate("date => date", date)
    assert result == date


async def test_evaluate_pass_regex_as_regexp(page: Page) -> None:
    result = await page.evaluate(
        "r => [r instanceof RegExp, r.source, r.flags, r.test('A12')]",
        re.compile(r"a\d+", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    )
    assert result == [True, "a\\d+", "ims", True]


async def test_evaluate_return_regex(page: Page) -> None:
    result = await page.evaluate(
        "() => ({ list: [/foo/s], nested: { re: /a\\d+/gi } })"
    )
    assert result == {
        "list": [re.compile("foo", re.DOTALL)],
        "nested": {"re": re.compile(r"a\d+", re.IGNORECASE)},
    }


async def test_evaluate_jsonvalue_regex(page: Page) -> None:
    handle = await page.evaluate_handle("() => ({ someKey: /foo/i })")
    assert await handle.json_value() == {"someKey": re.compile("foo", re.IGNORECASE)}


async def test_evaluate_return_regex_unsupported_by_python(page: Page) -> None:
    result = await page.evaluate("() => ({ a: 1, re: /(?<year>\\d{4})/ })")
    assert result == {"a": 1, "re": {"r": {"p": "(?<year>\\d{4})", "f": ""}}}


async def test_evaluate_throw_for_unsupported_regex(page: Page) -> None:
    with pytest.raises(Error, match="Unexpected re.Pattern flag"):
        await page.evaluate("a => a", re.compile("foo", re.VERBOSE))
    with pytest.raises(Error, match="Only str patterns are supported"):
        await page.evaluate("a => a", re.compile(b"foo"))


async def test_evaluate_large_integers(page: Page) -> None:
    # Python ints within JS safe integer range (abs(n) <= 2**53 - 1) serialize as Number
    assert await page.evaluate("x => typeof x", 2**53 - 1) == "number"
    assert await page.evaluate("x => typeof x", -(2**53 - 1)) == "number"

    # Python ints outside safe range serialize as BigInt without precision loss
    assert await page.evaluate("x => typeof x", 2**53) == "bigint"
    assert await page.evaluate("x => typeof x", -(2**53)) == "bigint"
    assert await page.evaluate("x => typeof x", 2**64) == "bigint"
    assert await page.evaluate("x => x", 2**53 + 1) == 2**53 + 1
    assert await page.evaluate("x => x", -(2**53 + 1)) == -(2**53 + 1)
    assert await page.evaluate("x => x", 2**64) == 2**64
    assert await page.evaluate("x => x", -2**63) == -2**63
    assert await page.evaluate("x => x", 2**70) == 2**70
    assert await page.evaluate("x => x", [2**64, 1]) == [2**64, 1]
    assert await page.evaluate("x => x.id", {"id": 2**70}) == 2**70


def test_serializers_large_integers() -> None:
    from playwright._impl.protocol.serializers import (
        MAX_SAFE_INTEGER,
        parse_serialized_value,
        serialize_value,
    )

    def fall_through(v: object) -> dict:
        return {"fallThrough": v}

    # Safe integer range serializes as number
    assert serialize_value(0, fall_through) == {"n": 0}
    assert serialize_value(42, fall_through) == {"n": 42}
    assert serialize_value(MAX_SAFE_INTEGER, fall_through) == {"n": MAX_SAFE_INTEGER}
    assert serialize_value(-MAX_SAFE_INTEGER, fall_through) == {"n": -MAX_SAFE_INTEGER}

    # Outside safe integer range serializes as bigint {"bi": str}
    assert serialize_value(MAX_SAFE_INTEGER + 1, fall_through) == {
        "bi": str(MAX_SAFE_INTEGER + 1)
    }
    assert serialize_value(-(MAX_SAFE_INTEGER + 1), fall_through) == {
        "bi": str(-(MAX_SAFE_INTEGER + 1))
    }
    assert serialize_value(2**64, fall_through) == {"bi": "18446744073709551616"}
    assert serialize_value(-2**63, fall_through) == {"bi": "-9223372036854775808"}
    assert serialize_value(2**70, fall_through) == {"bi": "1180591620717411303424"}

    # Booleans are still serialized as boolean
    assert serialize_value(True, fall_through) == {"b": True}
    assert serialize_value(False, fall_through) == {"b": False}

    # Deserialization round-trip
    assert parse_serialized_value({"bi": "18446744073709551616"}, None) == 2**64
    assert parse_serialized_value({"bi": "-9223372036854775808"}, None) == -2**63
