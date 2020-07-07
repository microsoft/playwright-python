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
import unittest
from playwright_web.helper import Error
from .server import EMPTY_PAGE
from .test import PageTestCase, make_async

class NetworkTestCase(PageTestCase):

  async def it_should_fulfill(self):
    async def handle_request(route, request):
      self.expect(route.request).toBe(request)
      self.expect(request.url).toContain('empty.html')
      self.expect(request.headers['user-agent']).toBeTruthy()
      self.expect(request.method).toBe('GET')
      self.expect(request.postData).toBe(None)
      self.expect(request.isNavigationRequest).toBeTruthy()
      self.expect(request.resourceType).toBe('document')
      self.expect(request.frame).toBe(self.page.mainFrame)
      self.expect(request.frame.url).toBe('about:blank')
      await route.fulfill(body='Text')

    await self.page.route('**/empty.html', lambda route, request: asyncio.ensure_future(handle_request(route, request)))

    response = await self.page.goto('http://www.non-existent.com/empty.html')
    self.expect(response.ok).toBeTruthy()
    self.expect(await response.text()).toBe('Text')

  async def it_should_continue(self):
    async def handle_request(route, request, intercepted):
      intercepted.append(True)
      await route.continue_()

    intercepted = list()
    await self.page.route('**/*', lambda route, request: asyncio.ensure_future(handle_request(route, request, intercepted)))

    response = await self.page.goto(EMPTY_PAGE)
    self.expect(response.ok).toBeTruthy()
    self.expect(intercepted).toBe([True])
    self.expect(await self.page.title()).toBe('')

make_async(NetworkTestCase)
