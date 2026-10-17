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

from playwright.sync_api import ElementHandle, Page


def test_JH_010_should_work_smoke(page: Page) -> None:
    a_handle = page.evaluate_handle(
        """() => ({
        one: 1,
        two: 2,
        three: 3
      })"""
    )
    two_handle = a_handle.get_property("two")
    assert two_handle.json_value() == 2


def test_JH_011_should_work_with_undefined_null_and_empty(page: Page) -> None:
    a_handle = page.evaluate_handle(
        """() => ({
        undefined: undefined,
        null: null,
      })"""
    )
    undefined_handle = a_handle.get_property("undefined")
    assert undefined_handle.json_value() is None
    null_handle = a_handle.get_property("null")
    assert null_handle.json_value() is None
    emptyhandle = a_handle.get_property("empty")
    assert emptyhandle.json_value() is None


def test_JH_012_should_work_with_unserializable_values(page: Page) -> None:
    a_handle = page.evaluate_handle(
        """() => ({
        infinity: Infinity,
        nInfinity: -Infinity,
        nan: NaN,
        nzero: -0
      })"""
    )
    infinity_handle = a_handle.get_property("infinity")
    assert infinity_handle.json_value() == float("inf")
    n_infinity_handle = a_handle.get_property("nInfinity")
    assert n_infinity_handle.json_value() == float("-inf")
    nan_handle = a_handle.get_property("nan")
    assert math.isnan(nan_handle.json_value())
    nzero_handle = a_handle.get_property("nzero")
    nzero = nzero_handle.json_value()
    assert nzero == 0
    assert math.copysign(1, nzero) == -1


def test_JH_013_get_properties_should_work(page: Page) -> None:
    a_handle = page.evaluate_handle(
        """() => ({
        foo: 'bar'
      })"""
    )
    properties = a_handle.get_properties()
    foo = properties.get("foo")
    assert foo
    assert foo.json_value() == "bar"


def test_JH_014_get_properties_should_return_empty_map_for_non_objects(
    page: Page,
) -> None:
    a_handle = page.evaluate_handle("() => 123")
    properties = a_handle.get_properties()
    assert len(properties) == 0


def test_JH_015_get_properties_should_return_properties_inhertied_from_super_class(
    page: Page,
) -> None:
    a_handle = page.evaluate_handle(
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
    properties = a_handle.get_properties()
    assert properties["a"].json_value() == "1"
    assert properties["b"].json_value() == "2"


def test_JH_016_get_properties_should_return_own_enumerable_properties_only(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/42651
    a_handle = page.evaluate_handle(
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
    assert list((a_handle.get_properties()).keys()) == ["own"]

    page.set_content("<div id=d><span>a</span><span>b</span></div>")
    collection = page.evaluate_handle("() => document.querySelector('#d').children")
    assert list((collection.get_properties()).keys()) == ["0", "1"]


def test_JH_017_get_properties_should_work_with_elements(page: Page) -> None:
    page.set_content("<div>Hello</div>")
    handle = page.evaluate_handle("() => ({ body: document.body })")
    properties = handle.get_properties()
    body = properties.get("body")
    assert isinstance(body, ElementHandle)
    assert body.text_content() == "Hello"
