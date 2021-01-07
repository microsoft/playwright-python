import pytest

from playwright.async_api import Error, Page


async def test_selectors_register_should_work(selectors, browser):
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

    # Register one engine before creating context.
    await selectors.register("tag", tag_selector)

    context = await browser.new_context()
    # Register another engine after creating context.
    await selectors.register("tag2", tag_selector)

    page = await context.new_page()
    await page.set_content("<div><span></span></div><div></div>")

    assert await page.eval_on_selector("tag=DIV", "e => e.nodeName") == "DIV"
    assert await page.eval_on_selector("tag=SPAN", "e => e.nodeName") == "SPAN"
    assert await page.eval_on_selector_all("tag=DIV", "es => es.length") == 2

    assert await page.eval_on_selector("tag2=DIV", "e => e.nodeName") == "DIV"
    assert await page.eval_on_selector("tag2=SPAN", "e => e.nodeName") == "SPAN"
    assert await page.eval_on_selector_all("tag2=DIV", "es => es.length") == 2

    # Selector names are case-sensitive.
    with pytest.raises(Error) as exc:
        await page.query_selector("tAG=DIV")
    assert 'Unknown engine "tAG" while parsing selector tAG=DIV' in exc.value.message

    await context.close()


async def test_selectors_register_should_work_with_path(
    selectors, page: Page, utils, assetdir
):
    await utils.register_selector_engine(
        selectors, "foo", path=assetdir / "sectionselectorengine.js"
    )
    await page.set_content("<section></section>")
    assert await page.eval_on_selector("foo=whatever", "e => e.nodeName") == "SECTION"


async def test_selectors_register_should_work_in_main_and_isolated_world(
    selectors, page: Page, utils
):
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


async def test_selectors_register_should_handle_errors(selectors, page: Page, utils):
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
        == "Selector engine name may only contain [a-zA-Z0-9_] characters"
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
