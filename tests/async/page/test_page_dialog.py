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

"""Port of tests/page/page-dialog.spec.ts."""


import time
from typing import Any, Callable, List, Optional

from playwright.async_api import Dialog, Error, Page


async def poll_until_equal(
    page: Page, actual: Callable[[], Any], expected: Any, timeout: float = 5000
) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    while actual() != expected and time.monotonic() < deadline:
        await page.wait_for_timeout(100)
    assert actual() == expected


async def test_DI_001_should_fire(page: Page) -> None:
    dialogs: List[Dialog] = []

    async def on_dialog(dialog: Dialog) -> None:
        dialogs.append(dialog)
        await dialog.accept()

    page.on("dialog", on_dialog)
    await page.evaluate("() => alert('yo')")
    assert len(dialogs) == 1
    assert dialogs[0].type == "alert"
    assert dialogs[0].default_value == ""
    assert dialogs[0].message == "yo"


async def test_DI_002_should_fire_dialogclosed_when_dialog_is_accepted(
    page: Page,
) -> None:
    closed: List[Dialog] = []
    page.on("dialogclosed", lambda dialog: closed.append(dialog))
    opened: Optional[Dialog] = None

    async def on_dialog(dialog: Dialog) -> None:
        nonlocal opened
        opened = dialog
        await dialog.accept()

    page.on("dialog", on_dialog)
    await page.evaluate("() => alert('yo')")
    await poll_until_equal(page, lambda: len(closed), 1)
    assert closed[0] == opened
    # Perform some roundtrips to ensure the event does not fire twice.
    await page.evaluate("() => 1")
    await page.evaluate("() => 1")
    assert len(closed) == 1


async def test_DI_003_should_fire_dialogclosed_when_dialog_is_dismissed(
    page: Page,
) -> None:
    async with page.expect_event("dialogclosed") as closed_info:
        page.on("dialog", lambda dialog: dialog.dismiss())
        await page.evaluate("() => confirm('boolean?')")
    dialog = await closed_info.value
    assert dialog.type == "confirm"
    assert dialog.message == "boolean?"


async def test_DI_004_should_fire_dialogclosed_for_auto_dismissed_dialogs(
    page: Page,
) -> None:
    async with page.expect_event("dialogclosed") as closed_info:
        await page.evaluate("() => alert('yo')")
    dialog = await closed_info.value
    assert dialog.message == "yo"


async def test_DI_005_should_allow_accepting_prompts_smoke(page: Page) -> None:
    dialogs: List[Dialog] = []

    async def on_dialog(dialog: Dialog) -> None:
        dialogs.append(dialog)
        await dialog.accept("answer!")

    page.on("dialog", on_dialog)
    result = await page.evaluate("() => prompt('question?', 'yes.')")
    assert len(dialogs) == 1
    assert dialogs[0].type == "prompt"
    assert dialogs[0].default_value == "yes."
    assert dialogs[0].message == "question?"
    assert result == "answer!"


async def test_DI_006_should_dismiss_the_prompt(page: Page) -> None:
    page.on("dialog", lambda dialog: dialog.dismiss())
    result = await page.evaluate("() => prompt('question?')")
    assert result is None


async def test_DI_007_should_accept_the_confirm_prompt(page: Page) -> None:
    page.on("dialog", lambda dialog: dialog.accept())
    result = await page.evaluate("() => confirm('boolean?')")
    assert result is True


async def test_DI_008_should_dismiss_the_confirm_prompt(page: Page) -> None:
    page.on("dialog", lambda dialog: dialog.dismiss())
    result = await page.evaluate("() => confirm('boolean?')")
    assert result is False


async def test_DI_009_should_be_able_to_close_context_with_open_alert(
    page: Page,
) -> None:
    async with page.expect_event("dialog"):
        await page.evaluate(
            """() => {
    window.builtins.setTimeout(() => alert('hello'), 0);
  }"""
        )


async def test_DI_010_should_handle_multiple_alerts(page: Page) -> None:
    async def on_dialog(dialog: Dialog) -> None:
        try:
            await dialog.accept()
        except Error:
            pass

    page.on("dialog", on_dialog)
    await page.set_content(
        """
    <p>Hello World</p>
    <script>
      alert('Please dismiss this dialog');
      alert('Please dismiss this dialog');
      alert('Please dismiss this dialog');
    </script>
  """
    )
    assert await page.text_content("p") == "Hello World"


async def test_DI_011_should_handle_multiple_confirms(page: Page) -> None:
    async def on_dialog(dialog: Dialog) -> None:
        try:
            await dialog.accept()
        except Error:
            pass

    page.on("dialog", on_dialog)
    await page.set_content(
        """
    <p>Hello World</p>
    <script>
      confirm('Please confirm me?');
      confirm('Please confirm me?');
      confirm('Please confirm me?');
    </script>
  """
    )
    assert await page.text_content("p") == "Hello World"


async def test_DI_012_should_auto_dismiss_the_prompt_without_listeners(
    page: Page,
) -> None:
    result = await page.evaluate("() => prompt('question?')")
    assert result is None


async def test_DI_013_should_auto_dismiss_the_alert_without_listeners(
    page: Page,
) -> None:
    await page.set_content(
        '<div onclick="window.alert(123); window._clicked=true">Click me</div>'
    )
    await page.click("div")
    assert await page.evaluate("window._clicked") is True
