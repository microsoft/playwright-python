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

"""Port of tests/library/selectors-register.spec.ts."""

from pathlib import Path

import pytest

from playwright.sync_api import Browser, Error, Selectors

from ..utils import Utils

# The engines are registered on the session's playwright.selectors, so a test that
# runs again in the same session finds its engine already registered: register them
# through utils.register_selector_engine, which ignores that error. The tests that
# check the registration errors call selectors.register directly.

# The JavaScript client sends a function engine as "(<function source>)()".
CREATE_TAG_SELECTOR = """(() => ({
  query(root, selector) {
    return root.querySelector(selector);
  },
  queryAll(root, selector) {
    return Array.from(root.querySelectorAll(selector));
  }
}))()"""


def test_SE_160_should_work(
    selectors: Selectors, browser: Browser, utils: Utils
) -> None:
    # Register one engine before creating context.
    utils.register_selector_engine(selectors, "tag", CREATE_TAG_SELECTOR)

    context = browser.new_context()
    # Register another engine after creating context.
    utils.register_selector_engine(selectors, "tag2", CREATE_TAG_SELECTOR)

    page = context.new_page()
    page.set_content("<div><span></span></div><div></div>")

    assert page.eval_on_selector("tag=DIV", "e => e.nodeName") == "DIV"
    assert page.eval_on_selector("tag=SPAN", "e => e.nodeName") == "SPAN"
    assert page.eval_on_selector_all("tag=DIV", "es => es.length") == 2

    assert page.eval_on_selector("tag2=DIV", "e => e.nodeName") == "DIV"
    assert page.eval_on_selector("tag2=SPAN", "e => e.nodeName") == "SPAN"
    assert page.eval_on_selector_all("tag2=DIV", "es => es.length") == 2

    # Selector names are case-sensitive.
    with pytest.raises(Error) as exc_info:
        page.query_selector("tAG=DIV")
    assert (
        'Unknown engine "tAG" while parsing selector tAG=DIV' in exc_info.value.message
    )

    context.close()


def test_SE_161_should_work_when_registered_on_global(
    selectors: Selectors, browser: Browser, utils: Utils
) -> None:
    # Upstream registers on require('@playwright/test').selectors, the selectors of
    # the Playwright instance that launched the browser. Python has no global
    # selectors: that instance is the session's playwright.selectors.
    utils.register_selector_engine(selectors, "oop-tag", CREATE_TAG_SELECTOR)

    context = browser.new_context()
    # Register another engine after creating context.
    utils.register_selector_engine(selectors, "oop-tag2", CREATE_TAG_SELECTOR)

    page = context.new_page()
    page.set_content("<div><span></span></div><div></div>")

    assert page.eval_on_selector("oop-tag=DIV", "e => e.nodeName") == "DIV"
    assert page.eval_on_selector("oop-tag=SPAN", "e => e.nodeName") == "SPAN"
    assert page.eval_on_selector_all("oop-tag=DIV", "es => es.length") == 2

    assert page.eval_on_selector("oop-tag2=DIV", "e => e.nodeName") == "DIV"
    assert page.eval_on_selector("oop-tag2=SPAN", "e => e.nodeName") == "SPAN"
    assert page.eval_on_selector_all("oop-tag2=DIV", "es => es.length") == 2

    context.close()


def test_SE_162_should_work_with_path(
    selectors: Selectors, browser: Browser, utils: Utils, assetdir: Path
) -> None:
    utils.register_selector_engine(
        selectors, "foo", path=assetdir / "sectionselectorengine.js"
    )
    page = browser.new_page()
    page.set_content("<section></section>")
    assert page.eval_on_selector("foo=whatever", "e => e.nodeName") == "SECTION"
    page.close()


