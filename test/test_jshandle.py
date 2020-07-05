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
import unittest
from datetime import datetime
from playwright_web.helper import Error
from .test import PageTestCase

class JSHandleEvaluateTestCase(PageTestCase):
  async def it_should_work(self):
    window_handle = await self.page.evaluateHandle('window')
    self.expect(window_handle).toBeTruthy()

  async def it_should_accept_object_handle_as_argument(self):
    navigator_handle = await self.page.evaluateHandle('navigator')
    text = await self.page.evaluate('e => e.userAgent', navigator_handle)
    self.expect(text).toContain('Mozilla')

  async def it_should_accept_handle_to_primitive_types(self):
    handle = await self.page.evaluateHandle('5')
    is_five = await self.page.evaluate('e => Object.is(e, 5)', handle)
    self.expect(is_five).toBeTruthy()

  async def it_should_accept_nested_handle(self):
    foo = await self.page.evaluateHandle('({ x: 1, y: "foo" })')
    result = await self.page.evaluate('({ foo }) => foo', { 'foo': foo })
    self.expect(result).toBe({ 'x': 1, 'y': 'foo' })

  async def it_should_accept_nested_window_handle(self):
    foo = await self.page.evaluateHandle('window')
    result = await self.page.evaluate('({ foo }) => foo === window', { 'foo': foo })
    self.expect(result).toBeTruthy()

  async def it_should_accept_multiple_nested_handles(self):
    foo = await self.page.evaluateHandle('({ x: 1, y: "foo" })')
    bar = await self.page.evaluateHandle('5')
    baz = await self.page.evaluateHandle('["baz"]')
    result = await self.page.evaluate('x => JSON.stringify(x)', {
      'a1': { 'foo': foo },
      'a2': { 'bar': bar, 'arr': [{ 'baz': baz }] }
    })
    self.expect(json.loads(result)).toBe({
      'a1': { 'foo': { 'x': 1, 'y': 'foo' } },
      'a2': { 'bar': 5, 'arr': [{ 'baz': ['baz'] }] }
    })

  async def it_should_throw_for_circular_objects(self):
    a = { 'x': 1 }
    a['y'] = a
    error = None
    try:
      await self.page.evaluate('x => x', a)
    except Error as e:
      error = e
    self.expect(error.message).toContain('Maximum argument depth exceeded')

  async def it_should_accept_same_nested_object_multiple_times(self):
    foo = { 'x': 1 }
    self.expect(await self.page.evaluate('x => x', { 'foo': foo, 'bar': [foo], 'baz': { 'foo' : foo } })).toBe(
      { 'foo': { 'x': 1 }, 'bar': [{ 'x' : 1 }], 'baz': { 'foo': { 'x' : 1 } } })

  async def it_should_accept_object_handle_to_unserializable_value(self):
    handle = await self.page.evaluateHandle('() => Infinity')
    self.expect(await self.page.evaluate('e => Object.is(e, Infinity)', handle)).toBeTruthy()

  async def it_should_pass_configurable_args(self):
    result = await self.page.evaluate('''arg => {
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
    self.expect(result).toBe({})

class JSHandlePropertiesTestCase(PageTestCase):
  async def it_should_get_property(self):
    handle1 = await self.page.evaluateHandle('''() => ({
      one: 1,
      two: 2,
      three: 3
    })''')
    handle2 = await handle1.getProperty('two')
    self.expect(await handle2.jsonValue()).toBe(2)

  async def it_should_work_with_undefined_null_and_empty(self):
    handle = await self.page.evaluateHandle('''() => ({
      undefined: undefined,
      null: null,
    })''')
    undefined_handle = await handle.getProperty('undefined')
    self.expect(await undefined_handle.jsonValue()).toBe(None)
    null_handle = await handle.getProperty('null')
    self.expect(await null_handle.jsonValue()).toBe(None)
    empty_handle = await handle.getProperty('empty')
    self.expect(await empty_handle.jsonValue()).toBe(None)

  async def it_should_work_with_unserializable_values(self):
    handle = await self.page.evaluateHandle('''() => ({
      infinity: Infinity,
      negInfinity: -Infinity,
      nan: NaN,
      negZero: -0
    })''')
    infinity_handle = await handle.getProperty('infinity')
    self.expect(await infinity_handle.jsonValue()).toBe(float('inf'))
    neg_infinity_handle = await handle.getProperty('negInfinity')
    self.expect(await neg_infinity_handle.jsonValue()).toBe(float('-inf'))
    nan_handle = await handle.getProperty('nan')
    self.assertTrue(math.isnan(await nan_handle.jsonValue()))
    neg_zero_handle = await handle.getProperty('negZero')
    self.expect(await neg_zero_handle.jsonValue()).toBe(float('-0'))

  async def it_should_get_properties(self):
    handle = await self.page.evaluateHandle('() => ({ foo: "bar" })')
    properties = await handle.getProperties()
    self.expect(properties).toContain('foo')
    foo = properties['foo']
    self.expect(await foo.jsonValue()).toBe('bar')

  async def it_should_return_empty_map_for_non_objects(self):
    handle = await self.page.evaluateHandle('123')
    properties = await handle.getProperties()
    self.expect(properties).toBe({})

class JSHandleJsonValueTestCase(PageTestCase):
  async def it_should_work(self):
    handle = await self.page.evaluateHandle('() => ({foo: "bar"})')
    json = await handle.jsonValue()
    self.expect(json).toBe({'foo': 'bar'})

  async def it_should_work_with_dates(self):
    handle = await self.page.evaluateHandle('() => new Date("2020-05-27T01:31:38.506Z")')
    json = await handle.jsonValue()
    self.expect(json).toBe(datetime.fromisoformat('2020-05-27T01:31:38.506'))

  async def it_should_throw_for_circular_object(self):
    handle = await self.page.evaluateHandle('window')
    error = None
    try:
      await handle.jsonValue()
    except Error as e:
      error = e
    self.expect(error.message).toContain('Argument is a circular structure')

class JSHandleAsElementTestCase(PageTestCase):
  async def it_should_work(self):
    handle = await self.page.evaluateHandle('document.body')
    element = handle.asElement()
    self.assertIsNotNone(element)

  async def it_should_return_none_for_non_elements(self):
    handle = await self.page.evaluateHandle('2')
    element = handle.asElement()
    self.assertIsNone(element)

class JSHandleToStringTestCase(PageTestCase):
  async def it_should_work_for_primitives(self):
    number_handle = await self.page.evaluateHandle('2')
    self.expect(number_handle.toString()).toBe('JSHandle@2')
    string_handle = await self.page.evaluateHandle('"a"')
    self.expect(string_handle.toString()).toBe('JSHandle@a')

  async def it_should_work_for_complicated_objects(self):
    handle = await self.page.evaluateHandle('window')
    self.expect(handle.toString()).toBe('JSHandle@object')

  async def it_should_work_for_promises(self):
    handle = await self.page.evaluateHandle('({b: Promise.resolve(123)})')
    b_handle = await handle.getProperty('b')
    self.expect(b_handle.toString()).toBe('JSHandle@promise')

JSHandleEvaluateTestCase()
JSHandlePropertiesTestCase()
JSHandleJsonValueTestCase()
JSHandleAsElementTestCase()
JSHandleToStringTestCase()