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
import unittest
from .test import PageTestSpec
from playwright_web.helper import Error

class JSHandleSpec(PageTestSpec):
  async def it_should_work(self):
    window_handle = await self.page.evaluateHandle('window')
    self.assertIsNotNone(window_handle)

  async def it_should_accept_object_handle_as_argument(self):
    navigator_handle = await self.page.evaluateHandle('navigator')
    text = await self.page.evaluate('e => e.userAgent', navigator_handle)
    self.assertIn('Mozilla', text)

  async def it_should_accept_handle_to_primitive_types(self):
    handle = await self.page.evaluateHandle('5')
    is_five = await self.page.evaluate('e => Object.is(e, 5)', handle)
    self.assertEqual(is_five, True)

  async def it_should_accept_nested_handle(self):
    foo = await self.page.evaluateHandle('({ x: 1, y: "foo" })')
    result = await self.page.evaluate('({ foo }) => foo', { 'foo': foo })
    self.assertEqual(result, { 'x': 1, 'y': 'foo' })

  async def it_should_accept_nested_window_handle(self):
    foo = await self.page.evaluateHandle('window')
    result = await self.page.evaluate('({ foo }) => foo === window', { 'foo': foo })
    self.assertEqual(result, True)

  async def it_should_accept_multiple_nested_handles(self):
    foo = await self.page.evaluateHandle('({ x: 1, y: "foo" })')
    bar = await self.page.evaluateHandle('5')
    baz = await self.page.evaluateHandle('["baz"]')
    result = await self.page.evaluate('x => JSON.stringify(x)', {
      'a1': { 'foo': foo },
      'a2': { 'bar': bar, 'arr': [{ 'baz': baz }] }
    })
    self.assertEqual(json.loads(result), {
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
    self.assertEqual(error.message, 'Maximum argument depth exceeded')

  async def it_should_get_property(self):
    handle1 = await self.page.evaluateHandle('''() => ({
      one: 1,
      two: 2,
      three: 3
    })''')
    handle2 = await handle1.getProperty('two')
    self.assertEqual(await handle2.jsonValue(), 2)

JSHandleSpec()
