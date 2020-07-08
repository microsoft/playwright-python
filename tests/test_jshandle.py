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
from datetime import datetime
from playwright.helper import Error

async def test_jshandle_evaluate_work(page):
  window_handle = await page.evaluateHandle('window')
  assert window_handle

async def test_jshandle_evaluate_accept_object_handle_as_argument(page):
  navigator_handle = await page.evaluateHandle('navigator')
  text = await page.evaluate('e => e.userAgent', navigator_handle)
  assert 'Mozilla' in text

async def test_jshandle_evaluate_accept_handle_to_primitive_types(page):
  handle = await page.evaluateHandle('5')
  is_five = await page.evaluate('e => Object.is(e, 5)', handle)
  assert is_five

async def test_jshandle_evaluate_accept_nested_handle(page):
  foo = await page.evaluateHandle('({ x: 1, y: "foo" })')
  result = await page.evaluate('({ foo }) => foo', { 'foo': foo })
  assert result == { 'x': 1, 'y': 'foo' }

async def test_jshandle_evaluate_accept_nested_window_handle(page):
  foo = await page.evaluateHandle('window')
  result = await page.evaluate('({ foo }) => foo === window', { 'foo': foo })
  assert result

async def test_jshandle_evaluate_accept_multiple_nested_handles(page):
  foo = await page.evaluateHandle('({ x: 1, y: "foo" })')
  bar = await page.evaluateHandle('5')
  baz = await page.evaluateHandle('["baz"]')
  result = await page.evaluate('x => JSON.stringify(x)', {
    'a1': { 'foo': foo },
    'a2': { 'bar': bar, 'arr': [{ 'baz': baz }] }
  })
  assert json.loads(result) == {
    'a1': { 'foo': { 'x': 1, 'y': 'foo' } },
    'a2': { 'bar': 5, 'arr': [{ 'baz': ['baz'] }] }
  }

async def test_jshandle_evaluate_throw_for_circular_objects(page):
  a = { 'x': 1 }
  a['y'] = a
  error = None
  try:
    await page.evaluate('x => x', a)
  except Error as e:
    error = e
  assert 'Maximum argument depth exceeded' in error.message

async def test_jshandle_evaluate_accept_same_nested_object_multiple_times(page):
  foo = { 'x': 1 }
  assert await page.evaluate('x => x', { 'foo': foo, 'bar': [foo], 'baz': { 'foo' : foo } }) == {
    'foo': { 'x': 1 }, 'bar': [{ 'x' : 1 }], 'baz': { 'foo': { 'x' : 1 } } }

async def test_jshandle_evaluate_accept_object_handle_to_unserializable_value(page):
  handle = await page.evaluateHandle('() => Infinity')
  assert await page.evaluate('e => Object.is(e, Infinity)', handle)

async def test_jshandle_evaluate_pass_configurable_args(page):
  result = await page.evaluate('''arg => {
    if (arg.foo !== 42)
      throw new Error('Not a 42');
    arg.foo = 17;
    if (arg.foo !== 17)
      throw new Error('Not 17');
    delete arg.foo;
    if (arg.foo === 17)
      throw new Error('Still 17');
    return arg;
  }''', { 'foo': 42 })
  assert result == {}

async def test_jshandle_properties_get_property(page):
  handle1 = await page.evaluateHandle('''() => ({
    one: 1,
    two: 2,
    three: 3
  })''')
  handle2 = await handle1.getProperty('two')
  assert await handle2.jsonValue() == 2

async def test_jshandle_properties_work_with_undefined_null_and_empty(page):
  handle = await page.evaluateHandle('''() => ({
    undefined: undefined,
    null: null,
  })''')
  undefined_handle = await handle.getProperty('undefined')
  assert await undefined_handle.jsonValue() is None
  null_handle = await handle.getProperty('null')
  assert await null_handle.jsonValue() is None
  empty_handle = await handle.getProperty('empty')
  assert await empty_handle.jsonValue() is None

async def test_jshandle_properties_work_with_unserializable_values(page):
  handle = await page.evaluateHandle('''() => ({
    infinity: Infinity,
    negInfinity: -Infinity,
    nan: NaN,
    negZero: -0
  })''')
  infinity_handle = await handle.getProperty('infinity')
  assert await infinity_handle.jsonValue() == float('inf')
  neg_infinity_handle = await handle.getProperty('negInfinity')
  assert await neg_infinity_handle.jsonValue() == float('-inf')
  nan_handle = await handle.getProperty('nan')
  assert math.isnan(await nan_handle.jsonValue()) is True
  neg_zero_handle = await handle.getProperty('negZero')
  assert await neg_zero_handle.jsonValue() == float('-0')

async def test_jshandle_properties_get_properties(page):
  handle = await page.evaluateHandle('() => ({ foo: "bar" })')
  properties = await handle.getProperties()
  assert 'foo' in properties
  foo = properties['foo']
  assert await foo.jsonValue() == 'bar'

async def test_jshandle_properties_return_empty_map_for_non_objects(page):
  handle = await page.evaluateHandle('123')
  properties = await handle.getProperties()
  assert properties == {}

async def test_jshandle_json_value_work(page):
  handle = await page.evaluateHandle('() => ({foo: "bar"})')
  json = await handle.jsonValue()
  assert json == {'foo': 'bar'}

async def test_jshandle_json_value_work_with_dates(page):
  handle = await page.evaluateHandle('() => new Date("2020-05-27T01:31:38.506Z")')
  json = await handle.jsonValue()
  assert json == datetime.fromisoformat('2020-05-27T01:31:38.506')

async def test_jshandle_json_value_throw_for_circular_object(page):
  handle = await page.evaluateHandle('window')
  error = None
  try:
    await handle.jsonValue()
  except Error as e:
    error = e
  assert 'Argument is a circular structure' in error.message

async def test_jshandle_as_element_work(page):
  handle = await page.evaluateHandle('document.body')
  element = handle.asElement()
  assert element is not None

async def test_jshandle_as_element_return_none_for_non_elements(page):
  handle = await page.evaluateHandle('2')
  element = handle.asElement()
  assert element is None

async def test_jshandle_to_string_work_for_primitives(page):
  number_handle = await page.evaluateHandle('2')
  assert number_handle.toString() == 'JSHandle@2'
  string_handle = await page.evaluateHandle('"a"')
  assert string_handle.toString() == 'JSHandle@a'

async def test_jshandle_to_string_work_for_complicated_objects(page):
  handle = await page.evaluateHandle('window')
  assert handle.toString() == 'JSHandle@object'

async def test_jshandle_to_string_work_for_promises(page):
  handle = await page.evaluateHandle('({b: Promise.resolve(123)})')
  b_handle = await handle.getProperty('b')
  assert b_handle.toString() == 'JSHandle@promise'
