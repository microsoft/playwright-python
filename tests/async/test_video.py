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

import os


async def test_should_expose_video_path(browser, tmpdir, server):
    page = await browser.newPage(videosPath=str(tmpdir))
    await page.goto(server.PREFIX + "/grid.html")
    path = await page.video.path()
    assert str(tmpdir) in path
    await page.context.close()


async def test_short_video_should_exist(browser, tmpdir, server):
    page = await browser.newPage(videosPath=str(tmpdir))
    await page.goto(server.PREFIX + "/grid.html")
    path = await page.video.path()
    assert str(tmpdir) in path
    await page.context.close()
    assert os.path.exists(path)


async def test_short_video_should_exist_persistent_context(browser_type, tmpdir):
    context = await browser_type.launchPersistentContext(
        str(tmpdir),
        viewport={"width": 320, "height": 240},
        videosPath=str(tmpdir) + "1",
    )
    page = context.pages[0]
    await context.close()
    path = await page.video.path()
    assert str(tmpdir) in path
    assert os.path.exists(path)
