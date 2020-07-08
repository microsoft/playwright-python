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

from playwright.helper import Error
from os import path

async def test_add_init_script_evaluate_before_anything_else_on_the_page(page):
  await page.addInitScript('window.injected = 123')
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.result') == 123

async def test_add_init_script_work_with_a_path(page):
  await page.addInitScript(path=path.join(path.dirname(path.abspath(__file__)), 'assets/injectedfile.js'))
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.result') == 123

async def test_add_init_script_work_with_content(page):
  await page.addInitScript('window.injected = 123')
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.result') == 123

async def test_add_init_script_throw_without_path_and_content(page):
  error = None
  try:
    await page.addInitScript({ 'foo': 'bar' })
  except Error as e:
    error = e
  assert error.message == 'Either path or source parameter must be specified'

async def test_add_init_script_work_with_browser_context_scripts(page, context):
  await context.addInitScript('window.temp = 123')
  page = await context.newPage()
  await page.addInitScript('window.injected = window.temp')
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.result') == 123

async def test_add_init_script_work_with_browser_context_scripts_with_a_path(page, context):
  await context.addInitScript(path=path.join(path.dirname(path.abspath(__file__)), 'assets/injectedfile.js'))
  page = await context.newPage()
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.result') == 123

async def test_add_init_script_work_with_browser_context_scripts_for_already_created_pages(page, context):
  await context.addInitScript('window.temp = 123')
  await page.addInitScript('window.injected = window.temp')
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.result') == 123

async def test_add_init_script_support_multiple_scripts(page):
  await page.addInitScript('window.script1 = 1')
  await page.addInitScript('window.script2 = 2')
  await page.goto('data:text/html,<script>window.result = window.injected</script>')
  assert await page.evaluate('window.script1') == 1
  assert await page.evaluate('window.script2') == 2

