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
from .server import EMPTY_PAGE, PORT

class FramesTestCase(PageTestCase):

  async def it_should_respect_name(self):
    await self.page.setContent('<iframe name=target></iframe>')
    self.expect(self.page.frame(name='bogus')).toBe(None)
    frame = self.page.frame(name='target')
    self.expect(frame).toBeTruthy()
    self.expect(frame).toBe(self.page.mainFrame.childFrames[0])

  async def it_should_respect_url(self):
    await self.page.setContent(f'<iframe src="{EMPTY_PAGE}"></iframe>')
    self.expect(self.page.frame(url='bogus')).toBe(None)
    self.expect(self.page.frame(url=f'**/empty.html').url).toBe('http://localhost:8907/empty.html')

make_async(FramesTestCase)
