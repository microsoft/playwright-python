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
from .assets.html import button_html, textarea_html

class ClickTestCase(PageTestCase):
  async def it_should_click_the_button(self):
    await self.page.setContent(button_html)
    await self.page.click('button')
    self.expect(await self.page.evaluate('result')).toBe('Clicked')

  async def it_should_select_the_text_by_triple_clicking(self):
    await self.page.setContent(textarea_html)
    text = 'This is the text that we are going to try to select. Let\'s see how it goes.'
    await self.page.fill('textarea', text)
    await self.page.click('textarea', clickCount=3)
    self.expect(await self.page.evaluate('''() => {
      const textarea = document.querySelector('textarea');
      return textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
    }''')).toBe(text)

  async def it_should_not_wait_with_force(self):
    await self.page.setContent(button_html)
    await self.page.evalOnSelector('button', 'b => b.style.display = "none"')
    error = None
    try:
      await self.page.click('button', force=True)
    except Error as e:
      error = e
    self.expect(error.message).toContain('Element is not visible')
    self.expect(await self.page.evaluate('result')).toBe('Was not clicked')

  async def it_should_click_the_button_with_px_border_with_offset(self):
    await self.page.setContent(button_html)
    await self.page.evalOnSelector('button', 'button => button.style.borderWidth = "8px"')
    await self.page.click('button', position=dict(x=20, y=10))
    self.expect(await self.page.evaluate('result')).toBe('Clicked')
    self.expect(await self.page.evaluate('offsetX')).toBe(20)
    self.expect(await self.page.evaluate('offsetY')).toBe(10)

make_async(ClickTestCase)
