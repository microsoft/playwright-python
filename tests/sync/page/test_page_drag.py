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

"""Port of tests/page/page-drag.spec.ts."""

import time
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import ElementHandle, JSHandle, Page, Route, expect
from tests.server import Server

from ..utils import Utils


@pytest.fixture(autouse=True)
def skip_headed(headless: bool) -> None:
    if not headless:
        pytest.skip("Stray mouse events mess up the tests.")


def track_events(target: Optional[ElementHandle]) -> JSHandle:
    assert target
    return target.evaluate_handle(
        """target => {
            const events = [];
            for (const event of [
              'mousedown', 'mousemove', 'mouseup',
              'dragstart', 'dragend', 'dragover', 'dragenter', 'dragleave', 'dragexit',
              'drop'
            ]) {
              target.addEventListener(event, e => {
                const pe = e;
                // Browsers are all over the place with dragend position.
                if (event === 'dragend')
                  events.push('dragend');
                else
                  events.push(`${event} at ${pe.clientX};${pe.clientY}`);
              }, false);
            }
            return events;
        }"""
    )


def poll_json_value(
    page: Page, handle: JSHandle, expected: Any, timeout: float = 5
) -> None:
    """Port of `await expect.poll(() => handle.jsonValue()).toEqual(expected)`."""
    deadline = time.monotonic() + timeout
    actual = handle.json_value()
    while actual != expected and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        actual = handle.json_value()
    assert actual == expected


