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
import unittest
from datetime import datetime
from playwright_web.helper import Error
from .test import PageTestCase, make_async

class EvaluateTestCase(PageTestCase):
  async def it_should_work(self):
    result = await self.page.evaluate('7 * 3')
    assert result == 21

  async def it_should_return_none_for_null(self):
    result = await self.page.evaluate('a => a', None)
    self.assertIsNone(result)

  async def it_should_transfer_nan(self):
    result = await self.page.evaluate('a => a', float('nan'))
    assert math.isnan(result)

  async def it_should_transfer_neg_zero(self):
    result = await self.page.evaluate('a => a', -0)
    assert result == float('-0')

  async def it_should_transfer_infinity(self):
    result = await self.page.evaluate('a => a', float('Infinity'))
    assert result == float('Infinity')

  async def it_should_transfer_neg_infinity(self):
    result = await self.page.evaluate('a => a', float('-Infinity'))
    assert result == float('-Infinity')

  async def it_should_roundtrip_unserializable_values(self):
    value = {
      'infinity': float('Infinity'),
      'nInfinity': float('-Infinity'),
      'nZero': float('-0')
    }
    result = await self.page.evaluate('a => a', value)
    assert result == value

  async def it_should_transfer_arrays(self):
    result = await self.page.evaluate('a => a', [1, 2, 3])
    assert result == [1, 2, 3]

  async def it_return_undefined_for_objects_with_symbols(self):
    assert await self.page.evaluate('[Symbol("foo4")]') == [None]
    assert await self.page.evaluate('''() => {
      const a = { };
      a[Symbol('foo4')] = 42;
      return a;
    }''') == {}
    assert await self.page.evaluate('''() => {
      return { foo: [{ a: Symbol('foo4') }] };
    }''') == { 'foo': [{ 'a': None } ] }

  async def it_should_work_with_unicode_chars(self):
    result = await self.page.evaluate('a => a["中文字符"]', { '中文字符' : 42 })
    assert result == 42

  async def it_should_throw_when_evaluation_triggers_reload(self):
    error = None
    try:
      await self.page.evaluate('() => { location.reload(); return new Promise(() => {}); }')
    except Error as e:
      error = e
    assert 'navigation' in error.message

  async def it_should_work_with_exposed_function(self):
    await self.page.exposeFunction('callController', lambda a, b: a * b)
    result = await self.page.evaluate('callController(9, 3)')
    assert result == 27

  async def it_should_reject_promise_with_exception(self):
    error = None
    try:
      await self.page.evaluate('not_existing_object.property')
    except Error as e:
      error = e
    assert 'not_existing_object' in error.message

  async def it_should_support_thrown_strings(self):
    error = None
    try:
      await self.page.evaluate('throw "qwerty"')
    except Error as e:
      error = e
    assert 'qwerty' in error.message

  async def it_should_support_thrown_numbers(self):
    error = None
    try:
      await self.page.evaluate('throw 100500')
    except Error as e:
      error = e
    assert '100500' in error.message

  async def it_should_return_complex_objects(self):
    obj = { 'foo': 'bar!' }
    result = await self.page.evaluate('a => a', obj)
    assert result == obj

  async def it_should_accept_none_as_one_of_multiple_parameters(self):
    result = await self.page.evaluate('({ a, b }) => Object.is(a, undefined) && Object.is(b, "foo")', { 'a': None, 'b': 'foo' })
    assert result

  async def it_should_properly_serialize_none_arguments(self):
    assert await self.page.evaluate('x => ({a: x})', None) == { 'a': None }

  async def it_should_fail_for_circular_object(self):
    self.assertIsNone(await self.page.evaluate('''() => {
      const a = {};
      const b = {a};
      a.b = b;
      return a;
    }'''))

  async def it_should_accept_string(self):
    assert await self.page.evaluate('1 + 2') == 3

  async def it_should_accept_element_handle_as_an_argument(self):
    await self.page.setContent('<section>42</section>')
    element = await self.page.querySelector('section')
    text = await self.page.evaluate('e => e.textContent', element)
    assert text == '42'

  async def it_should_throw_if_underlying_element_was_disposed(self):
    await self.page.setContent('<section>39</section>')
    element = await self.page.querySelector('section')
    await element.dispose()
    error = None
    try:
      await self.page.evaluate('e => e.textContent', element)
    except Error as e:
      error = e
    assert 'JSHandle is disposed' in error.message

  async def it_should_evaluate_exception(self):
    error = await self.page.evaluate('new Error("error message")')
    assert 'Error: error message' in error

  async def it_should_evaluate_date(self):
    result = await self.page.evaluate('() => ({ date: new Date("2020-05-27T01:31:38.506Z") })')
    assert result == { 'date': datetime.fromisoformat('2020-05-27T01:31:38.506') }

  async def it_should_roundtrip_date(self):
    date = datetime.fromisoformat('2020-05-27T01:31:38.506')
    result = await self.page.evaluate('date => date', date)
    assert result == date

  async def it_should_jsonvalue_date(self):
    date = datetime.fromisoformat('2020-05-27T01:31:38.506')
    result = await self.page.evaluate('() => ({ date: new Date("2020-05-27T01:31:38.506Z") })')
    assert result == { 'date': date }

make_async(EvaluateTestCase)
