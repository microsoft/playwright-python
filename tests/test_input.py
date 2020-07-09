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
from os import path
import os

from playwright.page import Page

FILE_TO_UPLOAD = path.join(os.path.dirname(os.path.realpath(__file__)), 'assets/file-to-upload.txt')

__dirname = os.path.dirname(os.path.realpath(__file__))

async def test_should_upload_the_file(page, server):
    await page.goto(server.PREFIX + '/input/fileupload.html')
    filePath = path.relpath(FILE_TO_UPLOAD, os.getcwd())
    input = await page.querySelector('input')
    await input.setInputFiles(filePath)
    assert await page.evaluate('e => e.files[0].name', input) == 'file-to-upload.txt'
    assert await page.evaluate('''e => {
        reader = new FileReader()
        promise = new Promise(fulfill => reader.onload = fulfill)
        reader.readAsText(e.files[0])
        return promise.then(() => reader.result)
    }''', input) == 'contents of the file'


async def test_should_work(page):
    await page.setContent('<input type=file>')
    await page.setInputFiles('input', path.join(__dirname, 'assets/file-to-upload.txt'))
    assert await page.evalOnSelector('input', 'input => input.files.length') == 1
    assert await page.evalOnSelector('input', 'input => input.files[0].name') == 'file-to-upload.txt'

async def test_should_set_from_memory(page):
    await page.setContent('<input type=file>')
    await page.setInputFiles('input', files=[{
         "name": 'test.txt',
         "mimeType": 'text/plain',
         "buffer": b'this is a test'}]
    )
    assert await page.evalOnSelector('input', 'input => input.files.length') == 1
    assert await page.evalOnSelector('input', 'input => input.files[0].name') == 'test.txt'


async def test_should_emit_event(page: Page, server):
    await page.setContent('<input type=file>')
    fc_done = asyncio.Future()
    page.once('filechooser', lambda fileChooser: fc_done.set_result(fileChooser)),
    await page.click('input')
    file_chooser = await fc_done
    assert file_chooser

async def test_should_work_when_file_input_is_attached_to_DOM(page:Page, server):
    await page.setContent('<input type=file>')
    file_chooser = page.waitForEvent("filechooser")
    await page.click('input')
    assert await file_chooser

async def test_should_work_when_file_input_is_not_attached_to_DOM(page, server):
    await page.evaluate('''() => {
        el = document.createElement('input')
        el.type = 'file'
        el.click()
      }''')
    file_chooser = page.waitForEvent("filechooser")
    assert await file_chooser

async def test_should_return_the_same_file_chooser_when_there_are_many_watchdogs_simultaneously(page:Page, server):
    await page.setContent('<input type=file>')
    results = await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.waitForEvent('filechooser'),
      page.evalOnSelector('input', 'input => input.click()'),
    )
    assert results[0] == results[1]

async def test_should_accept_single_file(page:Page, server):
    await page.setContent('<input type=file oninput="javascript:console.timeStamp()">')
    fileChooser = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.click('input'),
    ))[0]
    assert fileChooser.page == page
    assert fileChooser.element
    await fileChooser.setFiles(FILE_TO_UPLOAD)
    assert await page.evalOnSelector('input', 'input => input.files.length') == 1
    assert await page.evalOnSelector('input', 'input => input.files[0].name') == 'file-to-upload.txt'


async def test_should_be_able_to_read_selected_file(page: Page, server):
    page.once('filechooser',  lambda fileChooser: asyncio.ensure_future(fileChooser.setFiles(FILE_TO_UPLOAD)))
    await page.setContent('<input type=file>')
    content = await page.evalOnSelector('input', '''async picker => {
        picker.click();
        await new Promise(x => picker.oninput = x);
        const reader = new FileReader();
        const promise = new Promise(fulfill => reader.onload = fulfill);
        reader.readAsText(picker.files[0]);
        return promise.then(() => reader.result);
      }''')
    assert content == 'contents of the file'

async def test_should_be_able_to_reset_selected_files_with_empty_file_list(page:Page, server):
    await page.setContent('<input type=file>')
    page.once('filechooser',  lambda fileChooser: asyncio.ensure_future(fileChooser.setFiles(FILE_TO_UPLOAD)))
    fileLength1 = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.evalOnSelector('input', '''async picker => {
        picker.click();
        await new Promise(x => picker.oninput = x);
        return picker.files.length;
      }'''),
    ))[1]
    assert fileLength1 == 1

    page.once("filechooser", lambda fileChooser: asyncio.ensure_future(fileChooser.setFiles([])))
    fileLength2 = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.evalOnSelector('input', '''async picker => {
        picker.click()
        await new Promise(x => picker.oninput = x)
        return picker.files.length
      }'''),
    ))[1]
    assert fileLength2 == 0

async def test_should_not_accept_multiple_files_for_single_file_input(page, server):
    await page.setContent('<input type=file>')
    fileChooser = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.click('input'),
    ))[0]
    error = None
    try:
        await fileChooser.setFiles([
            path.relative(__dirname + 'assets/file-to-upload.txt'),
            path.relative(__dirname + 'assets/pptr.png')
        ])
    except Exception as exc:
        error = exc
    assert error != None

async def test_should_emit_input_and_change_events(page, server):
    events = []
    await page.exposeFunction('eventHandled', lambda e: events.append(e))
    await page.setContent('''
    <input id=input type=file></input>
    <script>
      input.addEventListener('input', e => eventHandled({ type: e.type }))
      input.addEventListener('change', e => eventHandled({ type: e.type }))
    </script>''')
    await (await page.querySelector('input')).setInputFiles(FILE_TO_UPLOAD)
    assert len(events) == 2
    assert events[0]["type"] == 'input'
    assert events[1]["type"] == 'change'

async def test_should_work_for_single_file_pick(page, server):
    await page.setContent('<input type=file>')
    fileChooser = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.click('input'),
    ))[0]
    assert fileChooser.isMultiple == False

async def test_should_work_for_multiple(page, server):
    await page.setContent('<input multiple type=file>')
    fileChooser = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.click('input'),
    ))[0]
    assert fileChooser.isMultiple

async def test_should_work_for_webkitdirectory(page, server):
    await page.setContent('<input multiple webkitdirectory type=file>')
    fileChooser = (await asyncio.gather(
      page.waitForEvent('filechooser'),
      page.click('input'),
    ))[0]
    assert fileChooser.isMultiple



