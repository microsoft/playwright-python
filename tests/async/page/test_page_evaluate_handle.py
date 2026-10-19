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

"""Port of tests/page/page-evaluate-handle.spec.ts."""

import json

from playwright.async_api import Page


async def test_EV_101_should_work(page: Page) -> None:
    window_handle = await page.evaluate_handle("() => window")
    assert window_handle


async def test_EV_102_should_accept_object_handle_as_an_argument(page: Page) -> None:
    navigator_handle = await page.evaluate_handle("() => navigator")
    text = await page.evaluate("e => e.userAgent", navigator_handle)
    assert "Mozilla" in text


async def test_EV_103_should_accept_object_handle_to_primitive_types(
    page: Page,
) -> None:
    a_handle = await page.evaluate_handle("() => 5")
    is_five = await page.evaluate("e => Object.is(e, 5)", a_handle)
    assert is_five


async def test_EV_104_should_accept_nested_handle(page: Page) -> None:
    foo = await page.evaluate_handle("() => ({ x: 1, y: 'foo' })")
    result = await page.evaluate(
        """({ foo }) => {
            return foo;
        }""",
        {"foo": foo},
    )
    assert result == {"x": 1, "y": "foo"}


async def test_EV_105_should_accept_nested_window_handle(page: Page) -> None:
    foo = await page.evaluate_handle("() => window")
    result = await page.evaluate(
        """({ foo }) => {
            return foo === window;
        }""",
        {"foo": foo},
    )
    assert result is True


async def test_EV_106_should_accept_multiple_nested_handles(page: Page) -> None:
    foo = await page.evaluate_handle("() => ({ x: 1, y: 'foo' })")
    bar = await page.evaluate_handle("() => 5")
    baz = await page.evaluate_handle("() => (['baz'])")
    result = await page.evaluate(
        """x => {
            return JSON.stringify(x);
        }""",
        {"a1": {"foo": foo}, "a2": {"bar": bar, "arr": [{"baz": baz}]}},
    )
    assert json.loads(result) == {
        "a1": {"foo": {"x": 1, "y": "foo"}},
        "a2": {"bar": 5, "arr": [{"baz": ["baz"]}]},
    }


async def test_EV_107_should_accept_same_handle_multiple_times(page: Page) -> None:
    foo = await page.evaluate_handle("() => 1")
    assert await page.evaluate(
        "x => x", {"foo": foo, "bar": [foo], "baz": {"foo": foo}}
    ) == {"foo": 1, "bar": [1], "baz": {"foo": 1}}


async def test_EV_108_should_accept_same_nested_object_multiple_times(
    page: Page,
) -> None:
    foo = {"x": 1}
    assert await page.evaluate(
        "x => x", {"foo": foo, "bar": [foo], "baz": {"foo": foo}}
    ) == {"foo": {"x": 1}, "bar": [{"x": 1}], "baz": {"foo": {"x": 1}}}


async def test_EV_109_should_accept_object_handle_to_unserializable_value(
    page: Page,
) -> None:
    a_handle = await page.evaluate_handle("() => Infinity")
    assert await page.evaluate("e => Object.is(e, Infinity)", a_handle) is True


async def test_EV_110_should_pass_configurable_args(page: Page) -> None:
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


async def test_EV_111_should_work_with_primitives(page: Page) -> None:
    a_handle = await page.evaluate_handle(
        """() => {
            window['FOO'] = 123;
            return window;
        }"""
    )
    assert await page.evaluate("e => e['FOO']", a_handle) == 123
