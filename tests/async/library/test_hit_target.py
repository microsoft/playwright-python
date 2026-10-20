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

"""Port of tests/library/hit-target.spec.ts."""

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server


async def test_HT_001_should_block_all_events_when_hit_target_is_wrong(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
    const blocker = document.createElement('div');
    blocker.style.position = 'absolute';
    blocker.style.width = '400px';
    blocker.style.height = '400px';
    blocker.style.left = '0';
    blocker.style.top = '0';
    document.body.appendChild(blocker);

    const allEvents = [];
    window.allEvents = allEvents;
    for (const name of ['mousedown', 'mouseup', 'click', 'dblclick', 'auxclick', 'contextmenu', 'pointerdown', 'pointerup']) {
      window.addEventListener(name, e => allEvents.push(e.type));
      blocker.addEventListener(name, e => allEvents.push(e.type));
    }
  }"""
    )

    with pytest.raises(Error) as exc_info:
        await page.click("button", timeout=3000)
    assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message

    # Give it some time, just in case.
    await page.wait_for_timeout(1000)
    all_events = await page.evaluate("() => window.allEvents")
    assert all_events == []


async def test_HT_002_should_block_click_when_mousedown_fails(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
    button.addEventListener('mousemove', () => {
      button.style.marginLeft = '100px';
    });

    const allEvents = [];
    window.allEvents = allEvents;
    for (const name of ['mousemove', 'mousedown', 'mouseup', 'click', 'dblclick', 'auxclick', 'contextmenu', 'pointerdown', 'pointerup'])
      button.addEventListener(name, e => allEvents.push(e.type));
  }""",
    )

    await page.click("button")
    assert await page.evaluate("result") == "Clicked"
    all_events = await page.evaluate("() => window.allEvents")
    assert all_events == [
        # First attempt failed.
        "mousemove",
        # Second attempt succeeded.
        "mousemove",
        "pointerdown",
        "mousedown",
        "pointerup",
        "mouseup",
        "click",
    ]


async def test_HT_003_should_click_when_element_detaches_in_mousedown(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
    button.addEventListener('mousedown', () => {
      window.result = 'Mousedown';
      button.remove();
    });
  }""",
    )

    await page.click("button", timeout=15000)
    assert await page.evaluate("result") == "Mousedown"


async def test_HT_004_should_block_all_events_when_hit_target_is_wrong_and_element_detaches(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
    const blocker = document.createElement('div');
    blocker.style.position = 'absolute';
    blocker.style.width = '400px';
    blocker.style.height = '400px';
    blocker.style.left = '0';
    blocker.style.top = '0';
    document.body.appendChild(blocker);

    window.addEventListener('mousemove', () => button.remove());

    const allEvents = [];
    window.allEvents = allEvents;
    for (const name of ['mousedown', 'mouseup', 'click', 'dblclick', 'auxclick', 'contextmenu', 'pointerdown', 'pointerup']) {
      window.addEventListener(name, e => allEvents.push(e.type));
      blocker.addEventListener(name, e => allEvents.push(e.type));
    }
  }""",
    )

    with pytest.raises(Error) as exc_info:
        await page.click("button", timeout=3000)
    assert "Page.click: Timeout 3000ms exceeded." in exc_info.value.message

    # Give it some time, just in case.
    await page.wait_for_timeout(1000)
    all_events = await page.evaluate("() => window.allEvents")
    assert all_events == []


