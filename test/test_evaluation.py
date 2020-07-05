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

import unittest
from .test import PageTestSpec
from playwright_web.helper import Error

class EvaluationSpec(PageTestSpec):
  async def it_should_work(self):
    result = await self.page.evaluate('7 * 3')
    self.assertEqual(result, 21)

  async def it_should_transfer_neg_zero(self):
    result = await self.page.evaluate('a => a', -0)
    self.assertEqual(result, float('-0'))

  async def it_should_transfer_infinity(self):
    result = await self.page.evaluate('a => a', float('Infinity'))
    self.assertEqual(result, float('Infinity'))

  async def it_should_transfer_neg_infinity(self):
    result = await self.page.evaluate('a => a', float('-Infinity'))
    self.assertEqual(result, float('-Infinity'))

  async def it_should_roundtrip_unserializable_values(self):
    value = {
      'infinity': float('Infinity'),
      'nInfinity': float('-Infinity'),
      'nZero': float('-0')
    }
    result = await self.page.evaluate('a => a', value)
    self.assertEqual(result, value)

  async def it_should_transfer_arrays(self):
    result = await self.page.evaluate('a => a', [1, 2, 3])
    self.assertEqual(result, [1, 2, 3])

  async def it_return_undefined_for_objects_with_symbols(self):
    self.assertEqual(await self.page.evaluate('[Symbol("foo4")]'), [None])
    self.assertEqual(await self.page.evaluate('''() => {
      const a = { };
      a[Symbol('foo4')] = 42;
      return a;
    }'''), {})
    self.assertEqual(await self.page.evaluate('''() => {
      return { foo: [{ a: Symbol('foo4') }] };
    }'''), { 'foo': [{ 'a': None } ] })

  async def it_should_work_with_unicode_chars(self):
    result = await self.page.evaluate('a => a["中文字符"]', { '中文字符' : 42 })
    self.assertEqual(result, 42)

  async def it_should_throw_when_evaluation_triggers_reload(self):
    error = None
    try:
      await self.page.evaluate('() => { location.reload(); return new Promise(() => {}); }')
    except Error as e:
      error = e
    self.assertIn('navigation', error.message)
  
  async def it_should_work_with_exposed_function(self):
    await self.page.exposeFunction('callController', lambda a, b: a * b)
    result = await self.page.evaluate('callController(9, 3)')
    self.assertEqual(result, 27)

  async def it_should_reject_promise_with_exception(self):
    error = None
    try:
      await self.page.evaluate('not_existing_object.property')
    except Error as e:
      error = e
    self.assertIn('not_existing_object', error.message)

  async def it_should_support_thrown_strings(self):
    error = None
    try:
      await self.page.evaluate('throw "qwerty"')
    except Error as e:
      error = e
    self.assertIn('qwerty', error.message)

  async def it_should_support_thrown_numbers(self):
    error = None
    try:
      await self.page.evaluate('throw 100500')
    except Error as e:
      error = e
    self.assertIn('100500', error.message)

  async def it_should_return_complex_objects(self):
    object = { 'foo': 'bar!' }
    result = await self.page.evaluate('a => a', object)
    self.assertEqual(result, object)

EvaluationSpec()
