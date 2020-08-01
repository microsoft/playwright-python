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
from asyncio import Future

import pytest

from playwright.dialog import Dialog
from playwright.page import Page


async def test_should_fire(page: Page, server):
    on_dialog_actions_complete: Future[None] = asyncio.Future()

    async def on_dialog(dialog: Dialog):
        assert dialog.type == "alert"
        assert dialog.defaultValue == ""
        assert dialog.message == "yo"
        on_dialog_actions_complete.set_result(await dialog.accept())

    page.on("dialog", lambda dialog: asyncio.create_task(on_dialog(dialog)))
    await page.evaluate("alert('yo')")
    await on_dialog_actions_complete


async def test_should_allow_accepting_prompts(page: Page, server):
    on_dialog_actions_complete: Future[None] = asyncio.Future()

    async def on_dialog(dialog: Dialog):
        assert dialog.type == "prompt"
        assert dialog.defaultValue == "yes."
        assert dialog.message == "question?"
        on_dialog_actions_complete.set_result(await dialog.accept("answer!"))

    page.on("dialog", lambda dialog: asyncio.create_task(on_dialog(dialog)))
    assert await page.evaluate("prompt('question?', 'yes.')") == "answer!"
    await on_dialog_actions_complete


async def test_should_dismiss_the_prompt(page: Page, server):
    on_dialog_actions_complete: Future[None] = asyncio.Future()

    async def on_dialog(dialog: Dialog):
        on_dialog_actions_complete.set_result(await dialog.dismiss())

    page.on("dialog", lambda dialog: asyncio.create_task(on_dialog(dialog)))
    assert await page.evaluate("prompt('question?')") is None
    await on_dialog_actions_complete


async def test_should_accept_the_confirm_prompt(page: Page, server):
    on_dialog_actions_complete: Future[None] = asyncio.Future()

    async def on_dialog(dialog: Dialog):
        on_dialog_actions_complete.set_result(await dialog.accept())

    page.on("dialog", lambda dialog: asyncio.create_task(on_dialog(dialog)))
    assert await page.evaluate("confirm('boolean?')") is True
    await on_dialog_actions_complete


async def test_should_dismiss_the_confirm_prompt(page: Page, server):
    on_dialog_actions_complete: Future[None] = asyncio.Future()

    async def on_dialog(dialog: Dialog):
        on_dialog_actions_complete.set_result(await dialog.dismiss())

    page.on("dialog", lambda dialog: asyncio.create_task(on_dialog(dialog)))
    assert await page.evaluate("confirm('boolean?')") is False
    await on_dialog_actions_complete


# TODO: Logger support not yet here
# //   it.fail(CHANNEL)('should log prompt actions', async({browser}) => {
# //     const messages = [];
# //     const context = await browser.newContext({
# //       logger: {
# //         isEnabled: () => true,
# //         log: (name, severity, message) => messages.push(message),
# //       }
# //     });
# //     const page = await context.newPage();
# //     const promise = page.evaluate(() => confirm('01234567890123456789012345678901234567890123456789012345678901234567890123456789'));
# //     const dialog = await page.waitForEvent('dialog');
# //     expect(messages.join()).toContain('confirm "0123456789012345678901234567890123456789012345678…" was shown');
# //     await dialog.accept('123');
# //     await promise;
# //     expect(messages.join()).toContain('confirm "0123456789012345678901234567890123456789012345678…" was accepted');
# //     await context.close();
# //   });


@pytest.mark.skip_browser("webkit")
async def test_should_be_able_to_close_context_with_open_alert(browser):
    context = await browser.newContext()
    page = await context.newPage()
    alertFuture = asyncio.create_task(page.waitForEvent("dialog"))
    await page.evaluate("() => setTimeout(() => alert('hello'), 0)", None)
    await alertFuture
    await context.close()
