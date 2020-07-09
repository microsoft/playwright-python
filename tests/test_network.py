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

async def test_request_fulfill(page):
  async def handle_request(route, request):
    assert route.request == request
    assert 'empty.html' in request.url
    assert request.headers['user-agent']
    assert request.method == 'GET'
    assert request.postData is None
    assert request.isNavigationRequest
    assert request.resourceType == 'document'
    assert request.frame == page.mainFrame
    assert request.frame.url == 'about:blank'
    await route.fulfill(body='Text')

  await page.route('**/empty.html', lambda route, request: asyncio.ensure_future(handle_request(route, request)))

  response = await page.goto('http://www.non-existent.com/empty.html')
  assert response.ok
  assert await response.text() == 'Text'

async def test_request_continue(page, server):
  async def handle_request(route, request, intercepted):
    intercepted.append(True)
    await route.continue_()

  intercepted = list()
  await page.route('**/*', lambda route, request: asyncio.ensure_future(handle_request(route, request, intercepted)))

  response = await page.goto(server.EMPTY_PAGE)
  assert response.ok
  assert intercepted == [True]
  assert await page.title() == ''
