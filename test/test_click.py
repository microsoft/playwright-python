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

import pytest
from playwright_web.helper import Error
from .server import PREFIX

pytestmark = pytest.mark.asyncio

async def test_click_the_button(page):
  await page.goto(f'{PREFIX}/button.html')
  await page.click('button')
  assert await page.evaluate('result') == 'Clicked'

async def test_select_the_text_by_triple_clicking(page):
  await page.goto(f'{PREFIX}/textarea.html')
  text = 'This is the text that we are going to try to select. Let\'s see how it goes.'
  await page.fill('textarea', text)
  await page.click('textarea', clickCount=3)
  assert await page.evaluate('''() => {
    const textarea = document.querySelector('textarea');
    return textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
  }''') == text

async def test_not_wait_with_force(page):
  await page.goto(f'{PREFIX}/button.html')
  await page.evalOnSelector('button', 'b => b.style.display = "none"')
  error = None
  try:
    await page.click('button', force=True)
  except Error as e:
    error = e
  assert 'Element is not visible' in error.message
  assert await page.evaluate('result') == 'Was not clicked'

async def test_click_the_button_with_px_border_with_offset(page):
  await page.goto(f'{PREFIX}/button.html')
  await page.evalOnSelector('button', 'button => button.style.borderWidth = "8px"')
  await page.click('button', position=dict(x=20, y=10))
  assert await page.evaluate('result') == 'Clicked'
  assert await page.evaluate('offsetX') == 20
  assert await page.evaluate('offsetY') == 10
