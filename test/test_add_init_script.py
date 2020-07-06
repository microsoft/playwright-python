# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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
from os import path

class AddInitScriptTestCase(PageTestCase):
  async def it_should_evaluate_before_anything_else_on_the_page(self):
    await self.page.addInitScript('window.injected = 123')
    await self.page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await self.page.evaluate('window.result')).toBe(123)

  async def it_should_work_with_a_path(self):
    await self.page.addInitScript(path=path.join(path.dirname(path.abspath(__file__)), 'assets/injectedfile.js'))
    await self.page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await self.page.evaluate('window.result')).toBe(123)

  async def it_should_work_with_content(self):
    await self.page.addInitScript('window.injected = 123')
    await self.page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await self.page.evaluate('window.result')).toBe(123)

  async def it_should_throw_without_path_and_content(self):
    error = None
    try:
      await self.page.addInitScript({ 'foo': 'bar' })
    except Error as e:
      error = e
    self.expect(error.message).toBe('Either path or source parameter must be specified')

  async def it_should_work_with_browser_context_scripts(self):
    await self.context.addInitScript('window.temp = 123')
    page = await self.context.newPage()
    await page.addInitScript('window.injected = window.temp')
    await page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await page.evaluate('window.result')).toBe(123)

  async def it_should_work_with_browser_context_scripts_with_a_path(self):
    await self.context.addInitScript(path=path.join(path.dirname(path.abspath(__file__)), 'assets/injectedfile.js'))
    page = await self.context.newPage()
    await page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await page.evaluate('window.result')).toBe(123)

  async def it_should_work_with_browser_context_scripts_for_already_created_pages(self):
    await self.context.addInitScript('window.temp = 123')
    await self.page.addInitScript('window.injected = window.temp')
    await self.page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await self.page.evaluate('window.result')).toBe(123)

  async def it_should_support_multiple_scripts(self):
    await self.page.addInitScript('window.script1 = 1')
    await self.page.addInitScript('window.script2 = 2')
    await self.page.goto('data:text/html,<script>window.result = window.injected</script>')
    self.expect(await self.page.evaluate('window.script1')).toBe(1)
    self.expect(await self.page.evaluate('window.script2')).toBe(2)

make_async(AddInitScriptTestCase)
