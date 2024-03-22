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
from pathlib import Path

import pytest

from playwright.async_api import Browser, Error, Page, Selectors

from .utils import Utils


async def test_selectors_register_should_work(
    selectors: Selectors, browser: Browser, browser_name: str
) -> None:
    tag_selector = """
        {
            create(root, target) {
                return target.nodeName;
            },
            query(root, selector) {
                return root.querySelector(selector);
            },
            queryAll(root, selector) {
                return Array.from(root.querySelectorAll(selector));
            }
        }"""

    selector_name = f"tag_{browser_name}"
    selector2_name = f"tag2_{browser_name}"

    # Register one engine before creating context.
    await selectors.register(selector_name, tag_selector)

    context = await browser.new_context()
    # Register another engine after creating context.
    await selectors.register(selector2_name, tag_selector)

    page = await context.new_page()
    await page.set_content("<div><span></span></div><div></div>")

    assert (
        await page.eval_on_selector(f"{selector_name}=DIV", "e => e.nodeName") == "DIV"
    )
    assert (
        await page.eval_on_selector(f"{selector_name}=SPAN", "e => e.nodeName")
        == "SPAN"
    )
    assert (
        await page.eval_on_selector_all(f"{selector_name}=DIV", "es => es.length") == 2
    )

    assert (
        await page.eval_on_selector(f"{selector2_name}=DIV", "e => e.nodeName") == "DIV"
    )
    assert (
        await page.eval_on_selector(f"{selector2_name}=SPAN", "e => e.nodeName")
        == "SPAN"
    )
    assert (
        await page.eval_on_selector_all(f"{selector2_name}=DIV", "es => es.length") == 2
    )

    # Selector names are case-sensitive.
    with pytest.raises(Error) as exc:
        await page.query_selector("tAG=DIV")
    assert 'Unknown engine "tAG" while parsing selector tAG=DIV' in exc.value.message

    await context.close()


async def test_selectors_register_should_work_with_path(
    selectors: Selectors, page: Page, utils: Utils, assetdir: Path
) -> None:
    await utils.register_selector_engine(
        selectors, "foo", path=assetdir / "sectionselectorengine.js"
    )
    await page.set_content("<section></section>")
    assert await page.eval_on_selector("foo=whatever", "e => e.nodeName") == "SECTION"


