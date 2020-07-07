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

from .server import PREFIX

async def test_keyboard_type_into_a_textarea(page):
  await page.evaluate('''
    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    textarea.focus();
  ''')
  text = 'Hello world. I am the text that was typed!'
  await page.keyboard.type(text)
  assert await page.evaluate('document.querySelector("textarea").value') == text

async def test_keyboard_move_with_the_arrow_keys(page):
  await page.goto(f'{PREFIX}/textarea.html')
  await page.type('textarea', 'Hello World!')
  assert await page.evaluate("document.querySelector('textarea').value") == 'Hello World!'
  for _ in 'World!':
    await page.keyboard.press('ArrowLeft')
  await page.keyboard.type('inserted ')
  assert await page.evaluate("document.querySelector('textarea').value")  == 'Hello inserted World!'
  await page.keyboard.down('Shift')
  for _ in 'inserted ':
    await page.keyboard.press('ArrowLeft')
  await page.keyboard.up('Shift')
  await page.keyboard.press('Backspace')
  assert await page.evaluate("document.querySelector('textarea').value") == 'Hello World!'

async def test_keyboard_send_a_character_with_elementhandle_press(page):
  await page.goto(f'{PREFIX}/textarea.html')
  textarea = await page.querySelector('textarea')
  await textarea.press('a')
  assert await page.evaluate("document.querySelector('textarea').value") == 'a'
  await page.evaluate("() => window.addEventListener('keydown', e => e.preventDefault(), true)")
  await textarea.press('b')
  assert await page.evaluate("document.querySelector('textarea').value") == 'a'

