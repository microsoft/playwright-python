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

async def test_fill_textarea(page):
  await page.goto(f'{PREFIX}/textarea.html')
  await page.fill('textarea', 'some value')
  assert await page.evaluate('result') == 'some value'

async def test_fill_input(page):
  await page.goto(f'{PREFIX}/textarea.html')
  await page.fill('input', 'some value')
  assert await page.evaluate('result') == 'some value'