def test_SE_163_should_work_in_main_and_isolated_world(
    selectors: Selectors, browser: Browser, utils: Utils
) -> None:
    create_dummy_selector = """(() => ({
      query(root, selector) {
        return window['__answer'];
      },
      queryAll(root, selector) {
        return window['__answer'] ? [window['__answer'], document.body, document.documentElement] : [];
      }
    }))()"""
    utils.register_selector_engine(selectors, "main", create_dummy_selector)
    utils.register_selector_engine(
        selectors, "isolated", create_dummy_selector, content_script=True
    )
    page = browser.new_page()
    page.set_content("<div><span><section></section></span></div>")
    page.evaluate("() => window['__answer'] = document.querySelector('span')")
    # Works in main if asked.
    assert page.eval_on_selector("main=ignored", "e => e.nodeName") == "SPAN"
    assert page.eval_on_selector("css=div >> main=ignored", "e => e.nodeName") == "SPAN"
    assert (
        page.eval_on_selector_all(
            "main=ignored", "es => window['__answer'] !== undefined"
        )
        is True
    )
    assert (
        page.eval_on_selector_all("main=ignored", "es => es.filter(e => e).length") == 3
    )
    # Works in isolated by default.
    assert page.query_selector("isolated=ignored") is None
    assert page.query_selector("css=div >> isolated=ignored") is None
    # $$eval always works in main, to avoid adopting nodes one by one.
    assert (
        page.eval_on_selector_all(
            "isolated=ignored", "es => window['__answer'] !== undefined"
        )
        is True
    )
    assert (
        page.eval_on_selector_all("isolated=ignored", "es => es.filter(e => e).length")
        == 3
    )
    # At least one engine in main forces all to be in main.
    assert (
        page.eval_on_selector("main=ignored >> isolated=ignored", "e => e.nodeName")
        == "SPAN"
    )
    assert (
        page.eval_on_selector("isolated=ignored >> main=ignored", "e => e.nodeName")
        == "SPAN"
    )
    # Can be chained to css.
    assert (
        page.eval_on_selector("main=ignored >> css=section", "e => e.nodeName")
        == "SECTION"
    )
    page.close()


def test_SE_164_should_handle_errors(
    selectors: Selectors, browser: Browser, utils: Utils
) -> None:
    page = browser.new_page()
    with pytest.raises(Error) as exc_info:
        page.query_selector("neverregister=ignored")
    assert (
        'Unknown engine "neverregister" while parsing selector neverregister=ignored'
        in exc_info.value.message
    )

    create_dummy_selector = """(() => ({
      query(root, selector) {
        return root.querySelector('dummy');
      },
      queryAll(root, selector) {
        return Array.from(root.querySelectorAll('dummy'));
      }
    }))()"""

    with pytest.raises(Error) as exc_info:
        selectors.register("$", create_dummy_selector)
    assert (
        exc_info.value.message
        == "Selectors.register: Selector engine name may only contain [a-zA-Z0-9_] characters"
    )

    # Selector names are case-sensitive.
    utils.register_selector_engine(selectors, "dummy", create_dummy_selector)
    utils.register_selector_engine(selectors, "duMMy", create_dummy_selector)

    with pytest.raises(Error) as exc_info:
        selectors.register("dummy", create_dummy_selector)
    assert (
        exc_info.value.message
        == 'Selectors.register: "dummy" selector engine has been already registered'
    )

    with pytest.raises(Error) as exc_info:
        selectors.register("css", create_dummy_selector)
    assert (
        exc_info.value.message
        == 'Selectors.register: "css" is a predefined selector engine'
    )
    page.close()


def test_SE_165_should_throw_already_registered_error_when_registering(
    selectors: Selectors, utils: Utils
) -> None:
    # https://github.com/microsoft/playwright/issues/36467
    utils.register_selector_engine(selectors, "alreadyRegistered", CREATE_TAG_SELECTOR)
    with pytest.raises(Error) as exc_info:
        selectors.register("alreadyRegistered", CREATE_TAG_SELECTOR)
    assert (
        'Selectors.register: "alreadyRegistered" selector engine has been already registered'
        in exc_info.value.message
    )


def test_SE_166_should_not_rely_on_engines_working_from_the_root(
    selectors: Selectors, browser: Browser, utils: Utils
) -> None:
    create_value_engine = """(() => ({
      query(root, selector) {
        return root && root.value.includes(selector) ? root : undefined;
      },
      queryAll(root, selector) {
        return root && root.value.includes(selector) ? [root] : [];
      },
    }))()"""
    utils.register_selector_engine(selectors, "__value", create_value_engine)
    page = browser.new_page()
    page.set_content("<input id=input1 value=value1><input id=input2 value=value2>")
    assert page.eval_on_selector("input >> __value=value2", "e => e.id") == "input2"
    page.close()


def test_SE_167_should_throw_a_nice_error_if_the_selector_returns_a_bad_value(
    selectors: Selectors, browser: Browser, utils: Utils
) -> None:
    create_fake_engine = """(() => ({
      query(root, selector) {
        return [document.body];
      },
      queryAll(root, selector) {
        return [[document.body]];
      },
    }))()"""

    utils.register_selector_engine(selectors, "__fake", create_fake_engine)
    page = browser.new_page()
    with pytest.raises(Error) as exc_info:
        page.query_selector("__fake=value2")
    assert "Expected a Node but got [object Array]" in exc_info.value.message
    page.close()