async def test_selectors_register_should_work_in_main_and_isolated_world(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    dummy_selector_script = """{
      create(root, target) { },
      query(root, selector) {
        return window.__answer;
      },
      queryAll(root, selector) {
        return window['__answer'] ? [window['__answer'], document.body, document.documentElement] : [];
      }
    }"""

    await utils.register_selector_engine(selectors, "main", dummy_selector_script)
    await utils.register_selector_engine(
        selectors, "isolated", dummy_selector_script, content_script=True
    )
    await page.set_content("<div><span><section></section></span></div>")
    await page.evaluate('() => window.__answer = document.querySelector("span")')
    # Works in main if asked.
    assert await page.eval_on_selector("main=ignored", "e => e.nodeName") == "SPAN"
    assert (
        await page.eval_on_selector("css=div >> main=ignored", "e => e.nodeName")
        == "SPAN"
    )
    assert await page.eval_on_selector_all(
        "main=ignored", "es => window.__answer !== undefined"
    )
    assert (
        await page.eval_on_selector_all(
            "main=ignored", "es => es.filter(e => e).length"
        )
        == 3
    )
    # Works in isolated by default.
    assert await page.query_selector("isolated=ignored") is None
    assert await page.query_selector("css=div >> isolated=ignored") is None
    # $$eval always works in main, to avoid adopting nodes one by one.
    assert await page.eval_on_selector_all(
        "isolated=ignored", "es => window.__answer !== undefined"
    )
    assert (
        await page.eval_on_selector_all(
            "isolated=ignored", "es => es.filter(e => e).length"
        )
        == 3
    )
    # At least one engine in main forces all to be in main.
    assert (
        await page.eval_on_selector(
            "main=ignored >> isolated=ignored", "e => e.nodeName"
        )
        == "SPAN"
    )
    assert (
        await page.eval_on_selector(
            "isolated=ignored >> main=ignored", "e => e.nodeName"
        )
        == "SPAN"
    )
    # Can be chained to css.
    assert (
        await page.eval_on_selector("main=ignored >> css=section", "e => e.nodeName")
        == "SECTION"
    )


async def test_selectors_register_should_handle_errors(
    selectors: Selectors, page: Page, utils: Utils
) -> None:
    with pytest.raises(Error) as exc:
        await page.query_selector("neverregister=ignored")
    assert (
        'Unknown engine "neverregister" while parsing selector neverregister=ignored'
        in exc.value.message
    )

    dummy_selector_engine_script = """{
      create(root, target) {
        return target.nodeName;
      },
      query(root, selector) {
        return root.querySelector('dummy');
      },
      queryAll(root, selector) {
        return Array.from(root.query_selector_all('dummy'));
      }
    }"""

    with pytest.raises(Error) as exc:
        await selectors.register("$", dummy_selector_engine_script)
    assert (
        exc.value.message
        == "Selectors.register: Selector engine name may only contain [a-zA-Z0-9_] characters"
    )

    # Selector names are case-sensitive.
    await utils.register_selector_engine(
        selectors, "dummy", dummy_selector_engine_script
    )
    await utils.register_selector_engine(
        selectors, "duMMy", dummy_selector_engine_script
    )

    with pytest.raises(Error) as exc:
        await selectors.register("dummy", dummy_selector_engine_script)
    assert (
        exc.value.message
        == 'Selectors.register: "dummy" selector engine has been already registered'
    )

    with pytest.raises(Error) as exc:
        await selectors.register("css", dummy_selector_engine_script)
    assert (
        exc.value.message == 'Selectors.register: "css" is a predefined selector engine'
    )


async def test_should_work_with_layout_selectors(page: Page) -> None:
    #        +--+  +--+
    #        | 1|  | 2|
    #        +--+  ++-++
    #        | 3|   | 4|
    #   +-------+  ++-++
    #   |   0   |  | 5|
    #   | +--+  +--+--+
    #   | | 6|  | 7|
    #   | +--+  +--+
    #   |       |
    #   O-------+
    #           +--+
    #           | 8|
    #           +--++--+
    #               | 9|
    #               +--+

    boxes = [
        # x, y, width, height
        [0, 0, 150, 150],
        [100, 200, 50, 50],
        [200, 200, 50, 50],
        [100, 150, 50, 50],
        [201, 150, 50, 50],
        [200, 100, 50, 50],
        [50, 50, 50, 50],
        [150, 50, 50, 50],
        [150, -51, 50, 50],
        [201, -101, 50, 50],
    ]
    await page.set_content(
        '<container style="width: 500px; height: 500px; position: relative;"></container>'
    )
    await page.eval_on_selector(
        "container",
        """(container, boxes) => {
    for (let i = 0; i < boxes.length; i++) {
      const div = document.createElement('div');
      div.style.position = 'absolute';
      div.style.overflow = 'hidden';
      div.style.boxSizing = 'border-box';
      div.style.border = '1px solid black';
      div.id = 'id' + i;
      div.textContent = 'id' + i;
      const box = boxes[i];
      div.style.left = box[0] + 'px';
      // Note that top is a flipped y coordinate.
      div.style.top = (250 - box[1] - box[3]) + 'px';
      div.style.width = box[2] + 'px';
      div.style.height = box[3] + 'px';
      container.appendChild(div);
      const span = document.createElement('span');
      span.textContent = '' + i;
      div.appendChild(span);
    }
  }""",
        boxes,
    )

    assert await page.eval_on_selector("div:right-of(#id6)", "e => e.id") == "id7"
    assert await page.eval_on_selector("div:right-of(#id1)", "e => e.id") == "id2"
    assert await page.eval_on_selector("div:right-of(#id3)", "e => e.id") == "id4"
    assert await page.query_selector("div:right-of(#id4)") is None
    assert await page.eval_on_selector("div:right-of(#id0)", "e => e.id") == "id7"
    assert await page.eval_on_selector("div:right-of(#id8)", "e => e.id") == "id9"
    assert (
        await page.eval_on_selector_all(
            "div:right-of(#id3)", "els => els.map(e => e.id).join(',')"
        )
        == "id4,id2,id5,id7,id8,id9"
    )
    assert (
        await page.eval_on_selector_all(
            "div:right-of(#id3, 50)", "els => els.map(e => e.id).join(',')"
        )
        == "id2,id5,id7,id8"
    )
    assert (
        await page.eval_on_selector_all(
            "div:right-of(#id3, 49)", "els => els.map(e => e.id).join(',')"
        )
        == "id7,id8"
    )

    assert await page.eval_on_selector("div:left-of(#id2)", "e => e.id") == "id1"
    assert await page.query_selector("div:left-of(#id0)") is None
    assert await page.eval_on_selector("div:left-of(#id5)", "e => e.id") == "id0"
    assert await page.eval_on_selector("div:left-of(#id9)", "e => e.id") == "id8"
    assert await page.eval_on_selector("div:left-of(#id4)", "e => e.id") == "id3"
    assert (
        await page.eval_on_selector_all(
            "div:left-of(#id5)", "els => els.map(e => e.id).join(',')"
        )
        == "id0,id7,id3,id1,id6,id8"
    )
    assert (
        await page.eval_on_selector_all(
            "div:left-of(#id5, 3)", "els => els.map(e => e.id).join(',')"
        )
        == "id7,id8"
    )

    assert await page.eval_on_selector("div:above(#id0)", "e => e.id") == "id3"
    assert await page.eval_on_selector("div:above(#id5)", "e => e.id") == "id4"
    assert await page.eval_on_selector("div:above(#id7)", "e => e.id") == "id5"
    assert await page.eval_on_selector("div:above(#id8)", "e => e.id") == "id0"
    assert await page.eval_on_selector("div:above(#id9)", "e => e.id") == "id8"
    assert await page.query_selector("div:above(#id2)") is None
    assert (
        await page.eval_on_selector_all(
            "div:above(#id5)", "els => els.map(e => e.id).join(',')"
        )
        == "id4,id2,id3,id1"
    )
    assert (
        await page.eval_on_selector_all(
            "div:above(#id5, 20)", "els => els.map(e => e.id).join(',')"
        )
        == "id4,id3"
    )

    assert await page.eval_on_selector("div:below(#id4)", "e => e.id") == "id5"
    assert await page.eval_on_selector("div:below(#id3)", "e => e.id") == "id0"
    assert await page.eval_on_selector("div:below(#id2)", "e => e.id") == "id4"
    assert await page.eval_on_selector("div:below(#id6)", "e => e.id") == "id8"
    assert await page.eval_on_selector("div:below(#id7)", "e => e.id") == "id8"
    assert await page.eval_on_selector("div:below(#id8)", "e => e.id") == "id9"
    assert await page.query_selector("div:below(#id9)") is None
    assert (
        await page.eval_on_selector_all(
            "div:below(#id3)", "els => els.map(e => e.id).join(',')"
        )
        == "id0,id5,id6,id7,id8,id9"
    )
    assert (
        await page.eval_on_selector_all(
            "div:below(#id3, 105)", "els => els.map(e => e.id).join(',')"
        )
        == "id0,id5,id6,id7"
    )

    assert await page.eval_on_selector("div:near(#id0)", "e => e.id") == "id3"
    assert (
        await page.eval_on_selector_all(
            "div:near(#id7)", "els => els.map(e => e.id).join(',')"
        )
        == "id0,id5,id3,id6"
    )
    assert (
        await page.eval_on_selector_all(
            "div:near(#id0)", "els => els.map(e => e.id).join(',')"
        )
        == "id3,id6,id7,id8,id1,id5"
    )
    assert (
        await page.eval_on_selector_all(
            "div:near(#id6)", "els => els.map(e => e.id).join(',')"
        )
        == "id0,id3,id7"
    )
    assert (
        await page.eval_on_selector_all(
            "div:near(#id6, 10)", "els => els.map(e => e.id).join(',')"
        )
        == "id0"
    )
    assert (
        await page.eval_on_selector_all(
            "div:near(#id0, 100)", "els => els.map(e => e.id).join(',')"
        )
        == "id3,id6,id7,id8,id1,id5,id4,id2"
    )

    assert (
        await page.eval_on_selector_all(
            "div:below(#id5):above(#id8)", "els => els.map(e => e.id).join(',')"
        )
        == "id7,id6"
    )
    assert (
        await page.eval_on_selector("div:below(#id5):above(#id8)", "e => e.id") == "id7"
    )

    assert (
        await page.eval_on_selector_all(
            "div:right-of(#id0) + div:above(#id8)",
            "els => els.map(e => e.id).join(',')",
        )
        == "id5,id6,id3"
    )

    with pytest.raises(Error) as exc_info:
        await page.query_selector(":near(50)")
    assert (
        '"near" engine expects a selector list and optional maximum distance in pixels'
        in exc_info.value.message
    )
    with pytest.raises(Error) as exc_info:
        await page.query_selector('left-of="div"')
    assert '"left-of" selector cannot be first' in exc_info.value.message