async def test_HT_005_should_not_block_programmatic_events(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.eval_on_selector(
        "button",
        """button => {
    button.addEventListener('mousemove', () => {
      button.style.marginLeft = '100px';
      button.dispatchEvent(new MouseEvent('click'));
    });

    const allEvents = [];
    window.allEvents = allEvents;
    button.addEventListener('click', e => {
      if (!e.isTrusted)
        allEvents.push(e.type);
    });
  }""",
    )

    await page.click("button")
    assert await page.evaluate("result") == "Clicked"
    all_events = await page.evaluate("() => window.allEvents")
    # We should get one programmatic click on each attempt.
    assert all_events == [
        "click",
        "click",
    ]


async def test_HT_006_should_click_the_button_again_after_document_write(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    assert await page.evaluate("result") == "Clicked"

    await page.evaluate(
        """() => {
    document.open();
    document.write('<button onclick="window.result2 = true"></button>');
    document.close();
  }"""
    )
    await page.click("button")
    assert await page.evaluate("result2") is True


async def test_HT_007_should_work_with_mui_select(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/mui.html")
    await page.evaluate(
        """() => {
    renderComponent(e(MaterialUI.FormControl, { fullWidth: true }, [
      e(MaterialUI.InputLabel, { id: 'demo-simple-select-label' }, ['Age']),
      e(MaterialUI.Select, {
        labelId: 'demo-simple-select-label',
        id: 'demo-simple-select',
        value: 10,
        label: 'Age',
      }, [
        e(MaterialUI.MenuItem, { value: 10 }, ['Ten']),
        e(MaterialUI.MenuItem, { value: 20 }, ['Twenty']),
        e(MaterialUI.MenuItem, { value: 30 }, ['Thirty']),
      ]),
    ]));
  }"""
    )
    await page.click('div.MuiFormControl-root:has-text("Age")')
    await expect(page.locator("text=Thirty")).to_be_visible()


async def test_HT_008_should_work_with_drag_and_drop_that_moves_the_element_under_cursor(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/input/drag-n-drop-manual.html")
    await page.drag_and_drop("#from", "#to")
    await expect(page.locator("#to")).to_have_text("Dropped")


async def test_HT_009_should_work_with_block_inside_inline(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <div>
      <span>
        <div id="target" onclick="window._clicked=true">
          Romimine
        </div>
      </span>
    </div>
  """
    )
    await page.locator("#target").click()
    assert await page.evaluate("window._clicked") is True


async def test_HT_010_should_work_with_block_block_block_inside_inline_inline(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <div>
      <a href="#ney">
        <div>
          <span>
            <a href="#yay">
              <div>
                <h3 id="target">
                  Romimine
                </h3>
              </div>
            </a>
          </span>
        </div>
      </a>
    </div>
  """
    )
    await page.locator("#target").click()
    await expect(page).to_have_url(server.EMPTY_PAGE + "#yay")


async def test_HT_011_should_work_with_block_inside_inline_in_shadow_dom(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <div>
    </div>
    <script>
      const root = document.querySelector('div');
      const shadowRoot = root.attachShadow({ mode: 'open' });
      const span = document.createElement('span');
      shadowRoot.appendChild(span);
      const div = document.createElement('div');
      span.appendChild(div);
      div.id = 'target';
      div.addEventListener('click', () => window._clicked = true);
      div.textContent = 'Hello';
    </script>
  """
    )
    await page.locator("#target").click()
    assert await page.evaluate("window._clicked") is True


async def test_HT_012_should_not_click_iframe_overlaying_the_target(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <button style="position: absolute; left: 250px;bottom: 0;height: 40px;width: 200px;" onclick="window._clicked=1">
      click-me
    </button>
    <div style="background: transparent; bottom: 0px; left: 0px; margin: 0px; padding: 0px; position: fixed; z-index: 2147483647;">
      <iframe srcdoc="<body onclick='window.top._clicked=2' style='background-color:red;height:40px;'></body>" style="display: block; border: 0px; width: 100vw; height: 48px;"></iframe>
    </div>
  """
    )
    with pytest.raises(Error) as exc_info:
        await page.click("text=click-me", timeout=3000)
    assert await page.evaluate("window._clicked") is None
    assert (
        "<iframe srcdoc=\"<body onclick='window.top._clicked=2' style='background-color:red;height:40px;'></body>\"></iframe> from <div>…</div> subtree intercepts pointer events"
        in exc_info.value.message
    )


async def test_HT_013_should_not_click_an_element_overlaying_iframe_with_the_target(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <div onclick='window.top._clicked=1'>padding</div>
    <iframe width=600 height=600 srcdoc="<iframe srcdoc='<div onclick=&quot;window.top._clicked=2&quot;>padding</div><div onclick=&quot;window.top._clicked=3&quot;>inner</div>'></iframe><div onclick='window.top._clicked=4'>outer</div>"></iframe>
    <div onclick='window.top._clicked=5' style="position: absolute; left: 0; right: 0; top: 0; bottom: 0; background: rgba(255, 0, 0, 0.1); padding: 200px;">PINK OVERLAY</div>
  """
    )

    target = page.frame_locator("iframe").frame_locator("iframe").locator("text=inner")
    with pytest.raises(Error) as exc_info:
        await target.click(timeout=3000)
    assert await page.evaluate("window._clicked") is None
    assert (
        '<div onclick="window.top._clicked=5">PINK OVERLAY</div> intercepts pointer events'
        in exc_info.value.message
    )

    await page.locator("text=overlay").evaluate("e => e.style.display = 'none'")

    await target.click()
    assert await page.evaluate("window._clicked") == 3


async def test_HT_014_should_click_into_frame_inside_closed_shadow_root(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <div id=framecontainer>
    </div>
    <script>
      const iframe = document.createElement('iframe');
      iframe.setAttribute('name', 'myframe');
      iframe.setAttribute('srcdoc', '<div onclick="window.top.__clicked = true">click me</div>');
      const div = document.getElementById('framecontainer');
      const host = div.attachShadow({ mode: 'closed' });
      host.appendChild(iframe);
    </script>
  """
    )

    frame = page.frames[1]
    await frame.locator("text=click me").click()
    assert await page.evaluate("window.__clicked") is True


async def test_HT_015_should_click_an_element_inside_closed_shadow_root(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <div id=container>
    </div>
    <script>
      const span = document.createElement('span');
      span.textContent = 'click me';
      span.addEventListener('click', () => window.__clicked = true);
      const div = document.getElementById('container');
      const host = div.attachShadow({ mode: 'closed' });
      host.appendChild(span);
      window.__target = span;
    </script>
  """
    )

    handle = await page.evaluate_handle("window.__target")
    element = handle.as_element()
    assert element
    await element.click()
    assert await page.evaluate("window.__clicked") is True


async def test_HT_016_should_detect_overlay_from_another_shadow_root(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <style>
      div > div {
        position: absolute;
        top: 0;
        left: 0;
        width: 10px;
        height: 10px;
      }
      span {
        display: block;
        position: absolute;
        left: 0;
        top: 0;
        width: 300px;
        height: 300px;
      }
    </style>
    <div style="position:relative; width:300px; height:300px">
      <div id=container1></div>
      <div id=container2></div>
    </div>
    <script>
      for (const id of ['container1', 'container2']) {
        const span = document.createElement('span');
        span.id = id + '-span';
        span.textContent = 'click me';
        span.style.display = 'block';
        span.style.position = 'absolute';
        span.style.left = '20px';
        span.style.top = '20px';
        span.style.width = '300px';
        span.style.height = '300px';
        span.addEventListener('click', () => window.__clicked = id);
        const div = document.getElementById(id);
        const host = div.attachShadow({ mode: 'open' });
        host.appendChild(span);
      }
    </script>
  """
    )

    with pytest.raises(Error) as exc_info:
        await page.locator("#container1 >> text=click me").click(timeout=3000)
    assert '<div id="container2"></div> intercepts pointer events' in (
        exc_info.value.message
    )


async def test_HT_017_should_detect_overlaid_element_in_a_transformed_iframe(
    page: Page,
) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; }
      iframe {
        border: 4px solid black;
        background: gray;
        margin-left: 33px;
        margin-top: 24px;
        width: 400px;
        height: 400px;
        transform: scale(1.2);
      }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { margin-left: 10px; margin-top: 20px; width: 2px; height: 2px; }
        section { position: absolute; top: 0; left: 0; bottom: 0; right: 0; }
      </style>
      <div>Target</div>
      <section>Overlay</section>
      <script>
        document.querySelector('div').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("div")
    with pytest.raises(Error) as exc_info:
        await locator.click(timeout=5000)
    assert "<section>Overlay</section> intercepts pointer events" in (
        exc_info.value.message
    )


async def test_HT_018_should_click_in_iframe_with_padding(page: Page) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; box-sizing: border-box; }
      iframe { background: gray; width: 200px; height: 200px; padding-top: 100px; }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { height: 100px; }
      </style>
      <div>Non-target</div>
      <div id=target>Target</div>
      <div>Non-target</div>
      <script>
        document.querySelector('#target').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("#target")
    await locator.click()
    assert await page.evaluate("window._clicked") is True


async def test_HT_019_should_click_in_iframe_with_padding_2(page: Page) -> None:
    await page.set_content(
        """
    <style>
      body, html, iframe { margin: 0; padding: 0; border: none; box-sizing: content-box; }
      iframe { background: gray; width: 200px; height: 200px; padding-top: 100px; }
    </style>
    <iframe srcdoc="
      <style>
        body, html { margin: 0; padding: 0; }
        div { height: 100px; }
      </style>
      <div>Non-target</div>
      <div id=target>Target</div>
      <div>Non-target</div>
      <script>
        document.querySelector('#target').addEventListener('click', () => window.top._clicked = true);
      </script>
    "></iframe>
  """
    )
    locator = page.frame_locator("iframe").locator("#target")
    await locator.click()
    assert await page.evaluate("window._clicked") is True


async def test_HT_020_should_click_in_custom_element(page: Page) -> None:
    await page.set_content(
        """
    <html>
      <body>
        <my-input></my-input>
        <script>
          class MyInput extends HTMLElement {
            connectedCallback() {
              this.attachShadow({mode:'open'});
              this.shadowRoot.innerHTML = '<div><span><input type="text" /></span></div>';
              this.shadowRoot.querySelector('input').addEventListener('click', () => window.__clicked = true);
            }
          }
          customElements.define('my-input', MyInput);
        </script>
      </body>
    </html>
  """
    )
    await page.locator("input").click()
    assert await page.evaluate("window.__clicked") is True


async def test_HT_021_should_click_in_nested_custom_elements(page: Page) -> None:
    await page.set_content(
        """
    <outer-host></outer-host>
    <script>
      customElements.define('inner-host', class extends HTMLElement {
        connectedCallback() {
          this.attachShadow({ mode: 'open' }).innerHTML = '<inner-most></inner-most>';
        }
      });
      customElements.define('inner-most', class extends HTMLElement {
        connectedCallback() {
          this.attachShadow({ mode: 'open' }).innerHTML = '<input>';
          this.shadowRoot.querySelector('input').addEventListener('click', () => window.__clicked = true);
        }
      });
      customElements.define('outer-host', class extends HTMLElement {
        connectedCallback() {
          this.attachShadow({ mode: 'open' }).innerHTML = '<inner-host></inner-host>';
        }
      });
    </script>
  """
    )
    await page.locator("input").click()
    assert await page.evaluate("window.__clicked") is True


async def test_HT_022_should_click_an_element_inside_nested_closed_shadow_roots(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div id=container></div>
    <script>
      const input = document.createElement('input');
      input.addEventListener('click', () => window.__clicked = true);
      const outer = document.getElementById('container').attachShadow({ mode: 'closed' });
      const inner = document.createElement('div');
      outer.appendChild(inner);
      inner.attachShadow({ mode: 'closed' }).appendChild(input);
      window.__target = input;
    </script>
  """
    )
    handle = await page.evaluate_handle("window.__target")
    element = handle.as_element()
    assert element
    await element.click()
    assert await page.evaluate("window.__clicked") is True
