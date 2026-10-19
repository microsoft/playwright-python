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
from typing import Any, Callable, Optional

import pytest

from playwright.sync_api import Error, JSHandle, Page, expect
from tests.server import Server

from ..utils import Utils


def poll_until_equal(
    page: Page,
    actual: Callable[[], Any],
    expected: Any,
    timeout: float = 5000,
) -> None:
    """Port of `expect.poll(actual).toEqual(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = actual()
    while value != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        value = actual()
    assert value == expected


def capture_last_keydown(page: Page) -> JSHandle:
    return page.evaluate_handle(
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


def test_KB_001_should_type_into_a_textarea_smoke(page: Page) -> None:
    page.evaluate(
        """() => {
        const textarea = document.createElement('textarea');
        document.body.appendChild(textarea);
        textarea.focus();
      }"""
    )
    text = "Hello world. I am the text that was typed!"
    page.keyboard.type(text)
    assert page.evaluate("() => document.querySelector('textarea').value") == text


def test_KB_002_should_move_with_the_arrow_keys(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.type("textarea", "Hello World!")
    assert (
        page.evaluate("() => document.querySelector('textarea').value")
        == "Hello World!"
    )
    for _ in range(len("World!")):
        page.keyboard.press("ArrowLeft")
    page.keyboard.type("inserted ")
    assert (
        page.evaluate("() => document.querySelector('textarea').value")
        == "Hello inserted World!"
    )
    page.keyboard.down("Shift")
    for _ in range(len("inserted ")):
        page.keyboard.press("ArrowLeft")
    page.keyboard.up("Shift")
    page.keyboard.press("Backspace")
    assert (
        page.evaluate("() => document.querySelector('textarea').value")
        == "Hello World!"
    )


def test_KB_003_should_send_a_character_with_element_handle_press(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.press("a")
    assert page.evaluate("() => document.querySelector('textarea').value") == "a"

    page.evaluate(
        "() => window.addEventListener('keydown', e => e.preventDefault(), true)"
    )

    textarea.press("b")
    assert page.evaluate("() => document.querySelector('textarea').value") == "a"


def test_KB_004_should_send_a_character_with_insert_text(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.focus("textarea")
    page.keyboard.insert_text("嗨")
    assert page.evaluate("() => document.querySelector('textarea').value") == "嗨"
    page.evaluate(
        "() => window.addEventListener('keydown', e => e.preventDefault(), true)"
    )
    page.keyboard.insert_text("a")
    assert page.evaluate("() => document.querySelector('textarea').value") == "嗨a"


def test_KB_005_should_not_type_text_with_alt_modifier(page: Page) -> None:
    # https://github.com/microsoft/playwright/issues/42928
    page.set_content("<input><textarea></textarea><div contenteditable></div>")
    for locator in [
        page.locator("input"),
        page.locator("textarea"),
        page.locator("div"),
    ]:
        locator.press("Alt+KeyA")
        locator.press("Alt+Digit1")
        locator.press("Alt+Shift+KeyA")
        page.keyboard.down("Alt")
        page.keyboard.press("b")
        page.keyboard.up("Alt")
        locator.press("c")
    expect(page.locator("input")).to_have_value("c")
    expect(page.locator("textarea")).to_have_value("c")
    expect(page.locator("div")).to_have_text("c")


def test_KB_006_insert_text_should_only_emit_input_event(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.focus("textarea")
    page.on("console", lambda m: print(m.text))
    events = page.evaluate_handle(
        """() => {
        const events = [];
        document.addEventListener('keydown', e => events.push(e.type));
        document.addEventListener('keyup', e => events.push(e.type));
        document.addEventListener('keypress', e => events.push(e.type));
        document.addEventListener('input', e => events.push(e.type));
        return events;
      }"""
    )
    page.keyboard.insert_text("hello world")
    assert events.json_value() == ["input"]


def test_KB_007_should_emit_keydown_keypress_text_input_and_input_when_typing_a_character(
    page: Page,
) -> None:
    page.set_content("<input>")
    events = page.evaluate_handle(
        """() => {
        const events = [];
        for (const type of ['keydown', 'keypress', 'textInput', 'input', 'keyup'])
          document.querySelector('input').addEventListener(type, () => events.push(type));
        return events;
      }"""
    )
    page.focus("input")
    page.keyboard.press("f")
    assert events.json_value() == [
        "keydown",
        "keypress",
        "textInput",
        "input",
        "keyup",
    ]


def test_KB_008_should_dispatch_key_events_in_separate_tasks(
    page: Page, browser_name: str
) -> None:
    if browser_name == "firefox":
        pytest.skip("Firefox/Juggler dispatches keydown and keypress in the same task")
    page.set_content("<input>")
    log = page.evaluate_handle(
        """() => {
        const log = [];
        const input = document.querySelector('input');
        for (const type of ['keydown', 'keypress'])
          input.addEventListener(type, () => { log.push(type); queueMicrotask(() => log.push('microtask-' + type)); });
        input.focus();
        return log;
      }"""
    )
    page.keyboard.press("a")
    # A microtask scheduled in the keydown handler must run before keypress,
    # proving each event is delivered in its own task rather than synchronously.
    assert log.json_value() == [
        "keydown",
        "microtask-keydown",
        "keypress",
        "microtask-keypress",
    ]


def test_KB_009_should_report_shift_key(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    code_for_key = {"Shift": 16, "Alt": 18, "Control": 17}
    for modifier_key in code_for_key:
        keyboard.down(modifier_key)
        assert (
            page.evaluate("getResult()")
            == "Keydown: "
            + modifier_key
            + " "
            + modifier_key
            + "Left LEFT ["
            + modifier_key
            + "]"
        )
        keyboard.down("!")
        # Shift+! will generate a keypress
        if modifier_key == "Shift":
            assert (
                page.evaluate("getResult()")
                == "Keydown: ! Digit1 STANDARD ["
                + modifier_key
                + "]\nKeypress: ! Digit1 STANDARD 33 ["
                + modifier_key
                + "]"
            )
        else:
            assert (
                page.evaluate("getResult()")
                == "Keydown: ! Digit1 STANDARD [" + modifier_key + "]"
            )

        keyboard.up("!")
        assert (
            page.evaluate("getResult()")
            == "Keyup: ! Digit1 STANDARD [" + modifier_key + "]"
        )
        keyboard.up(modifier_key)
        assert (
            page.evaluate("getResult()")
            == "Keyup: " + modifier_key + " " + modifier_key + "Left LEFT []"
        )


def test_KB_010_should_report_multiple_modifiers(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    keyboard.down("Control")
    assert page.evaluate("getResult()") == "Keydown: Control ControlLeft LEFT [Control]"
    keyboard.down("Alt")
    assert page.evaluate("getResult()") == "Keydown: Alt AltLeft LEFT [Alt Control]"
    keyboard.down(";")
    assert page.evaluate("getResult()") == "Keydown: ; Semicolon STANDARD [Alt Control]"
    keyboard.up(";")
    assert page.evaluate("getResult()") == "Keyup: ; Semicolon STANDARD [Alt Control]"
    keyboard.up("Control")
    assert page.evaluate("getResult()") == "Keyup: Control ControlLeft LEFT [Alt]"
    keyboard.up("Alt")
    assert page.evaluate("getResult()") == "Keyup: Alt AltLeft LEFT []"


def test_KB_011_should_send_proper_codes_while_typing(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.type("!")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: ! Digit1 STANDARD []",
            "Keypress: ! Digit1 STANDARD 33 []",
            "Keyup: ! Digit1 STANDARD []",
        ]
    )
    page.keyboard.type("^")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: ^ Digit6 STANDARD []",
            "Keypress: ^ Digit6 STANDARD 94 []",
            "Keyup: ^ Digit6 STANDARD []",
        ]
    )


def test_KB_012_should_send_proper_codes_while_typing_with_shift(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    keyboard.down("Shift")
    page.keyboard.type("~")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: ~ Backquote STANDARD [Shift]",
            "Keypress: ~ Backquote STANDARD 126 [Shift]",
            "Keyup: ~ Backquote STANDARD [Shift]",
        ]
    )
    keyboard.up("Shift")


def test_KB_013_should_not_type_canceled_events(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.focus("textarea")
    page.evaluate(
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
    page.keyboard.type("Hello World!")
    assert page.eval_on_selector("textarea", "textarea => textarea.value") == (
        "He Wrd!"
    )


def test_KB_014_should_press_plus(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("+")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: + Equal STANDARD []",
            "Keypress: + Equal STANDARD 43 []",
            "Keyup: + Equal STANDARD []",
        ]
    )


def test_KB_015_should_press_shift_plus(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("Shift++")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: + Equal STANDARD [Shift]",
            "Keypress: + Equal STANDARD 43 [Shift]",
            "Keyup: + Equal STANDARD [Shift]",
            "Keyup: Shift ShiftLeft LEFT []",
        ]
    )


def test_KB_016_should_support_plus_separated_modifiers(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("Shift+~")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: ~ Backquote STANDARD [Shift]",
            "Keypress: ~ Backquote STANDARD 126 [Shift]",
            "Keyup: ~ Backquote STANDARD [Shift]",
            "Keyup: Shift ShiftLeft LEFT []",
        ]
    )


def test_KB_017_should_support_multiple_plus_separated_modifiers(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("Control+Shift+~")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Control ControlLeft LEFT [Control]",
            "Keydown: Shift ShiftLeft LEFT [Control Shift]",
            "Keydown: ~ Backquote STANDARD [Control Shift]",
            "Keyup: ~ Backquote STANDARD [Control Shift]",
            "Keyup: Shift ShiftLeft LEFT [Control]",
            "Keyup: Control ControlLeft LEFT []",
        ]
    )


def test_KB_018_should_shift_raw_codes(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("Shift+Digit3")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft LEFT [Shift]",
            "Keydown: # Digit3 STANDARD [Shift]",
            "Keypress: # Digit3 STANDARD 35 [Shift]",
            "Keyup: # Digit3 STANDARD [Shift]",
            "Keyup: Shift ShiftLeft LEFT []",
        ]
    )


def test_KB_019_should_specify_repeat_property(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.focus("textarea")
    last_event = capture_last_keydown(page)
    page.keyboard.down("a")
    assert last_event.evaluate("e => e.repeat") is False
    page.keyboard.press("a")
    assert last_event.evaluate("e => e.repeat") is True

    page.keyboard.down("b")
    assert last_event.evaluate("e => e.repeat") is False
    page.keyboard.down("b")
    assert last_event.evaluate("e => e.repeat") is True

    page.keyboard.up("a")
    page.keyboard.down("a")
    assert last_event.evaluate("e => e.repeat") is False


def test_KB_020_should_type_all_kinds_of_characters(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.focus("textarea")
    text = "This text goes onto two lines.\nThis character is 嗨."
    page.keyboard.type(text)
    assert page.eval_on_selector("textarea", "t => t.value") == text


def test_KB_021_should_specify_location(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    last_event = capture_last_keydown(page)
    textarea = page.query_selector("textarea")
    assert textarea

    textarea.press("Digit5")
    assert last_event.evaluate("e => e.location") == 0
    assert last_event.evaluate("e => e.key") == "5"
    assert last_event.evaluate("e => e.code") == "Digit5"

    textarea.press("ControlLeft")
    assert last_event.evaluate("e => e.location") == 1
    assert last_event.evaluate("e => e.key") == "Control"
    assert last_event.evaluate("e => e.code") == "ControlLeft"

    textarea.press("ControlRight")
    assert last_event.evaluate("e => e.location") == 2
    assert last_event.evaluate("e => e.key") == "Control"
    assert last_event.evaluate("e => e.code") == "ControlRight"

    textarea.press("NumpadSubtract")
    assert last_event.evaluate("e => e.location") == 3
    assert last_event.evaluate("e => e.key") == "-"
    assert last_event.evaluate("e => e.code") == "NumpadSubtract"


def test_KB_022_should_specify_numpad_location_on_keyup(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("NumpadSubtract")
    assert page.evaluate("getResult()") == "\n".join(
        [
            "Keydown: - NumpadSubtract NUMPAD []",
            "Keypress: - NumpadSubtract NUMPAD 45 []",
            "Keyup: - NumpadSubtract NUMPAD []",
        ]
    )


def test_KB_023_should_press_numpad_decimal_as_delete(page: Page) -> None:
    page.set_content("<textarea></textarea>")
    last_event = capture_last_keydown(page)
    textarea = page.locator("textarea")

    textarea.press("NumpadDecimal")
    assert last_event.evaluate("e => e.key") == "Delete"
    assert last_event.evaluate("e => e.code") == "NumpadDecimal"
    assert last_event.evaluate("e => e.location") == 3
    expect(textarea).to_have_value("")


def test_KB_024_should_type_numpad_digits_with_shift(page: Page) -> None:
    page.set_content("<textarea></textarea>")
    textarea = page.locator("textarea")
    textarea.press("Shift+Numpad1")
    textarea.press("Shift+NumpadDecimal")
    textarea.press("Shift+Numpad9")
    expect(textarea).to_have_value("1.9")


def test_KB_025_should_press_enter(page: Page, server: Server) -> None:
    page.set_content("<textarea></textarea>")
    page.focus("textarea")
    last_event_handle = capture_last_keydown(page)

    def test_enter_key(key: str, expected_key: str, expected_code: str) -> None:
        page.keyboard.press(key)
        last_event = last_event_handle.json_value()
        assert last_event["key"] == expected_key  # had the wrong key
        assert last_event["code"] == expected_code  # had the wrong code
        value = page.eval_on_selector("textarea", "t => t.value")
        assert value == "\n"  # failed to create a newline
        page.eval_on_selector("textarea", "t => t.value = ''")

    test_enter_key("Enter", "Enter", "Enter")
    test_enter_key("NumpadEnter", "Enter", "NumpadEnter")
    test_enter_key("\n", "Enter", "Enter")
    test_enter_key("\r", "Enter", "Enter")


def test_KB_026_should_press_audio_and_media_control_keys(
    page: Page, browser_name: str
) -> None:
    page.set_content("<input autofocus>")
    page.focus("input")
    last_event = capture_last_keydown(page)
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
        page.keyboard.press(media_key["key"])
        assert last_event.evaluate("e => e.key") == media_key["key"]
        assert last_event.evaluate("e => e.code") == media_key["code"]
        assert last_event.evaluate("e => e.location") == 0


def test_KB_027_should_throw_on_unknown_keys(page: Page, server: Server) -> None:
    with pytest.raises(Error) as exc_info:
        page.keyboard.press("NotARealKey")
    assert 'Unknown key: "NotARealKey"' in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        page.keyboard.press("ё")
    assert 'Unknown key: "ё"' in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        page.keyboard.press("😊")
    assert 'Unknown key: "😊"' in exc_info.value.message


def test_KB_028_should_type_emoji(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    page.type("textarea", "👹 Tokyo street Japan 🇯🇵")
    assert (
        page.eval_on_selector("textarea", "textarea => textarea.value")
        == "👹 Tokyo street Japan 🇯🇵"
    )


def test_KB_029_should_type_emoji_into_an_iframe(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    utils.attach_frame(page, "emoji-test", server.PREFIX + "/input/textarea.html")
    frame = page.frames[1]
    textarea = frame.query_selector("textarea")
    assert textarea
    textarea.type("👹 Tokyo street Japan 🇯🇵")
    assert (
        frame.eval_on_selector("textarea", "textarea => textarea.value")
        == "👹 Tokyo street Japan 🇯🇵"
    )


def test_KB_030_should_handle_select_all(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.type("some text")
    page.keyboard.down("ControlOrMeta")
    page.keyboard.press("a")
    page.keyboard.up("ControlOrMeta")
    page.keyboard.press("Backspace")
    assert page.eval_on_selector("textarea", "textarea => textarea.value") == ""


def test_KB_031_pressing_meta_should_not_result_in_any_text_insertion_on_any_platform(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/28495
    page.set_content('<input type="text" value="hello world">')
    input = page.locator("input")
    expect(input).to_have_value("hello world")
    input.focus()
    page.keyboard.press("Meta")
    expect(input).to_have_value("hello world")


def test_KB_032_should_be_able_to_prevent_select_all(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.type("some text")
    page.eval_on_selector(
        "textarea",
        """textarea => {
        textarea.addEventListener('keydown', event => {
          if (event.key === 'a' && (event.metaKey || event.ctrlKey))
            event.preventDefault();
        }, false);
      }""",
    )
    page.keyboard.down("ControlOrMeta")
    page.keyboard.press("a")
    page.keyboard.up("ControlOrMeta")
    page.keyboard.press("Backspace")
    assert page.eval_on_selector("textarea", "textarea => textarea.value") == "some tex"


def test_KB_033_should_support_mac_os_shortcuts(
    page: Page, server: Server, platform: str, browser_name: str
) -> None:
    if platform != "darwin":
        pytest.skip("macOS only")
    # @see https://github.com/microsoft/playwright/issues/5721
    if browser_name == "firefox" and platform == "darwin":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/5721")

    page.goto(server.PREFIX + "/input/textarea.html")
    textarea = page.query_selector("textarea")
    assert textarea
    textarea.type("some text")
    # select one word backwards
    page.keyboard.press("Shift+Control+Alt+KeyB")
    page.keyboard.press("Backspace")
    assert page.eval_on_selector("textarea", "textarea => textarea.value") == "some "


def test_KB_034_should_press_the_meta_key(page: Page) -> None:
    last_event = capture_last_keydown(page)
    page.keyboard.press("Meta")
    value = last_event.json_value()
    assert value["key"] == "Meta"
    assert value["code"] == "MetaLeft"
    assert value["metaKey"] is True


def test_KB_035_should_work_with_keyboard_events_with_empty_html(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/empty.html")
    last_event = capture_last_keydown(page)
    page.keyboard.press("a")
    assert last_event.evaluate("l => l.key") == "a"


def test_KB_036_should_work_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/empty.html")
    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    last_event = capture_last_keydown(page)
    page.keyboard.press("a")
    assert last_event.evaluate("l => l.key") == "a"


def test_KB_037_should_expose_key_identifier_in_webkit(
    page: Page, browser_name: str
) -> None:
    if browser_name != "webkit":
        pytest.skip(
            "event.keyIdentifier has been removed from all browsers except WebKit"
        )

    last_event = capture_last_keydown(page)
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
        page.keyboard.press(key)
        assert last_event.evaluate("e => e.keyIdentifier") == key_identifier


def test_KB_038_should_scroll_with_page_down(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/input/scrollable.html")
    # A click is required for WebKit to send the event into the body.
    page.click("body")
    page.keyboard.press("PageDown")
    # We can't wait for the scroll to finish, so just wait for it to start.
    page.wait_for_function("() => scrollY > 0")


def test_KB_039_should_move_around_the_selection_in_a_contenteditable(
    page: Page, is_mac: bool
) -> None:
    page.set_content("<div contenteditable></div>")
    page.focus("div")
    modifier = "Alt" if is_mac else "Control"
    page.keyboard.type("Hello World")
    page.keyboard.down(modifier)
    page.keyboard.down("Shift")
    page.keyboard.press("ArrowLeft")
    page.keyboard.up("Shift")
    page.keyboard.up(modifier)
    assert page.evaluate("() => window.getSelection().toString()") == "World"


def test_KB_040_should_move_to_the_start_of_the_document(
    page: Page, is_mac: bool
) -> None:
    if not is_mac:
        pytest.skip("macOS only")
    page.set_content("<div contenteditable></div>")
    page.focus("div")
    page.keyboard.type("1\n2\n3\n")
    page.keyboard.press("Shift+Meta+ArrowUp")
    assert page.evaluate("() => window.getSelection().toString()") == "1\n2\n3\n"


def test_KB_041_should_dispatch_a_click_event_on_a_button_when_space_gets_pressed(
    page: Page,
) -> None:
    page.set_content('<button type="button">a11y</button>')
    actual = page.evaluate_handle(
        """() => {
        const actual = { clicked: false };
        document.querySelector('button').addEventListener('click', () => (actual.clicked = true));
        return actual;
      }"""
    )
    page.focus("button")
    page.keyboard.press("Space")
    assert (actual.json_value())["clicked"] is True


def test_KB_042_should_dispatch_a_click_event_on_a_button_when_enter_gets_pressed(
    page: Page,
) -> None:
    page.set_content('<button type="button">a11y</button>')
    actual = page.evaluate_handle(
        """() => {
        const actual = { clicked: false };
        document.querySelector('button').addEventListener('click', () => (actual.clicked = true));
        return actual;
      }"""
    )
    page.focus("button")
    page.keyboard.press("Enter")
    assert (actual.json_value())["clicked"] is True


def test_KB_043_should_support_simple_copy_pasting(page: Page) -> None:
    page.set_content("<div contenteditable>123</div>")
    page.focus("div")
    page.keyboard.press("ControlOrMeta+KeyA")
    page.keyboard.press("ControlOrMeta+KeyC")
    page.keyboard.press("ControlOrMeta+KeyV")
    page.keyboard.press("ControlOrMeta+KeyV")
    assert page.evaluate("() => document.querySelector('div').textContent") == "123123"


def test_KB_044_should_support_simple_cut_pasting(page: Page) -> None:
    page.set_content("<div contenteditable>123</div>")
    page.focus("div")
    page.keyboard.press("ControlOrMeta+KeyA")
    page.keyboard.press("ControlOrMeta+KeyX")
    page.keyboard.press("ControlOrMeta+KeyV")
    page.keyboard.press("ControlOrMeta+KeyV")
    assert page.evaluate("() => document.querySelector('div').textContent") == "123123"


def test_KB_045_should_support_undo_redo(
    page: Page, browser_name: str, is_linux: bool, browser_channel: Optional[str]
) -> None:
    if (browser_name == "webkit" and is_linux) or browser_channel == "webkit-wsl":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/12000")
    page.set_content("<div contenteditable></div>")
    div = page.locator("div")
    expect(div).to_have_text("")
    div.type("123")
    expect(div).to_have_text("123")
    page.keyboard.press("ControlOrMeta+KeyZ")
    expect(div).to_have_text("")
    page.keyboard.press("Shift+ControlOrMeta+KeyZ")
    expect(div).to_have_text("123")


def test_KB_046_should_type_repeatedly_in_contenteditable_in_shadow_dom(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/12941
    page.set_content(
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
    editor.type("This is the first box.")

    section_editor = page.locator("section .editor")
    section_editor.type("This is the second box.")

    assert editor.text_content() == "This is the first box."
    assert section_editor.text_content() == "This is the second box."


def test_KB_047_should_type_repeatedly_in_contenteditable_in_shadow_dom_with_nested_elements(
    page: Page,
) -> None:
    page.set_content(
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
    editor.type("This is the first box: ")

    section_editor = page.locator("section .editor")
    section_editor.type("This is the second box: ")

    assert editor.text_content() == "This is the first box: hello"
    assert section_editor.text_content() == "This is the second box: world"


def test_KB_048_should_type_repeatedly_in_input_in_shadow_dom(
    page: Page,
) -> None:
    page.set_content(
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
    editor.type("This is the first box.")

    section_editor = page.locator("section .editor")
    section_editor.type("This is the second box.")

    assert editor.input_value() == "This is the first box."
    assert section_editor.input_value() == "This is the second box."


def test_KB_049_type_to_non_focusable_element_should_maintain_old_focus(
    page: Page,
) -> None:
    page.set_content(
        """
    <div id="focusable" tabindex="0">focusable div</div>
    <div id="non-focusable-and-non-editable">non-editable, non-focusable</div>
  """
    )

    page.locator("#focusable").focus()
    assert page.evaluate("() => document.activeElement?.id") == "focusable"
    page.locator("#non-focusable-and-non-editable").type("foo")
    assert page.evaluate("() => document.activeElement?.id") == "focusable"


def test_KB_050_should_dispatch_insert_text_after_context_menu_was_opened(
    server: Server, page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "chromium" and is_win:
        pytest.skip("context menu support is best-effort for Linux and MacOS")
    page.goto(server.PREFIX + "/input/textarea.html")
    page.evaluate(
        """() => {
        window['contextMenuPromise'] = new Promise(x => {
          window.addEventListener('contextmenu', x, false);
        });
      }"""
    )

    box = page.locator("textarea").bounding_box()
    assert box
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    page.mouse.click(cx, cy, button="right")
    page.evaluate("() => window['contextMenuPromise']")

    page.keyboard.insert_text("嗨")
    poll_until_equal(page, lambda: page.locator("textarea").input_value(), "嗨")


def test_KB_051_should_type_after_context_menu_was_opened(
    server: Server, page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "chromium" and is_win:
        pytest.skip("context menu support is best-effort for Linux and MacOS")
    page.evaluate(
        """() => {
        window['keys'] = [];
        window.addEventListener('keydown', event => window['keys'].push(event.key));
        window['contextMenuPromise'] = new Promise(x => {
          window.addEventListener('contextmenu', x, false);
        });
      }"""
    )

    page.mouse.move(100, 100)
    page.mouse.down(button="right")
    page.evaluate("() => window['contextMenuPromise']")

    page.keyboard.down("ArrowDown")

    poll_until_equal(page, lambda: page.evaluate("window.keys"), ["ArrowDown"])


def test_KB_052_should_have_correct_keydown_keyup_order_when_pressing_escape_key(
    page: Page, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/27709
    page.goto(server.PREFIX + "/input/keyboard.html")
    page.keyboard.press("Escape")
    assert (
        page.evaluate("getResult()")
        == """
Keydown: Escape Escape STANDARD []
Keyup: Escape Escape STANDARD []
""".strip()
    )


def test_KB_053_should_close_dialog_on_escape_key_press_in_contenteditable(
    page: Page, is_frozen_webkit: bool
) -> None:
    # https://github.com/microsoft/playwright/issues/36727
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    page.set_content(
        """
    <dialog>
      <div contenteditable>Edit Me</div>
    </dialog>
  """
    )

    dialog = page.locator("dialog")
    widget = dialog.locator("[contenteditable]")
    dialog.evaluate("node => node.showModal()")
    expect(dialog).to_have_js_property("open", True)
    expect(widget).to_be_visible()

    widget.press("Escape")
    expect(dialog).to_have_js_property("open", False)
    expect(widget).not_to_be_visible()
