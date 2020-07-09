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
import json
import math
from datetime import datetime
from playwright import file_chooser
from playwright.page import Page
from playwright.helper import Error
from playwright import TimeoutError
from os import path
import os

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

# TODO: add support for timeout
# async def test_should_respect_timeout(page:Page, server):
#     error = None
#     try:
#         await page.waitForEvent('filechooser', timeout=1)
#     except Exception as exc:
#         error = exc
#     assert type(error) == type(TimeoutError)

#   async def test_should_respect_default_timeout_when_there_is_no_custom_timeout(page, server):
#     page.setDefaultTimeout(1)
#     error = None
#     await page.waitForEvent('filechooser').catch(e => error = e)
#     expect(error).toBeInstanceOf(playwright.errors.TimeoutError)

#   async def test_should_prioritize_exact_timeout_over_default_timeout(page, server):
#     page.setDefaultTimeout(0)
#     error = None
#     await page.waitForEvent('filechooser', {'timeout':1}).catch(e => error = e)
#     expect(error).toBeInstanceOf(playwright.errors.TimeoutError)

#   async def test_should_work_with_no_timeout(page, server):
#     [chooser] = await asyncio.gather(
#       page.waitForEvent('filechooser', {'timeout':0}),
#       page.evaluate('() => setTimeout(() => {
#         el = document.createElement('input')
#         el.type = 'file'
#         el.click()
#       }, 50))
#     ])
#     expect(chooser).toBeTruthy()

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

#   async def test_should_detect_mime_type(page, server):
#     files
#     server.setRoute('/upload', async (req, res) => {
#       form = new formidable.IncomingForm()
#       form.parse(req, function(err, fields, f) {
#         files = f
#         res.end()


#     await page.goto(server.EMPTY_PAGE)
#     await page.setContent(`
#       <form action="/upload" method="post" enctype="multipart/form-data" >
#         <input type="file" name="file1">
#         <input type="file" name="file2">
#         <input type="submit" value="Submit">
#       </form>`)
#     await (await page.querySelector('input[name=file1]')).setInputFiles(path.join(__dirname, '/assets/file-to-upload.txt'))
#     await (await page.querySelector('input[name=file2]')).setInputFiles(path.join(__dirname, '/assets/pptr.png'))
#     await asyncio.gather(
#       page.click('input[type=submit]'),
#       server.waitForRequest('/upload'),
#     ])
#     { file1, file2 } = files
#     assert file1.name == 'file-to-upload.txt'
#     assert file1.type == 'text/plain'
#     expect(fs.readFileSync(file1.path).toString()).toBe(
#       fs.readFileSync(path.join(__dirname, '/assets/file-to-upload.txt')).toString())
#     assert file2.name == 'pptr.png'
#     assert file2.type == 'image/png'
#     expect(fs.readFileSync(file2.path).toString()).toBe(
#       fs.readFileSync(path.join(__dirname, '/assets/pptr.png')).toString())

#   async def test_should_be_able_to_read_selected_file(page, server):
#     await page.setContent('<input type=file>')
#     [, content] = await asyncio.gather(
#       page.waitForEvent('filechooser').then(fileChooser => fileChooser.setFiles(FILE_TO_UPLOAD)),
#       page.evalOnSelector('input', async picker => {
#         picker.click()
#         await new Promise(x => picker.oninput = x)
#         reader = new FileReader()
#         promise = new Promise(fulfill => reader.onload = fulfill)
#         reader.readAsText(picker.files[0])
#         return promise.then(() => reader.result)
#       }),
#     ])
#     assert content == 'contents of the file'

# async def test_should_be_able_to_reset_selected_files_with_empty_file_list(page:Page, server):
#     await page.setContent('<input type=file>')
#     page.once("filechooser", lambda fileChooser: fileChooser.setFiles(FILE_TO_UPLOAD))
#     print("block")
#     fileLength1 = (await asyncio.gather(
#       page.waitForEvent('filechooser'),
#       page.evalOnSelector('input', '''async picker => {
#         picker.click();
#         await new Promise(x => picker.oninput = x);
#         return picker.files.length;
#       }'''),
#     ))[1]
#     assert fileLength1 == 1

    # page.once("filechooser", lambda fileChooser: fileChooser.setFiles([]))
    # fileLength2 = (await asyncio.gather(
    #   page.waitForEvent('filechooser'),
    #   page.evalOnSelector('input', '''async picker => {
    #     picker.click()
    #     await new Promise(x => picker.oninput = x)
    #     return picker.files.length
    #   }'''),
    # ))[1]
    # assert fileLength2 == 0

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



