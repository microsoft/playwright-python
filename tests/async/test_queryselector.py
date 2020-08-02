from typing import Any, cast

import pytest

from playwright.helper import Error
from playwright.page import Page


async def test_selectors_register_should_work(selectors, page: Page, utils):
    await utils.register_selector_engine(
        selectors,
        "tag",
        """{
      create(root, target) {
        return target.nodeName;
      },
      query(root, selector) {
        return root.querySelector(selector);
      },
      queryAll(root, selector) {
        return Array.from(root.querySelectorAll(selector));
      }
    }""",
    )
    await page.setContent("<div><span></span></div><div></div>")
    assert (
        await selectors._impl_obj._createSelector(
            "tag", cast(Any, await page.querySelector("div"))._impl_obj
        )
        == "DIV"
    )
    assert await page.evalOnSelector("tag=DIV", "e => e.nodeName") == "DIV"
    assert await page.evalOnSelector("tag=SPAN", "e => e.nodeName") == "SPAN"
    assert await page.evalOnSelectorAll("tag=DIV", "es => es.length") == 2

    # Selector names are case-sensitive.
    with pytest.raises(Error) as exc:
        await page.querySelector("tAG=DIV")
    assert 'Unknown engine "tAG" while parsing selector tAG=DIV' in exc.value.message


async def test_selectors_register_should_work_with_path(
    selectors, page: Page, utils, assetdir
):
    await utils.register_selector_engine(
        selectors, "foo", path=assetdir / "sectionselectorengine.js"
    )
    await page.setContent("<section></section>")
    assert await page.evalOnSelector("foo=whatever", "e => e.nodeName") == "SECTION"


async def test_selectors_register_should_work_in_main_and_isolated_world(
    selectors, page: Page, utils
):
    dummy_selector_script = """{
      create(root, target) { },
      query(root, selector) {
        return window.__answer;
      },
      queryAll(root, selector) {
        return [document.body, document.documentElement, window.__answer];
      }
    }"""

    await utils.register_selector_engine(selectors, "main", dummy_selector_script)
    await utils.register_selector_engine(
        selectors, "isolated", dummy_selector_script, contentScript=True
    )
    await page.setContent("<div><span><section></section></span></div>")
    await page.evaluate('() => window.__answer = document.querySelector("span")')
    # Works in main if asked.
    assert await page.evalOnSelector("main=ignored", "e => e.nodeName") == "SPAN"
    assert (
        await page.evalOnSelector("css=div >> main=ignored", "e => e.nodeName")
        == "SPAN"
    )
    assert await page.evalOnSelectorAll(
        "main=ignored", "es => window.__answer !== undefined"
    )
    assert (
        await page.evalOnSelectorAll("main=ignored", "es => es.filter(e => e).length")
        == 3
    )
    # Works in isolated by default.
    assert await page.querySelector("isolated=ignored") is None
    assert await page.querySelector("css=div >> isolated=ignored") is None
    # $$eval always works in main, to avoid adopting nodes one by one.
    assert await page.evalOnSelectorAll(
        "isolated=ignored", "es => window.__answer !== undefined"
    )
    assert (
        await page.evalOnSelectorAll(
            "isolated=ignored", "es => es.filter(e => e).length"
        )
        == 3
    )
    # At least one engine in main forces all to be in main.
    assert (
        await page.evalOnSelector("main=ignored >> isolated=ignored", "e => e.nodeName")
        == "SPAN"
    )
    assert (
        await page.evalOnSelector("isolated=ignored >> main=ignored", "e => e.nodeName")
        == "SPAN"
    )
    # Can be chained to css.
    assert (
        await page.evalOnSelector("main=ignored >> css=section", "e => e.nodeName")
        == "SECTION"
    )


async def test_selectors_register_should_handle_errors(selectors, page: Page, utils):
    with pytest.raises(Error) as exc:
        await page.querySelector("neverregister=ignored")
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
        return Array.from(root.querySelectorAll('dummy'));
      }
    }"""

    with pytest.raises(Error) as exc:
        await selectors.register("$", dummy_selector_engine_script)
    assert (
        "Selector engine name may only contain [a-zA-Z0-9_] characters"
        == exc.value.message
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
    assert exc.value.message == '"dummy" selector engine has been already registered'

    with pytest.raises(Error) as exc:
        await selectors.register("css", dummy_selector_engine_script)
    assert exc.value.message == '"css" is a predefined selector engine'
