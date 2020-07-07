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
from playwright_web.helper import Error
from .test import PageTestCase, make_async
from .server import PREFIX

class FillTestCase(PageTestCase):

  async def it_should_fill_textarea(self):
    await self.page.goto(f'{PREFIX}/textarea.html')
    await self.page.fill('textarea', 'some value')
    self.expect(await self.page.evaluate('result')).toBe('some value')

  async def it_should_fill_input(self):
    await self.page.goto(f'{PREFIX}/textarea.html')
    await self.page.fill('input', 'some value')
    self.expect(await self.page.evaluate('result')).toBe('some value')

make_async(FillTestCase)
