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

async def test_frames_respect_name(page):
  await page.setContent('<iframe name=target></iframe>')
  assert page.frame(name='bogus') is None
  frame = page.frame(name='target')
  assert frame
  assert frame == (page.mainFrame.childFrames[0])

async def test_frames_respect_url(page, server):
  await page.setContent(f'<iframe src="{server.EMPTY_PAGE}"></iframe>')
  assert page.frame(url='bogus') is None
  assert page.frame(url=f'**/empty.html').url == (f'http://localhost:{server.PORT}/empty.html')
