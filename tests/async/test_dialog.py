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


async def test_should_be_able_to_close_context_with_open_alert(browser):
    context = await browser.new_context()
    page = await context.new_page()
    async with page.expect_event("dialog"):
        await page.evaluate("() => setTimeout(() => alert('hello'), 0)", None)
    await context.close()


async def test_should_auto_dismiss_the_prompt_without_listeners(page):
    result = await page.evaluate('() => prompt("question?")')
    assert not result


async def test_should_auto_dismiss_the_alert_without_listeners(page):
    await page.set_content(
        '<div onclick="window.alert(123); window._clicked=true">Click me</div>'
    )
    await page.click("div")
    assert await page.evaluate('"window._clicked"')
