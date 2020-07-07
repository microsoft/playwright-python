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

class KeyboardTestCase(PageTestCase):
  async def it_should_type_into_a_textarea(self):
    await self.page.evaluate('''
      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);
      textarea.focus();
    ''')
    text = 'Hello world. I am the text that was typed!'
    await self.page.keyboard.type(text)
    self.expect(await self.page.evaluate('document.querySelector("textarea").value')).toBe(text)

  async def it_should_move_with_the_arrow_keys(self):
    await self.page.goto(f'{PREFIX}/textarea.html')
    await self.page.type('textarea', 'Hello World!')
    self.expect(await self.page.evaluate("document.querySelector('textarea').value")).toBe('Hello World!')
    for _ in 'World!':
      await self.page.keyboard.press('ArrowLeft')
    await self.page.keyboard.type('inserted ')
    self.expect(await self.page.evaluate("document.querySelector('textarea').value")).toBe('Hello inserted World!')
    await self.page.keyboard.down('Shift')
    for _ in 'inserted ':
      await self.page.keyboard.press('ArrowLeft')
    await self.page.keyboard.up('Shift')
    await self.page.keyboard.press('Backspace')
    self.expect(await self.page.evaluate("document.querySelector('textarea').value")).toBe('Hello World!')

  async def it_should_send_a_character_with_elementhandle_press(self):
    await self.page.goto(f'{PREFIX}/textarea.html')
    textarea = await self.page.querySelector('textarea')
    await textarea.press('a')
    self.expect(await self.page.evaluate("document.querySelector('textarea').value")).toBe('a')
    await self.page.evaluate("() => window.addEventListener('keydown', e => e.preventDefault(), true)")
    await textarea.press('b')
    self.expect(await self.page.evaluate("document.querySelector('textarea').value")).toBe('a')

make_async(KeyboardTestCase)
