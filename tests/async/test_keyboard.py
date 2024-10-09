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
import pytest

from playwright.async_api import Error, JSHandle, Page
from tests.server import Server

from .utils import Utils


async def captureLastKeydown(page: Page) -> JSHandle:
    lastEvent = await page.evaluate_handle(
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
        // keyIdentifier only exists in WebKit, and isn't in TypeScript's lib.
        lastEvent.keyIdentifier = 'keyIdentifier' in e && e.keyIdentifier;
        }, true);
        return lastEvent;
    }"""
    )
    return lastEvent


async def test_keyboard_type_into_a_textarea(page: Page) -> None:
    await page.evaluate(
        """
            const textarea = document.createElement('textarea');
            document.body.appendChild(textarea);
            textarea.focus();
        """
    )
    text = "Hello world. I am the text that was typed!"
    await page.keyboard.type(text)
    assert await page.evaluate('document.querySelector("textarea").value') == text


async def test_keyboard_move_with_the_arrow_keys(page: Page, server: Server) -> None:
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    await page.type("textarea", "Hello World!")
    assert (
        await page.evaluate("document.querySelector('textarea').value")
        == "Hello World!"
    )
    for _ in "World!":
        await page.keyboard.press("ArrowLeft")
    await page.keyboard.type("inserted ")
    assert (
        await page.evaluate("document.querySelector('textarea').value")
        == "Hello inserted World!"
    )
    await page.keyboard.down("Shift")
    for _ in "inserted ":
        await page.keyboard.press("ArrowLeft")
    await page.keyboard.up("Shift")
    await page.keyboard.press("Backspace")
    assert (
        await page.evaluate("document.querySelector('textarea').value")
        == "Hello World!"
    )


async def test_keyboard_send_a_character_with_elementhandle_press(
    page: Page, server: Server
) -> None:
    await page.goto(f"{server.PREFIX}/input/textarea.html")
    textarea = await page.query_selector("textarea")
    assert textarea
    await textarea.press("a")
    assert await page.evaluate("document.querySelector('textarea').value") == "a"
    await page.evaluate(
        "() => window.addEventListener('keydown', e => e.preventDefault(), true)"
    )
    await textarea.press("b")
    assert await page.evaluate("document.querySelector('textarea').value") == "a"


async def test_should_send_a_character_with_send_character(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    await page.keyboard.insert_text("嗨")
    assert await page.evaluate('() => document.querySelector("textarea").value') == "嗨"
    await page.evaluate(
        '() => window.addEventListener("keydown", e => e.preventDefault(), true)'
    )
    await page.keyboard.insert_text("a")
    assert (
        await page.evaluate('() => document.querySelector("textarea").value') == "嗨a"
    )


async def test_should_only_emit_input_event(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
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


async def test_should_report_shiftkey(
    page: Page, server: Server, is_mac: bool, is_firefox: bool
) -> None:
    if is_firefox and is_mac:
        pytest.skip()
    await page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    codeForKey = {"Shift": 16, "Alt": 18, "Control": 17}
    for modifierKey in codeForKey.keys():
        await keyboard.down(modifierKey)
        assert (
            await page.evaluate("() => getResult()")
            == "Keydown: "
            + modifierKey
            + " "
            + modifierKey
            + "Left "
            + str(codeForKey[modifierKey])
            + " ["
            + modifierKey
            + "]"
        )
        await keyboard.down("!")
        # Shift+! will generate a keypress
        if modifierKey == "Shift":
            assert (
                await page.evaluate("() => getResult()")
                == "Keydown: ! Digit1 49 ["
                + modifierKey
                + "]\nKeypress: ! Digit1 33 33 ["
                + modifierKey
                + "]"
            )
        else:
            assert (
                await page.evaluate("() => getResult()")
                == "Keydown: ! Digit1 49 [" + modifierKey + "]"
            )

        await keyboard.up("!")
        assert (
            await page.evaluate("() => getResult()")
            == "Keyup: ! Digit1 49 [" + modifierKey + "]"
        )
        await keyboard.up(modifierKey)
        assert (
            await page.evaluate("() => getResult()")
            == "Keyup: "
            + modifierKey
            + " "
            + modifierKey
            + "Left "
            + str(codeForKey[modifierKey])
            + " []"
        )


async def test_should_report_multiple_modifiers(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    await keyboard.down("Control")
    assert (
        await page.evaluate("() => getResult()")
        == "Keydown: Control ControlLeft 17 [Control]"
    )
    await keyboard.down("Alt")
    assert (
        await page.evaluate("() => getResult()")
        == "Keydown: Alt AltLeft 18 [Alt Control]"
    )
    await keyboard.down(";")
    assert (
        await page.evaluate("() => getResult()")
        == "Keydown: ; Semicolon 186 [Alt Control]"
    )
    await keyboard.up(";")
    assert (
        await page.evaluate("() => getResult()")
        == "Keyup: ; Semicolon 186 [Alt Control]"
    )
    await keyboard.up("Control")
    assert (
        await page.evaluate("() => getResult()")
        == "Keyup: Control ControlLeft 17 [Alt]"
    )
    await keyboard.up("Alt")
    assert await page.evaluate("() => getResult()") == "Keyup: Alt AltLeft 18 []"


async def test_should_send_proper_codes_while_typing(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.type("!")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: ! Digit1 49 []",
            "Keypress: ! Digit1 33 33 []",
            "Keyup: ! Digit1 49 []",
        ]
    )
    await page.keyboard.type("^")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: ^ Digit6 54 []",
            "Keypress: ^ Digit6 94 94 []",
            "Keyup: ^ Digit6 54 []",
        ]
    )


async def test_should_send_proper_codes_while_typing_with_shift(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    keyboard = page.keyboard
    await keyboard.down("Shift")
    await page.keyboard.type("~")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft 16 [Shift]",
            "Keydown: ~ Backquote 192 [Shift]",  # 192 is ` keyCode
            "Keypress: ~ Backquote 126 126 [Shift]",  # 126 is ~ charCode
            "Keyup: ~ Backquote 192 [Shift]",
        ]
    )
    await keyboard.up("Shift")


async def test_should_not_type_canceled_events(page: Page, server: Server) -> None:
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
    assert (
        await page.eval_on_selector("textarea", "textarea => textarea.value")
        == "He Wrd!"
    )


async def test_should_press_plus(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("+")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: + Equal 187 []",  # 192 is ` keyCode
            "Keypress: + Equal 43 43 []",  # 126 is ~ charCode
            "Keyup: + Equal 187 []",
        ]
    )


async def test_should_press_shift_plus(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Shift++")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft 16 [Shift]",
            "Keydown: + Equal 187 [Shift]",  # 192 is ` keyCode
            "Keypress: + Equal 43 43 [Shift]",  # 126 is ~ charCode
            "Keyup: + Equal 187 [Shift]",
            "Keyup: Shift ShiftLeft 16 []",
        ]
    )


async def test_should_support_plus_separated_modifiers(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Shift+~")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft 16 [Shift]",
            "Keydown: ~ Backquote 192 [Shift]",  # 192 is ` keyCode
            "Keypress: ~ Backquote 126 126 [Shift]",  # 126 is ~ charCode
            "Keyup: ~ Backquote 192 [Shift]",
            "Keyup: Shift ShiftLeft 16 []",
        ]
    )


async def test_should_suport_multiple_plus_separated_modifiers(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Control+Shift+~")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: Control ControlLeft 17 [Control]",
            "Keydown: Shift ShiftLeft 16 [Control Shift]",
            "Keydown: ~ Backquote 192 [Control Shift]",  # 192 is ` keyCode
            "Keyup: ~ Backquote 192 [Control Shift]",
            "Keyup: Shift ShiftLeft 16 [Control]",
            "Keyup: Control ControlLeft 17 []",
        ]
    )


async def test_should_shift_raw_codes(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/keyboard.html")
    await page.keyboard.press("Shift+Digit3")
    assert await page.evaluate("() => getResult()") == "\n".join(
        [
            "Keydown: Shift ShiftLeft 16 [Shift]",
            "Keydown: # Digit3 51 [Shift]",  # 51 is # keyCode
            "Keypress: # Digit3 35 35 [Shift]",  # 35 is # charCode
            "Keyup: # Digit3 51 [Shift]",
            "Keyup: Shift ShiftLeft 16 []",
        ]
    )


async def test_should_specify_repeat_property(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    lastEvent = await captureLastKeydown(page)
    await page.keyboard.down("a")
    assert await lastEvent.evaluate("e => e.repeat") is False
    await page.keyboard.press("a")
    assert await lastEvent.evaluate("e => e.repeat")

    await page.keyboard.down("b")
    assert await lastEvent.evaluate("e => e.repeat") is False
    await page.keyboard.down("b")
    assert await lastEvent.evaluate("e => e.repeat")

    await page.keyboard.up("a")
    await page.keyboard.down("a")
    assert await lastEvent.evaluate("e => e.repeat") is False


async def test_should_type_all_kinds_of_characters(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.focus("textarea")
    text = "This text goes onto two lines.\nThis character is 嗨."
    await page.keyboard.type(text)
    assert await page.eval_on_selector("textarea", "t => t.value") == text


async def test_should_specify_location(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    lastEvent = await captureLastKeydown(page)
    textarea = await page.query_selector("textarea")
    assert textarea

    await textarea.press("Digit5")
    assert await lastEvent.evaluate("e => e.location") == 0

    await textarea.press("ControlLeft")
    assert await lastEvent.evaluate("e => e.location") == 1

    await textarea.press("ControlRight")
    assert await lastEvent.evaluate("e => e.location") == 2

    await textarea.press("NumpadSubtract")
    assert await lastEvent.evaluate("e => e.location") == 3


async def test_should_press_enter(page: Page) -> None:
    await page.set_content("<textarea></textarea>")
    await page.focus("textarea")
    lastEventHandle = await captureLastKeydown(page)

    async def testEnterKey(key: str, expectedKey: str, expectedCode: str) -> None:
        await page.keyboard.press(key)
        lastEvent = await lastEventHandle.json_value()
        assert lastEvent["key"] == expectedKey
        assert lastEvent["code"] == expectedCode
        value = await page.eval_on_selector("textarea", "t => t.value")
        assert value == "\n"
        await page.eval_on_selector("textarea", "t => t.value = ''")

    await testEnterKey("Enter", "Enter", "Enter")
    await testEnterKey("NumpadEnter", "Enter", "NumpadEnter")
    await testEnterKey("\n", "Enter", "Enter")
    await testEnterKey("\r", "Enter", "Enter")


async def test_should_throw_unknown_keys(page: Page, server: Server) -> None:
    with pytest.raises(Error) as exc:
        await page.keyboard.press("NotARealKey")
    assert exc.value.message == 'Keyboard.press: Unknown key: "NotARealKey"'

    with pytest.raises(Error) as exc:
        await page.keyboard.press("ё")
    assert exc.value.message == 'Keyboard.press: Unknown key: "ё"'

    with pytest.raises(Error) as exc:
        await page.keyboard.press("😊")
    assert exc.value.message == 'Keyboard.press: Unknown key: "😊"'


async def test_should_type_emoji(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    await page.type("textarea", "👹 Tokyo street Japan 🇯🇵")
    assert (
        await page.eval_on_selector("textarea", "textarea => textarea.value")
        == "👹 Tokyo street Japan 🇯🇵"
    )


async def test_should_type_emoji_into_an_iframe(
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


async def test_should_handle_select_all(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/textarea.html")
    textarea = await page.query_selector("textarea")
    assert textarea
    await textarea.type("some text")
    await page.keyboard.down("ControlOrMeta")
    await page.keyboard.press("a")
    await page.keyboard.up("ControlOrMeta")
    await page.keyboard.press("Backspace")
    assert await page.eval_on_selector("textarea", "textarea => textarea.value") == ""


async def test_should_be_able_to_prevent_select_all(page: Page, server: Server) -> None:
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


@pytest.mark.only_platform("darwin")
@pytest.mark.skip_browser("firefox")  # Upstream issue
async def test_should_support_macos_shortcuts(
    page: Page, server: Server, is_firefox: bool, is_mac: bool
) -> None:
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


async def test_should_press_the_meta_key(page: Page) -> None:
    lastEvent = await captureLastKeydown(page)
    await page.keyboard.press("Meta")
    v = await lastEvent.json_value()
    metaKey = v["metaKey"]
    key = v["key"]
    code = v["code"]
    assert key == "Meta"
    assert code == "MetaLeft"
    assert metaKey


async def test_should_work_after_a_cross_origin_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/empty.html")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    lastEvent = await captureLastKeydown(page)
    await page.keyboard.press("a")
    assert await lastEvent.evaluate("l => l.key") == "a"


# event.keyIdentifier has been removed from all browsers except WebKit
@pytest.mark.only_browser("webkit")
async def test_should_expose_keyIdentifier_in_webkit(
    page: Page, server: Server
) -> None:
    lastEvent = await captureLastKeydown(page)
    keyMap = {
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
    for key, keyIdentifier in keyMap.items():
        await page.keyboard.press(key)
        assert await lastEvent.evaluate("e => e.keyIdentifier") == keyIdentifier


async def test_should_scroll_with_pagedown(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/input/scrollable.html")
    # A click is required for WebKit to send the event into the body.
    await page.click("body")
    await page.keyboard.press("PageDown")
    # We can't wait for the scroll to finish, so just wait for it to start.
    await page.wait_for_function("() => scrollY > 0")
