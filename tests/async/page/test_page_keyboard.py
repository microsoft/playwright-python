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

"""Port of tests/page/page-keyboard.spec.ts."""

import time
from typing import Any, Awaitable, Callable, Optional

import pytest

from playwright.async_api import Error, JSHandle, Page, expect
from tests.server import Server

from ..utils import Utils


async def poll_until_equal(
    page: Page,
    actual: Callable[[], Awaitable[Any]],
    expected: Any,
    timeout: float = 5000,
) -> None:
    """Port of `await expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = await actual()
    while value != expected and time.monotonic() < deadline:
        await page.wait_for_timeout(100)
        value = await actual()
    assert value == expected


async def capture_last_keydown(page: Page) -> JSHandle:
    return await page.evaluate_handle(
        """() => {
        const lastEvent = {
          repeat: false,
          location: -1,
          code: '',
          key: '',
          metaKey: false,
          keyIdentifier: 'unsupported'
        };
        document.addEventListener('keydown', e => {
          lastEvent.repeat = e.repeat;
          lastEvent.location = e.location;
          lastEvent.key = e.key;
          lastEvent.code = e.code;
          lastEvent.metaKey = e.metaKey;
          lastEvent.keyIdentifier = 'keyIdentifier' in e && typeof e['keyIdentifier'] === 'string' && e['keyIdentifier'];
        }, true);
        return lastEvent;
      }"""
    )


async def test_KB_001_should_type_into_a_textarea_smoke(page: Page) -> None:
    await page.evaluate(
        """() => {
        const textarea = document.createElement('textarea');
        document.body.appendChild(textarea);
        textarea.focus();
      }"""
    )
    text = "Hello world. I am the text that was typed!"
    await page.keyboard.type(text)
    assert await page.evaluate("() => document.querySelector('textarea').value") == text


async def test_KB_002_should_move_with_the_arrow_keys(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.type("textarea", "Hello World!")
    assert (
        await page.evaluate("() => document.querySelector('textarea').value")
        == "Hello World!"
    )
    for _ in range(len("World!")):
        await page.keyboard.press("ArrowLeft")
    await page.keyboard.type("inserted ")
    assert (
        await page.evaluate("() => document.querySelector('textarea').value")
        == "Hello inserted World!"
    )
    await page.keyboard.down("Shift")
    for _ in range(len("inserted ")):
        await page.keyboard.press("ArrowLeft")
    await page.keyboard.up("Shift")
    await page.keyboard.press("Backspace")
    assert (
        await page.evaluate("() => document.querySelector('textarea').value")
        == "Hello World!"
    )


async def test_KB_003_should_send_a_character_with_element_handle_press(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    assert textarea
    await textarea.press("a")
    assert await page.evaluate("() => document.querySelector('textarea').value") == "a"

    await page.evaluate(
        "() => window.addEventListener('keydown', e => e.preventDefault(), true)"
    )

    await textarea.press("b")
    assert await page.evaluate("() => document.querySelector('textarea').value") == "a"


async def test_KB_004_should_send_a_character_with_insert_text(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    await page.keyboard.insert_text("嗨")
    assert await page.evaluate("() => document.querySelector('textarea').value") == "嗨"
    await page.evaluate(
        "() => window.addEventListener('keydown', e => e.preventDefault(), true)"
    )
    await page.keyboard.insert_text("a")
    assert (
        await page.evaluate("() => document.querySelector('textarea').value") == "嗨a"
    )


async def test_KB_005_should_not_type_text_with_alt_modifier(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/42928
    await page.set_content("<input><textarea></textarea><div contenteditable></div>")
    for locator in [
        page.locator("input"),
        page.locator("textarea"),
        page.locator("div"),
    ]:
        await locator.press("Alt+KeyA")
        await locator.press("Alt+Digit1")
        await locator.press("Alt+Shift+KeyA")
        await page.keyboard.down("Alt")
        await page.keyboard.press("b")
        await page.keyboard.up("Alt")
        await locator.press("c")
    await expect(page.locator("input")).to_have_value("c")
    await expect(page.locator("textarea")).to_have_value("c")
    await expect(page.locator("div")).to_have_text("c")


async def test_KB_006_insert_text_should_only_emit_input_event(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    page.on("console", lambda m: print(m.text))
    events = await page.evaluate_handle(
        """() => {
        const events = [];
        document.addEventListener('keydown', e => events.push(e.type));
        document.addEventListener('keyup', e => events.push(e.type));
        document.addEventListener('keypress', e => events.push(e.type));
        document.addEventListener('input', e => events.push(e.type));
        return events;
      }"""
    )
    await page.keyboard.insert_text("hello world")
    assert await events.json_value() == ["input"]


async def test_KB_007_should_emit_keydown_keypress_text_input_and_input_when_typing_a_character(
    page: Page,
) -> None:
    await page.set_content("<input>")
    events = await page.evaluate_handle(
        """() => {
        const events = [];
        for (const type of ['keydown', 'keypress', 'textInput', 'input', 'keyup'])
          document.querySelector('input').addEventListener(type, () => events.push(type));
        return events;
      }"""
    )
    await page.focus("input")
    await page.keyboard.press("f")
    assert await events.json_value() == [
        "keydown",
        "keypress",
        "textInput",
        "input",
        "keyup",
    ]


async def test_KB_008_should_dispatch_key_events_in_separate_tasks(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("Firefox/Juggler dispatches keydown and keypress in the same task")
    await page.set_content("<input>")
    log = await page.evaluate_handle(
        """() => {
        const log = [];
        const input = document.querySelector('input');
        for (const type of ['keydown', 'keypress'])
          input.addEventListener(type, () => { log.push(type); queueMicrotask(() => log.push('microtask-' + type)); });
        input.focus();
        return log;
      }"""
    )
    await page.keyboard.press("a")
    # A microtask scheduled in the keydown handler must run before keypress,
    # proving each event is delivered in its own task rather than synchronously.
    assert await log.json_value() == [
        "keydown",
        "microtask-keydown",
        "keypress",
        "microtask-keypress",
    ]


async def test_KB_009_should_report_shift_key(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    code_for_key = {"Shift": 16, "Alt": 18, "Control": 17}
    for modifier_key in code_for_key:
        await keyboard.down(modifier_key)
        assert (
            await page.evaluate("getResult()")
            == "Keydown: "
            + modifier_key
            + " "
            + modifier_key
            + "Left LEFT ["
            + modifier_key
            + "]"
        )
        await keyboard.down("!")
        # Shift+! will generate a keypress
        if modifier_key == "Shift":
            assert (
                await page.evaluate("getResult()")
                == "Keydown: ! Digit1 STANDARD ["
                + modifier_key
                + "]\nKeypress: ! Digit1 STANDARD 33 ["
                + modifier_key
                + "]"
            )
        else:
            assert (
                await page.evaluate("getResult()")
                == "Keydown: ! Digit1 STANDARD [" + modifier_key + "]"
            )

        await keyboard.up("!")
        assert (
            await page.evaluate("getResult()")
            == "Keyup: ! Digit1 STANDARD [" + modifier_key + "]"
        )
        await keyboard.up(modifier_key)
        assert (
            await page.evaluate("getResult()")
            == "Keyup: " + modifier_key + " " + modifier_key + "Left LEFT []"
        )


async def test_KB_010_should_report_multiple_modifiers(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    await keyboard.down("Control")
    assert (
        await page.evaluate("getResult()")
        == "Keydown: Control ControlLeft LEFT [Control]"
    )
    await keyboard.down("Alt")
    assert (
        await page.evaluate("getResult()") == "Keydown: Alt AltLeft LEFT [Alt Control]"
    )
    await keyboard.down(";")
    assert (
        await page.evaluate("getResult()")
        == "Keydown: ; Semicolon STANDARD [Alt Control]"
    )
    await keyboard.up(";")
    assert (
        await page.evaluate("getResult()")
        == "Keyup: ; Semicolon STANDARD [Alt Control]"
    )
    await keyboard.up("Control")
    assert await page.evaluate("getResult()") == "Keyup: Control ControlLeft LEFT [Alt]"
    await keyboard.up("Alt")
    assert await page.evaluate("getResult()") == "Keyup: Alt AltLeft LEFT []"


async def test_KB_011_should_send_proper_codes_while_typing(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.type("!")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: ! Digit1 STANDARD []",
            "Keypress: ! Digit1 STANDARD 33 []",
            "Keyup: ! Digit1 STANDARD []",
        ]
    )
    await page.keyboard.type("^")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: ^ Digit6 STANDARD []",
            "Keypress: ^ Digit6 STANDARD 94 []",
            "Keyup: ^ Digit6 STANDARD []",
        ]
    )


async def test_KB_012_should_send_proper_codes_while_typing_with_shift(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    await keyboard.down("Shift")
    await page.keyboard.type("~")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: ~ Backquote STANDARD [Shift]",
            "Keypress: ~ Backquote STANDARD 126 [Shift]",
            "Keyup: ~ Backquote STANDARD [Shift]",
        ]
    )
    await keyboard.up("Shift")


async def test_KB_013_should_not_type_canceled_events(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    await page.evaluate(
        """() => {
        window.addEventListener('keydown', event => {
          event.stopPropagation();
          event.stopImmediatePropagation();
          if (event.key === 'l')
            event.preventDefault();
          if (event.key === 'o')
            event.preventDefault();
        }, false);
      }"""
    )
    await page.keyboard.type("Hello World!")
    assert await page.eval_on_selector("textarea", "textarea => textarea.value") == (
        "He Wrd!"
    )


async def test_KB_014_should_press_plus(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("+")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: + Equal STANDARD []",
            "Keypress: + Equal STANDARD 43 []",
            "Keyup: + Equal STANDARD []",
        ]
    )


async def test_KB_015_should_press_shift_plus(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Shift++")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: + Equal STANDARD [Shift]",
            "Keypress: + Equal STANDARD 43 [Shift]",
            "Keyup: + Equal STANDARD [Shift]",
            "Keyup: Shift ShiftLeft LEFT []",
        ]
    )


async def test_KB_016_should_support_plus_separated_modifiers(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Shift+~")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: ~ Backquote STANDARD [Shift]",
            "Keypress: ~ Backquote STANDARD 126 [Shift]",
            "Keyup: ~ Backquote STANDARD [Shift]",
            "Keyup: Shift ShiftLeft LEFT []",
        ]
    )


async def test_KB_017_should_support_multiple_plus_separated_modifiers(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Control+Shift+~")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Control ControlLeft LEFT [Control]",
            "Keydown: Shift ShiftLeft LEFT [Control Shift]",
            "Keydown: ~ Backquote STANDARD [Control Shift]",
            "Keyup: ~ Backquote STANDARD [Control Shift]",
            "Keyup: Shift ShiftLeft LEFT [Control]",
            "Keyup: Control ControlLeft LEFT []",
        ]
    )


async def test_KB_018_should_shift_raw_codes(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Shift+Digit3")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: # Digit3 STANDARD [Shift]",
            "Keypress: # Digit3 STANDARD 35 [Shift]",
            "Keyup: # Digit3 STANDARD [Shift]",
            "Keyup: Shift ShiftLeft LEFT []",
        ]
    )


async def test_KB_019_should_specify_repeat_property(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    last_event = await capture_last_keydown(page)
    await page.keyboard.down("a")
    assert await last_event.evaluate("e => e.repeat") is False
    await page.keyboard.press("a")
    assert await last_event.evaluate("e => e.repeat") is True

    await page.keyboard.down("b")
    assert await last_event.evaluate("e => e.repeat") is False
    await page.keyboard.down("b")
    assert await last_event.evaluate("e => e.repeat") is True

    await page.keyboard.up("a")
    await page.keyboard.down("a")
    assert await last_event.evaluate("e => e.repeat") is False


async def test_KB_020_should_type_all_kinds_of_characters(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    text = "This text goes onto two lines.\nThis character is 嗨."
    await page.keyboard.type(text)
    assert await page.eval_on_selector("textarea", "t => t.value") == text


async def test_KB_021_should_specify_location(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    last_event = await capture_last_keydown(page)
    textarea = await page.query_selector("textarea")
    assert textarea

    await textarea.press("Digit5")
    assert await last_event.evaluate("e => e.location") == 0
    assert await last_event.evaluate("e => e.key") == "5"
    assert await last_event.evaluate("e => e.code") == "Digit5"

    await textarea.press("ControlLeft")
    assert await last_event.evaluate("e => e.location") == 1
    assert await last_event.evaluate("e => e.key") == "Control"
    assert await last_event.evaluate("e => e.code") == "ControlLeft"

    await textarea.press("ControlRight")
    assert await last_event.evaluate("e => e.location") == 2
    assert await last_event.evaluate("e => e.key") == "Control"
    assert await last_event.evaluate("e => e.code") == "ControlRight"

    await textarea.press("NumpadSubtract")
    assert await last_event.evaluate("e => e.location") == 3
    assert await last_event.evaluate("e => e.key") == "-"
    assert await last_event.evaluate("e => e.code") == "NumpadSubtract"


async def test_KB_022_should_specify_numpad_location_on_keyup(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("NumpadSubtract")
    assert await page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: - NumpadSubtract NUMPAD []",
            "Keypress: - NumpadSubtract NUMPAD 45 []",
            "Keyup: - NumpadSubtract NUMPAD []",
        ]
    )


async def test_KB_023_should_press_numpad_decimal_as_delete(page: Page) -> None:
    await page.set_content("<textarea></textarea>")
    last_event = await capture_last_keydown(page)
    textarea = page.locator("textarea")

    await textarea.press("NumpadDecimal")
    assert await last_event.evaluate("e => e.key") == "Delete"
    assert await last_event.evaluate("e => e.code") == "NumpadDecimal"
    assert await last_event.evaluate("e => e.location") == 3
    await expect(textarea).to_have_value("")


async def test_KB_024_should_type_numpad_digits_with_shift(page: Page) -> None:
    await page.set_content("<textarea></textarea>")
    textarea = page.locator("textarea")
    await textarea.press("Shift+Numpad1")
    await textarea.press("Shift+NumpadDecimal")
    await textarea.press("Shift+Numpad9")
    await expect(textarea).to_have_value("1.9")


async def test_KB_025_should_press_enter(page: Page, server: Server) -> None:
    await page.set_content("<textarea></textarea>")
    await page.focus("textarea")
    last_event_handle = await capture_last_keydown(page)

    async def test_enter_key(key: str, expected_key: str, expected_code: str) -> None:
        await page.keyboard.press(key)
        last_event = await last_event_handle.json_value()
        assert last_event["key"] == expected_key  # had the wrong key
        assert last_event["code"] == expected_code  # had the wrong code
        value = await page.eval_on_selector("textarea", "t => t.value")
        assert value == "\n"  # failed to create a newline
        await page.eval_on_selector("textarea", "t => t.value = ''")

    await test_enter_key("Enter", "Enter", "Enter")
    await test_enter_key("NumpadEnter", "Enter", "NumpadEnter")
    await test_enter_key("\n", "Enter", "Enter")
    await test_enter_key("\r", "Enter", "Enter")


async def test_KB_026_should_press_audio_and_media_control_keys(
    page: Page, browser_name: str
) -> None:
    await page.set_content("<input autofocus>")
    await page.focus("input")
    last_event = await capture_last_keydown(page)
    media_keys = [
        {
            "key": "AudioVolumeMute",
            "code": "VolumeMute" if browser_name == "firefox" else "AudioVolumeMute",
        },
        {
            "key": "AudioVolumeDown",
            "code": "VolumeDown" if browser_name == "firefox" else "AudioVolumeDown",
        },
        {
            "key": "AudioVolumeUp",
            "code": "VolumeUp" if browser_name == "firefox" else "AudioVolumeUp",
        },
        {"key": "MediaTrackNext", "code": "MediaTrackNext"},
        {"key": "MediaTrackPrevious", "code": "MediaTrackPrevious"},
        {"key": "MediaPlayPause", "code": "MediaPlayPause"},
    ]

    for media_key in media_keys:
        await page.keyboard.press(media_key["key"])
        assert await last_event.evaluate("e => e.key") == media_key["key"]
        assert await last_event.evaluate("e => e.code") == media_key["code"]
        assert await last_event.evaluate("e => e.location") == 0


async def test_KB_027_should_throw_on_unknown_keys(page: Page, server: Server) -> None:
    with pytest.raises(Error) as exc_info:
        await page.keyboard.press("NotARealKey")
    assert 'Unknown key: "NotARealKey"' in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        await page.keyboard.press("ё")
    assert 'Unknown key: "ё"' in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        await page.keyboard.press("😊")
    assert 'Unknown key: "😊"' in exc_info.value.message


async def test_KB_028_should_type_emoji(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.type("textarea", "👹 Tokyo street Japan 🇯🇵")
    assert (
        await page.eval_on_selector("textarea", "textarea => textarea.value")
        == "👹 Tokyo street Japan 🇯🇵"
    )


async def test_KB_029_should_type_emoji_into_an_iframe(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "emoji-test", server.PREFIX + "/input/textarea.html")
    frame = page.frames[1]
    textarea = await frame.query_selector("textarea")
    assert textarea
    await textarea.type("👹 Tokyo street Japan 🇯🇵")
    assert (
        await frame.eval_on_selector("textarea", "textarea => textarea.value")
        == "👹 Tokyo street Japan 🇯🇵"
    )


async def test_KB_030_should_handle_select_all(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    assert textarea
    await textarea.type("some text")
    await page.keyboard.down("ControlOrMeta")
    await page.keyboard.press("a")
    await page.keyboard.up("ControlOrMeta")
    await page.keyboard.press("Backspace")
    assert await page.eval_on_selector("textarea", "textarea => textarea.value") == ""


async def test_KB_031_pressing_meta_should_not_result_in_any_text_insertion_on_any_platform(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28495
    await page.set_content('<input type="text" value="hello world">')
    input = page.locator("input")
    await expect(input).to_have_value("hello world")
    await input.focus()
    await page.keyboard.press("Meta")
    await expect(input).to_have_value("hello world")


async def test_KB_032_should_be_able_to_prevent_select_all(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    assert textarea
    await textarea.type("some text")
    await page.eval_on_selector(
        "textarea",
        """textarea => {
        textarea.addEventListener('keydown', event => {
          if (event.key === 'a' && (event.metaKey || event.ctrlKey))
            event.preventDefault();
        }, false);
      }""",
    )
    await page.keyboard.down("ControlOrMeta")
    await page.keyboard.press("a")
    await page.keyboard.up("ControlOrMeta")
    await page.keyboard.press("Backspace")
    assert (
        await page.eval_on_selector("textarea", "textarea => textarea.value")
        == "some tex"
    )


async def test_KB_033_should_support_mac_os_shortcuts(
    page: Page, server: Server, platform: str, browser_name: str
) -> None:
    if platform != "darwin":
        pytest.skip("macOS only")
    # @see https://github.com/microsoft/playwright/issues/5721
    if browser_name == "firefox" and platform == "darwin":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/5721")

    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    assert textarea
    await textarea.type("some text")
    # select one word backwards
    await page.keyboard.press("Shift+Control+Alt+KeyB")
    await page.keyboard.press("Backspace")
    assert (
        await page.eval_on_selector("textarea", "textarea => textarea.value") == "some "
    )


async def test_KB_034_should_press_the_meta_key(page: Page) -> None:
    last_event = await capture_last_keydown(page)
    await page.keyboard.press("Meta")
    value = await last_event.json_value()
    assert value["key"] == "Meta"
    assert value["code"] == "MetaLeft"
    assert value["metaKey"] is True


async def test_KB_035_should_work_with_keyboard_events_with_empty_html(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    last_event = await capture_last_keydown(page)
    await page.keyboard.press("a")
    assert await last_event.evaluate("l => l.key") == "a"


async def test_KB_036_should_work_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    last_event = await capture_last_keydown(page)
    await page.keyboard.press("a")
    assert await last_event.evaluate("l => l.key") == "a"


async def test_KB_037_should_expose_key_identifier_in_webkit(
    page: Page, browser_name: str
) -> None:
    if browser_name != "webkit":
        pytest.skip(
            "event.keyIdentifier has been removed from all browsers except WebKit"
        )

    last_event = await capture_last_keydown(page)
    key_map = {
        "ArrowUp": "Up",
        "ArrowDown": "Down",
        "ArrowLeft": "Left",
        "ArrowRight": "Right",
        "Backspace": "U+0008",
        "Tab": "U+0009",
        "Delete": "U+007F",
        "a": "U+0041",
        "b": "U+0042",
        "F12": "F12",
    }
    for key, key_identifier in key_map.items():
        await page.keyboard.press(key)
        assert await last_event.evaluate("e => e.keyIdentifier") == key_identifier


async def test_KB_038_should_scroll_with_page_down(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    # A click is required for WebKit to send the event into the body.
    await page.click("body")
    await page.keyboard.press("PageDown")
    # We can't wait for the scroll to finish, so just wait for it to start.
    await page.wait_for_function("() => scrollY > 0")


async def test_KB_039_should_move_around_the_selection_in_a_contenteditable(
    page: Page, is_mac: bool
) -> None:
    await page.set_content("<div contenteditable></div>")
    await page.focus("div")
    modifier = "Alt" if is_mac else "Control"
    await page.keyboard.type("Hello World")
    await page.keyboard.down(modifier)
    await page.keyboard.down("Shift")
    await page.keyboard.press("ArrowLeft")
    await page.keyboard.up("Shift")
    await page.keyboard.up(modifier)
    assert await page.evaluate("() => window.getSelection().toString()") == "World"


async def test_KB_040_should_move_to_the_start_of_the_document(
    page: Page, is_mac: bool
) -> None:
    if not is_mac:
        pytest.skip("macOS only")
    await page.set_content("<div contenteditable></div>")
    await page.focus("div")
    await page.keyboard.type("1\n2\n3\n")
    await page.keyboard.press("Shift+Meta+ArrowUp")
    assert await page.evaluate("() => window.getSelection().toString()") == "1\n2\n3\n"


async def test_KB_041_should_dispatch_a_click_event_on_a_button_when_space_gets_pressed(
    page: Page,
) -> None:
    await page.set_content('<button type="button">a11y</button>')
    actual = await page.evaluate_handle(
        """() => {
        const actual = { clicked: false };
        document.querySelector('button').addEventListener('click', () => (actual.clicked = true));
        return actual;
      }"""
    )
    await page.focus("button")
    await page.keyboard.press("Space")
    assert (await actual.json_value())["clicked"] is True


async def test_KB_042_should_dispatch_a_click_event_on_a_button_when_enter_gets_pressed(
    page: Page,
) -> None:
    await page.set_content('<button type="button">a11y</button>')
    actual = await page.evaluate_handle(
        """() => {
        const actual = { clicked: false };
        document.querySelector('button').addEventListener('click', () => (actual.clicked = true));
        return actual;
      }"""
    )
    await page.focus("button")
    await page.keyboard.press("Enter")
    assert (await actual.json_value())["clicked"] is True


async def test_KB_043_should_support_simple_copy_pasting(page: Page) -> None:
    await page.set_content("<div contenteditable>123</div>")
    await page.focus("div")
    await page.keyboard.press("ControlOrMeta+KeyA")
    await page.keyboard.press("ControlOrMeta+KeyC")
    await page.keyboard.press("ControlOrMeta+KeyV")
    await page.keyboard.press("ControlOrMeta+KeyV")
    assert (
        await page.evaluate("() => document.querySelector('div').textContent")
        == "123123"
    )


async def test_KB_044_should_support_simple_cut_pasting(page: Page) -> None:
    await page.set_content("<div contenteditable>123</div>")
    await page.focus("div")
    await page.keyboard.press("ControlOrMeta+KeyA")
    await page.keyboard.press("ControlOrMeta+KeyX")
    await page.keyboard.press("ControlOrMeta+KeyV")
    await page.keyboard.press("ControlOrMeta+KeyV")
    assert (
        await page.evaluate("() => document.querySelector('div').textContent")
        == "123123"
    )


async def test_KB_045_should_support_undo_redo(
    page: Page, browser_name: str, is_linux: bool, browser_channel: Optional[str]
) -> None:
    if (browser_name == "webkit" and is_linux) or browser_channel == "webkit-wsl":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/12000")
    await page.set_content("<div contenteditable></div>")
    div = page.locator("div")
    await expect(div).to_have_text("")
    await div.type("123")
    await expect(div).to_have_text("123")
    await page.keyboard.press("ControlOrMeta+KeyZ")
    await expect(div).to_have_text("")
    await page.keyboard.press("Shift+ControlOrMeta+KeyZ")
    await expect(div).to_have_text("123")


async def test_KB_046_should_type_repeatedly_in_contenteditable_in_shadow_dom(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/12941
    await page.set_content(
        """
    <html>
      <body>
        <shadow-element></shadow-element>
        <script>
          customElements.define('shadow-element', class extends HTMLElement {
            constructor() {
              super();
              this.attachShadow({ mode: 'open' });
            }

            connectedCallback() {
              this.shadowRoot.innerHTML = `
                <style>
                  .editor { padding: 1rem; margin: 1rem; border: 1px solid #ccc; }
                </style>
                <div class=editor contenteditable id=foo></div>
                <hr>
                <section>
                  <div class=editor contenteditable id=bar></div>
                </section>
              `;
            }
          });
        </script>
      </body>
    </html>
  """
    )

    editor = page.locator("shadow-element > .editor").first
    await editor.type("This is the first box.")

    section_editor = page.locator("section .editor")
    await section_editor.type("This is the second box.")

    assert await editor.text_content() == "This is the first box."
    assert await section_editor.text_content() == "This is the second box."


async def test_KB_047_should_type_repeatedly_in_contenteditable_in_shadow_dom_with_nested_elements(
    page: Page,
) -> None:
    await page.set_content(
        """
    <html>
      <body>
        <shadow-element></shadow-element>
        <script>
          customElements.define('shadow-element', class extends HTMLElement {
            constructor() {
              super();
              this.attachShadow({ mode: 'open' });
            }

            connectedCallback() {
              this.shadowRoot.innerHTML = `
                <style>
                  .editor { padding: 1rem; margin: 1rem; border: 1px solid #ccc; }
                </style>
                <div class=editor contenteditable id=foo><p>hello</p></div>
                <hr>
                <section>
                  <div class=editor contenteditable id=bar><p>world</p></div>
                </section>
              `;
            }
          });
        </script>
      </body>
    </html>
  """
    )

    editor = page.locator("shadow-element > .editor").first
    await editor.type("This is the first box: ")

    section_editor = page.locator("section .editor")
    await section_editor.type("This is the second box: ")

    assert await editor.text_content() == "This is the first box: hello"
    assert await section_editor.text_content() == "This is the second box: world"


async def test_KB_048_should_type_repeatedly_in_input_in_shadow_dom(
    page: Page,
) -> None:
    await page.set_content(
        """
    <html>
      <body>
        <shadow-element></shadow-element>
        <script>
          customElements.define('shadow-element', class extends HTMLElement {
            constructor() {
              super();
              this.attachShadow({ mode: 'open' });
            }

            connectedCallback() {
              this.shadowRoot.innerHTML = `
                <style>
                  .editor { padding: 1rem; margin: 1rem; border: 1px solid #ccc; }
                </style>
                <input class=editor id=foo>
                <hr>
                <section>
                  <input class=editor id=bar>
                </section>
              `;
            }
          });
        </script>
      </body>
    </html>
  """
    )

    editor = page.locator("shadow-element > .editor").first
    await editor.type("This is the first box.")

    section_editor = page.locator("section .editor")
    await section_editor.type("This is the second box.")

    assert await editor.input_value() == "This is the first box."
    assert await section_editor.input_value() == "This is the second box."


async def test_KB_049_type_to_non_focusable_element_should_maintain_old_focus(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div id="focusable" tabindex="0">focusable div</div>
    <div id="non-focusable-and-non-editable">non-editable, non-focusable</div>
  """
    )

    await page.locator("#focusable").focus()
    assert await page.evaluate("() => document.activeElement?.id") == "focusable"
    await page.locator("#non-focusable-and-non-editable").type("foo")
    assert await page.evaluate("() => document.activeElement?.id") == "focusable"


