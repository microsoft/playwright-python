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

import asyncio
import os
import sys

import unittest

from playwright_web import chromium

class ActualValue:
    def __init__(self, test_case: unittest.TestCase, value):
      self.test_case = test_case
      self.value = value

    def toBe(self, value):
      self.test_case.assertEqual(self.value, value)

    def toContain(self, value):
      self.test_case.assertIn(value, self.value)

    def toBeTruthy(self):
      if not self.value:
        self.test_case.assertTrue(False)

class TestCase(unittest.TestCase):
  def setUp(self):
    asyncio.get_event_loop().run_until_complete(self.before_each())

  def tearDown(self):
    asyncio.get_event_loop().run_until_complete(self.after_each())

  async def before_each(self):
    return None

  async def after_each(self):
    return None

  def expect(self, value: any) -> ActualValue:
    return ActualValue(self, value)

class PageTestCase(TestCase):

  @classmethod
  def setUpClass(cls):
    asyncio.get_event_loop().run_until_complete(cls.before_all())

  @classmethod
  def tearDownClass(cls):
    asyncio.get_event_loop().run_until_complete(cls.after_all())

  @classmethod
  async def before_all(cls):
    cls.browser = await chromium.launch()

  @classmethod
  async def after_all(cls):
    await cls.browser.close()

  async def before_each(self):
    self.context = await self.browser.newContext()
    self.page = await self.context.newPage()

  async def after_each(self):
    await self.context.close()
    self.context = None
    self.page = None


def make_async(cls):
  def add_test(name):
    def do_test_expected(self):
      asyncio.get_event_loop().run_until_complete(cls.__dict__[name](self))
    test_method = do_test_expected
    test_method.__name__ = 'test_' + name
    setattr(cls, 'test_' + name, test_method)

  tests = list()
  for name in cls.__dict__:
    if name.startswith('fit_'):
      tests.append(name)
    if not len(tests):
      for name in cls.__dict__:
        if name.startswith('it_'):
          tests.append(name)
  for name in tests:
    add_test(name)
