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

"""Port of tests/page/jshandle-properties.spec.ts."""

import math

from playwright.async_api import ElementHandle, Page


async def test_JH_010_should_work_smoke(page: Page) -> None:
    a_handle = await page.evaluate_handle(
        """() => ({
        one: 1,
        two: 2,
        three: 3
      })"""
    )
    two_handle = await a_handle.get_property("two")
    assert await two_handle.json_value() == 2


async def test_JH_011_should_work_with_undefined_null_and_empty(page: Page) -> None:
    a_handle = await page.evaluate_handle(
        """() => ({
        undefined: undefined,
        null: null,
      })"""
    )
    undefined_handle = await a_handle.get_property("undefined")
    assert await undefined_handle.json_value() is None
    null_handle = await a_handle.get_property("null")
    assert await null_handle.json_value() is None
    emptyhandle = await a_handle.get_property("empty")
    assert await emptyhandle.json_value() is None


async def test_JH_012_should_work_with_unserializable_values(page: Page) -> None:
    a_handle = await page.evaluate_handle(
        """() => ({
        infinity: Infinity,
        nInfinity: -Infinity,
        nan: NaN,
        nzero: -0
      })"""
    )
    infinity_handle = await a_handle.get_property("infinity")
    assert await infinity_handle.json_value() == float("inf")
    n_infinity_handle = await a_handle.get_property("nInfinity")
    assert await n_infinity_handle.json_value() == float("-inf")
    nan_handle = await a_handle.get_property("nan")
    assert math.isnan(await nan_handle.json_value())
    nzero_handle = await a_handle.get_property("nzero")
    nzero = await nzero_handle.json_value()
    assert nzero == 0
    assert math.copysign(1, nzero) == -1


async def test_JH_013_get_properties_should_work(page: Page) -> None:
    a_handle = await page.evaluate_handle(
        """() => ({
        foo: 'bar'
      })"""
    )
    properties = await a_handle.get_properties()
    foo = properties.get("foo")
    assert foo
    assert await foo.json_value() == "bar"


async def test_JH_014_get_properties_should_return_empty_map_for_non_objects(
    page: Page,
) -> None:
    a_handle = await page.evaluate_handle("() => 123")
    properties = await a_handle.get_properties()
    assert len(properties) == 0


async def test_JH_015_get_properties_should_return_properties_inhertied_from_super_class(
    page: Page,
) -> None:
    a_handle = await page.evaluate_handle(
        """() => {
        class A {
          constructor() {
            this.a = '1';
          }
        }
        class B extends A {
          constructor() {
            super();
            this.b = '2';
          }
        }
        return new B();
      }"""
    )
    properties = await a_handle.get_properties()
    assert await properties["a"].json_value() == "1"
    assert await properties["b"].json_value() == "2"


async def test_JH_016_get_properties_should_return_own_enumerable_properties_only(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42651
    a_handle = await page.evaluate_handle(
        """() => {
        class A {
          constructor() {
            this.own = 1;
            Object.defineProperty(this, 'ownHidden', { value: 2, enumerable: false });
          }
        }
        A.prototype.inherited = 3;
        return new A();
      }"""
    )
    assert list((await a_handle.get_properties()).keys()) == ["own"]

    await page.set_content("<div id=d><span>a</span><span>b</span></div>")
    collection = await page.evaluate_handle(
        "() => document.querySelector('#d').children"
    )
    assert list((await collection.get_properties()).keys()) == ["0", "1"]


async def test_JH_017_get_properties_should_work_with_elements(page: Page) -> None:
    await page.set_content("<div>Hello</div>")
    handle = await page.evaluate_handle("() => ({ body: document.body })")
    properties = await handle.get_properties()
    body = properties.get("body")
    assert isinstance(body, ElementHandle)
    assert await body.text_content() == "Hello"