async def test_KB_050_should_dispatch_insert_text_after_context_menu_was_opened(
    server: Server, page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "chromium" and is_win:
        pytest.skip("context menu support is best-effort for Linux and MacOS")
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.evaluate(
        """() => {
        window['contextMenuPromise'] = new Promise(x => {
          window.addEventListener('contextmenu', x, false);
        });
      }"""
    )

    box = await page.locator("textarea").bounding_box()
    assert box
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    await page.mouse.click(cx, cy, button="right")
    await page.evaluate("() => window['contextMenuPromise']")

    await page.keyboard.insert_text("嗨")
    await poll_until_equal(page, lambda: page.locator("textarea").input_value(), "嗨")


async def test_KB_051_should_type_after_context_menu_was_opened(
    server: Server, page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "chromium" and is_win:
        pytest.skip("context menu support is best-effort for Linux and MacOS")
    await page.evaluate(
        """() => {
        window['keys'] = [];
        window.addEventListener('keydown', event => window['keys'].push(event.key));
        window['contextMenuPromise'] = new Promise(x => {
          window.addEventListener('contextmenu', x, false);
        });
      }"""
    )

    await page.mouse.move(100, 100)
    await page.mouse.down(button="right")
    await page.evaluate("() => window['contextMenuPromise']")

    await page.keyboard.down("ArrowDown")

    await poll_until_equal(page, lambda: page.evaluate("window.keys"), ["ArrowDown"])


async def test_KB_052_should_have_correct_keydown_keyup_order_when_pressing_escape_key(
    page: Page, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/27709
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Escape")
    assert (
        await page.evaluate("getResult()")
        == """
Keydown: Escape Escape STANDARD []
Keyup: Escape Escape STANDARD []
""".strip()
    )


async def test_KB_053_should_close_dialog_on_escape_key_press_in_contenteditable(
    page: Page, is_frozen_webkit: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/36727
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    await page.set_content(
        """
    <dialog>
      <div contenteditable>Edit Me</div>
    </dialog>
  """
    )

    dialog = page.locator("dialog")
    widget = dialog.locator("[contenteditable]")
    await dialog.evaluate("node => node.showModal()")
    await expect(dialog).to_have_js_property("open", True)
    await expect(widget).to_be_visible()

    await widget.press("Escape")
    await expect(dialog).to_have_js_property("open", False)
    await expect(widget).not_to_be_visible()
