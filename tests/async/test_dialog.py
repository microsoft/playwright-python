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

import pytest

from playwright.async_api import Dialog, Page


async def test_should_fire(page: Page, server):
    result = []

    async def on_dialog(dialog: Dialog):
        result.append(True)
        assert dialog.type == "alert"
        assert dialog.default_value == ""
        assert dialog.message == "yo"
        await dialog.accept()

    page.on("dialog", on_dialog)
    await page.evaluate("alert('yo')")
    assert result


async def test_should_allow_accepting_prompts(page: Page, server):
    result = []

    async def on_dialog(dialog: Dialog):
        result.append(True)
        assert dialog.type == "prompt"
        assert dialog.default_value == "yes."
        assert dialog.message == "question?"
        await dialog.accept("answer!")

    page.on("dialog", on_dialog)
    assert await page.evaluate("prompt('question?', 'yes.')") == "answer!"
    assert result


async def test_should_dismiss_the_prompt(page: Page, server):
    result = []

    async def on_dialog(dialog: Dialog):
        result.append(True)
        await dialog.dismiss()

    page.on("dialog", on_dialog)
    assert await page.evaluate("prompt('question?')") is None
    assert result


async def test_should_accept_the_confirm_prompt(page: Page, server):
    result = []

    async def on_dialog(dialog: Dialog):
        result.append(True)
        await dialog.accept()

    page.on("dialog", on_dialog)
    assert await page.evaluate("confirm('boolean?')") is True
    assert result


async def test_should_dismiss_the_confirm_prompt(page: Page, server):
    result = []

    async def on_dialog(dialog: Dialog):
        result.append(True)
        await dialog.dismiss()

    page.on("dialog", on_dialog)
    assert await page.evaluate("confirm('boolean?')") is False
    assert result


# TODO: Logger support not yet here
# //   it.fail(CHANNEL)('should log prompt actions', async({browser}) => {
# //     const messages = [];
# //     const context = await browser.new_context({
# //       logger: {
# //         isEnabled: () => true,
# //         log: (name, severity, message) => messages.push(message),
# //       }
# //     });
# //     const page = await context.new_page();
# //     const promise = page.evaluate(() => confirm('01234567890123456789012345678901234567890123456789012345678901234567890123456789'));
# //     const dialog = await page.wait_for_event('dialog');
# //     expect(messages.join()).toContain('confirm "0123456789012345678901234567890123456789012345678…" was shown');
# //     await dialog.accept('123');
# //     await promise;
# //     expect(messages.join()).toContain('confirm "0123456789012345678901234567890123456789012345678…" was accepted');
# //     await context.close();
# //   });


@pytest.mark.skip_browser("webkit")
async def test_should_be_able_to_close_context_with_open_alert(browser):
    context = await browser.new_context()
    page = await context.new_page()
    alertFuture = asyncio.create_task(page.wait_for_event("dialog"))
    await page.evaluate("() => setTimeout(() => alert('hello'), 0)", None)
    await alertFuture
    await context.close()