def test_DD_001_drag_and_drop_should_work_smoke(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    # could not find source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


def test_DD_002_drag_and_drop_should_send_the_right_events(
    server: Server, page: Page, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    events = track_events(page.query_selector("body"))
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    assert events.json_value() == [
        "mousemove at 120;86",
        "mousedown at 120;86",
        "dragstart at 120;86" if browser_name == "firefox" else "mousemove at 240;350",
        "mousemove at 240;350" if browser_name == "firefox" else "dragstart at 120;86",
        "dragenter at 240;350",
        "dragover at 240;350",
        "drop at 240;350",
        "dragend",
    ]


def test_DD_003_drag_and_drop_should_not_send_dragover_on_the_first_mousemove(
    server: Server, page: Page, browser_name: str
) -> None:
    if browser_name != "chromium":
        pytest.skip("fixme")

    page.goto(server.PREFIX + "/drag-n-drop.html")
    events = track_events(page.query_selector("body"))
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    assert events.json_value() == [
        "mousemove at 120;86",
        "mousedown at 120;86",
        "dragstart at 120;86" if browser_name == "firefox" else "mousemove at 240;350",
        "mousemove at 240;350" if browser_name == "firefox" else "dragstart at 120;86",
        "dragenter at 240;350",
    ]


def test_DD_004_drag_and_drop_should_work_inside_iframe(
    page: Page, server: Server, browser_name: str, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    frame = utils.attach_frame(page, "myframe", server.PREFIX + "/drag-n-drop.html")
    page.eval_on_selector(
        "iframe",
        """iframe => {
            iframe.style.width = '500px';
            iframe.style.height = '600px';
            iframe.style.marginLeft = '80px';
            iframe.style.marginTop = '60px';
        }""",
    )
    page_events = track_events(page.query_selector("body"))
    frame_events = track_events(frame.query_selector("body"))
    frame.hover("#source")
    page.mouse.down()
    frame.hover("#target")
    page.mouse.up()
    # could not find source in target
    assert (
        frame.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )
    assert frame_events.json_value() == [
        "mousemove at 120;86",
        "mousedown at 120;86",
        "dragstart at 120;86" if browser_name == "firefox" else "mousemove at 240;350",
        "mousemove at 240;350" if browser_name == "firefox" else "dragstart at 120;86",
        "dragenter at 240;350",
        "dragover at 240;350",
        "drop at 240;350",
        "dragend",
    ]
    assert page_events.json_value() == []


def test_DD_005_drag_and_drop_should_cancel_on_escape(
    server: Server, page: Page, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    events = track_events(page.query_selector("body"))
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.keyboard.press("Escape")
    page.mouse.up()
    # found source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is False
    )
    expected: List[Optional[str]] = [
        "mousemove at 120;86",
        "mousedown at 120;86",
        "dragstart at 120;86" if browser_name == "firefox" else "mousemove at 240;350",
        "mousemove at 240;350" if browser_name == "firefox" else "dragstart at 120;86",
        "dragenter at 240;350",
        None if browser_name == "chromium" else "dragover at 240;350",
        "dragend",
        "mouseup at 240;350",
    ]
    assert events.json_value() == [event for event in expected if event]


def test_DD_006_drag_and_drop_iframe_should_drag_into_an_iframe(
    server: Server, page: Page, browser_name: str, utils: Utils
) -> None:
    pytest.skip("fixme: implement dragging with iframes")
    page.goto(server.PREFIX + "/drag-n-drop.html")
    frame = utils.attach_frame(page, "oopif", server.PREFIX + "/drag-n-drop.html")
    page.eval_on_selector(
        "iframe",
        """iframe => {
            iframe.style.width = '500px';
            iframe.style.height = '600px';
            iframe.style.marginLeft = '500px';
            iframe.style.marginTop = '60px';
        }""",
    )
    page_events = track_events(page.query_selector("body"))
    frame_events = track_events(frame.query_selector("body"))
    page.hover("#source")
    page.mouse.down()
    frame.hover("#target")
    page.mouse.up()
    # could not find source in target
    assert (
        frame.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )
    assert page_events.json_value() == [
        "mousemove",
        "mousedown",
        "dragstart" if browser_name == "firefox" else "mousemove",
        "mousemove" if browser_name == "firefox" else "dragstart",
    ]
    assert frame_events.json_value() == [
        "dragenter",
        "dragover",
        "drop",
    ]


def test_DD_007_drag_and_drop_iframe_should_drag_out_of_an_iframe(
    server: Server, page: Page, utils: Utils
) -> None:
    pytest.skip("fixme: implement dragging with iframes")
    page.goto(server.PREFIX + "/drag-n-drop.html")
    frame = utils.attach_frame(page, "oopif", server.PREFIX + "/drag-n-drop.html")
    page_events = track_events(page.query_selector("body"))
    frame_events = track_events(frame.query_selector("body"))
    frame.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    # could not find source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )
    assert frame_events.json_value() == [
        "mousemove",
        "mousedown",
        "dragstart",
        "dragend",
    ]
    assert page_events.json_value() == [
        "dragenter",
        "dragover",
        "drop",
    ]


def test_DD_008_drag_and_drop_should_respect_the_drop_effect(
    page: Page,
    browser_name: str,
    is_linux: bool,
    is_mac: bool,
    headless: bool,
) -> None:
    if browser_name == "webkit" and not is_linux:
        pytest.skip(
            "fixme: WebKit doesn't handle the drop effect correctly outside of linux."
        )
    if browser_name == "webkit" and is_linux and not headless:
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/21646")
    if browser_name == "chromium" and not is_mac and not headless:
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/21646")

    def test_if_dropped(effect_allowed: str, drop_effect: str) -> Any:
        page.set_content(
            """
            <div draggable="true">drag target</div>
            <drop-target>this is the drop target</drop-target>
            """
        )
        page.evaluate(
            """({ effectAllowed, dropEffect }) => {
                window['dropped'] = false;

                document.querySelector('div').addEventListener('dragstart', event => {
                  event.dataTransfer.effectAllowed = effectAllowed;
                  event.dataTransfer.setData('text/plain', 'drag data');
                });

                const dropTarget = document.querySelector('drop-target');
                dropTarget.addEventListener('dragover', event => {
                  event.dataTransfer.dropEffect = dropEffect;
                  event.preventDefault();
                });
                dropTarget.addEventListener('drop', event => {
                  window['dropped'] = true;
                });
            }""",
            {"effectAllowed": effect_allowed, "dropEffect": drop_effect},
        )
        page.hover("div")
        page.mouse.down()
        page.hover("drop-target")
        page.mouse.up()
        return page.evaluate("dropped")

    assert test_if_dropped("copy", "copy") is True
    assert test_if_dropped("copy", "move") is False
    assert test_if_dropped("all", "link") is True
    assert test_if_dropped("all", "none") is False

    assert test_if_dropped("copyMove", "copy") is True
    assert test_if_dropped("copyLink", "copy") is True
    assert test_if_dropped("linkMove", "copy") is False

    assert test_if_dropped("copyMove", "link") is False
    assert test_if_dropped("copyLink", "link") is True
    assert test_if_dropped("linkMove", "link") is True

    assert test_if_dropped("copyMove", "move") is True
    assert test_if_dropped("copyLink", "move") is False
    assert test_if_dropped("linkMove", "move") is True

    assert test_if_dropped("uninitialized", "copy") is True


def test_DD_009_drag_and_drop_should_work_if_the_drag_is_canceled(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.evaluate(
        """() => {
            document.body.addEventListener('dragstart', event => {
              event.preventDefault();
            }, false);
        }"""
    )
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is False
    )


def test_DD_010_drag_and_drop_should_work_if_the_drag_event_is_captured_but_not_canceled(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.evaluate(
        """() => {
            document.body.addEventListener('dragstart', event => {
              event.stopImmediatePropagation();
            }, false);
        }"""
    )
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


def test_DD_011_drag_and_drop_should_be_able_to_drag_the_mouse_in_a_frame(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/frames/one-frame.html")
    events_handle = track_events(page.frames[1].query_selector("html"))
    page.mouse.move(30, 30)
    page.mouse.down()
    page.mouse.move(60, 60)
    page.mouse.up()
    assert events_handle.json_value() == [
        "mousemove at 20;20",
        "mousedown at 20;20",
        "mousemove at 50;50",
        "mouseup at 50;50",
    ]


def test_DD_012_drag_and_drop_should_work_if_a_frame_is_stalled(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    routes: List[Route] = []

    def handler(route: Route) -> None:
        routes.append(route)

    page.route("**/empty.html", handler)
    # Upstream does not wait for attachFrame(): the frame never loads until the route aborts.
    page.evaluate(
        """url => {
            const frame = document.createElement('iframe');
            frame.src = url;
            frame.id = 'frame';
            document.body.appendChild(frame);
        }""",
        server.EMPTY_PAGE,
    )
    while not routes:
        page.wait_for_timeout(100)
    route = routes[0]
    page.hover("#source")
    page.mouse.down()
    page.hover("#target")
    page.mouse.up()
    route.abort()
    # could not find source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


def test_DD_013_drag_and_drop_should_work_with_the_helper_method(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.drag_and_drop("#source", "#target")
    # could not find source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


@pytest.mark.parametrize("title", ["dragAndDrop", "dragTo"])
def test_DD_014_drag_and_drop_should_with_tweened_mouse_movement(
    page: Page, headless: bool, title: str
) -> None:
    if not headless:
        pytest.skip("actual mouse interferes with the exact mousemove events")

    page.set_content(
        """
        <body style="margin: 0; padding: 0;">
          <div style="width:100px;height:100px;background:red;" id="red"></div>
          <div style="width:300px;height:100px;background:blue;" id="blue"></div>
        </body>
        """
    )
    events_handle = page.evaluate_handle(
        """() => {
            const events = [];
            document.addEventListener('mousedown', event => {
              events.push({
                type: 'mousedown',
                x: event.pageX,
                y: event.pageY,
              });
            });
            document.addEventListener('mouseup', event => {
              events.push({
                type: 'mouseup',
                x: event.pageX,
                y: event.pageY,
              });
            });
            document.addEventListener('mousemove', event => {
              events.push({
                type: 'mousemove',
                x: event.pageX,
                y: event.pageY,
              });
            });
            return events;
        }"""
    )
    if title == "dragAndDrop":
        page.drag_and_drop("#red", "#blue", steps=4)
    else:
        page.locator("#red").drag_to(page.locator("#blue"), steps=4)
    poll_json_value(
        page,
        events_handle,
        [
            {"type": "mousemove", "x": 50, "y": 50},
            {"type": "mousedown", "x": 50, "y": 50},
            {"type": "mousemove", "x": 75, "y": 75},
            {"type": "mousemove", "x": 100, "y": 100},
            {"type": "mousemove", "x": 125, "y": 125},
            {"type": "mousemove", "x": 150, "y": 150},
            {"type": "mouseup", "x": 150, "y": 150},
        ],
    )


def test_DD_015_drag_and_drop_should_allow_specifying_the_position(
    page: Page, server: Server
) -> None:
    page.set_content(
        """
        <div style="width:100px;height:100px;background:red;" id="red">
        </div>
        <div style="width:100px;height:100px;background:blue;" id="blue">
        </div>
        """
    )
    events_handle = page.evaluate_handle(
        """() => {
            const events = [];
            document.getElementById('red').addEventListener('mousedown', event => {
              events.push({
                type: 'mousedown',
                x: event.offsetX,
                y: event.offsetY,
              });
            });
            document.getElementById('blue').addEventListener('mouseup', event => {
              events.push({
                type: 'mouseup',
                x: event.offsetX,
                y: event.offsetY,
              });
            });
            return events;
        }"""
    )
    page.drag_and_drop(
        "#red",
        "#blue",
        source_position={"x": 34, "y": 7},
        target_position={"x": 10, "y": 20},
    )
    assert events_handle.json_value() == [
        {"type": "mousedown", "x": 34, "y": 7},
        {"type": "mouseup", "x": 10, "y": 20},
    ]


def test_DD_016_drag_and_drop_should_work_with_locators(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/drag-n-drop.html")
    page.locator("#source").drag_to(page.locator("#target"))
    # could not find source in target
    assert (
        page.eval_on_selector(
            "#target", "target => target.contains(document.querySelector('#source'))"
        )
        is True
    )


def test_DD_017_should_work_if_not_doing_a_drag(page: Page) -> None:
    events_handle = track_events(page.query_selector("html"))
    page.mouse.move(50, 50)
    page.mouse.down()
    page.mouse.move(100, 100)
    page.mouse.up()
    assert events_handle.json_value() == [
        "mousemove at 50;50",
        "mousedown at 50;50",
        "mousemove at 100;100",
        "mouseup at 100;100",
    ]


def test_DD_018_should_report_event_buttons(page: Page) -> None:
    logs_handle = page.evaluate_handle(
        """async () => {
            const div = document.createElement('div');
            document.body.appendChild(div);
            div.style.width = '200px';
            div.style.height = '200px';
            div.style.backgroundColor = 'blue';
            div.addEventListener('mousedown', onEvent);
            div.addEventListener('mousemove', onEvent, { passive: false });
            div.addEventListener('mouseup', onEvent);
            const logs = [];
            function onEvent(event) {
              logs.push({ type: event.type, buttons: event.buttons });
            }
            await new Promise(window.builtins.requestAnimationFrame);
            return logs;
        }"""
    )
    page.mouse.move(20, 20)
    page.mouse.down()
    page.mouse.move(40, 40)
    page.mouse.up()
    logs = logs_handle.json_value()
    assert logs == [
        {"type": "mousemove", "buttons": 0},
        {"type": "mousedown", "buttons": 1},
        {"type": "mousemove", "buttons": 1},
        {"type": "mouseup", "buttons": 0},
    ]


def test_DD_019_should_handle_custom_data_transfer(
    page: Page, browser_name: str, is_win: bool, sync_gather: Callable
) -> None:
    if browser_name == "webkit" and is_win:
        pytest.skip("fixme")
    page.set_content("""<button draggable="true">Draggable</button>""")

    def drag() -> None:
        page.hover('[draggable="true"]')
        page.mouse.down()
        page.mouse.move(100, 100)
        page.mouse.up()

    result, _ = sync_gather(
        lambda: page.evaluate(
            """() => new Promise(resolve => {
                document.addEventListener('dragstart', event => {
                  event.dataTransfer.setData('custom-type', 'Hello World');
                }, false);

                document.addEventListener('dragenter', event => {
                  event.preventDefault();
                }, false);
                document.addEventListener('dragover', event => {
                  event.preventDefault();
                }, false);

                document.addEventListener('drop', event => {
                  event.preventDefault();
                  resolve({
                    types: event.dataTransfer.types,
                    data: event.dataTransfer.getData('custom-type'),
                  });
                }, false);
            })"""
        ),
        drag,
    )

    assert result == {
        "types": ["custom-type"],
        "data": "Hello World",
    }


def test_DD_020_what_happens_when_dragging_element_is_destroyed(
    page: Page, browser_name: str
) -> None:
    page.set_content(
        """
        <button draggable="true">Draggable</button>
        <div id=target>drop here</div>
        """
    )

    page.evaluate(
        """() => {
            document.querySelector('#target').addEventListener('dragover', event => {
              document.querySelector('button')?.remove();
            }, false);

            document.querySelector('#target').addEventListener('drop', event => {
              document.querySelector('#target').textContent = 'dropped';
            }, false);
        }"""
    )

    page.locator("button").drag_to(page.locator("div"))
    expect(page.locator("div")).to_have_text("drop here")
