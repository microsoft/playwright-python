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

import asyncio
import os
import pytest
import re
from playwright import Error, TimeoutError

__dirname = os.path.dirname(os.path.realpath(__file__))


async def test_close_should_reject_all_promises(context):
    new_page = await context.newPage()
    with pytest.raises(Error) as exc_info:
        await asyncio.gather(
            new_page.evaluate("() => new Promise(r => {})"), new_page.close()
        )
    assert "Protocol error" in exc_info.value.message


async def test_closed_should_not_visible_in_context_pages(context):
    page = await context.newPage()
    assert page in context.pages
    await page.close()
    assert page not in context.pages


async def test_close_should_run_beforeunload_if_asked_for(
    context, server, is_chromium, is_webkit
):
    page = await context.newPage()
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    page_closing_future = asyncio.ensure_future(page.close(runBeforeUnload=True))
    dialog = await page.waitForEvent("dialog")
    assert dialog.type == "beforeunload"
    assert dialog.defaultValue == ""
    if is_chromium:
        assert dialog.message == ""
    elif is_webkit:
        assert dialog.message == "Leave?"
    else:
        assert (
            dialog.message
            == "This page is asking you to confirm that you want to leave - data you have entered may not be saved."
        )
    await dialog.accept()
    await page_closing_future


async def test_close_should_not_run_beforeunload_by_default(context, server):
    page = await context.newPage()
    await page.goto(server.PREFIX + "/beforeunload.html")
    # We have to interact with a page so that 'beforeunload' handlers
    # fire.
    await page.click("body")
    await page.close()


async def test_close_should_set_the_page_close_state(context):
    page = await context.newPage()
    assert page.isClosed() is False
    await page.close()
    assert page.isClosed()


async def test_close_should_terminate_network_waiters(context, server):
    page = await context.newPage()

    async def wait_for_request():
        try:
            await page.waitForRequest(server.EMPTY_PAGE)
        except Error as e:
            return e

    async def wait_for_response():
        try:
            await page.waitForResponse(server.EMPTY_PAGE)
        except Error as e:
            return e

    results = await asyncio.gather(
        wait_for_request(), wait_for_response(), page.close()
    )
    for i in range(2):
        error = results[i]
        assert "Page closed" in error.message
        assert "Timeout" not in error.message


async def test_close_should_be_callable_twice(context):
    page = await context.newPage()
    await asyncio.gather(
        page.close(), page.close(),
    )
    await page.close()


async def test_load_should_fire_when_expected(page):
    await asyncio.gather(
        page.goto("about:blank"), page.waitForEvent("load"),
    )


async def test_async_stacks_should_work(page, server):
    await page.route(
        "**/empty.html", lambda route, response: asyncio.ensure_future(route.abort())
    )
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    assert __file__ in exc_info.value.stack


# TODO: bring in page.crash events


async def test_opener_should_provide_access_to_the_opener_page(page):
    [popup, _] = await asyncio.gather(
        page.waitForEvent("popup"), page.evaluate("window.open('about:blank')"),
    )
    opener = await popup.opener()
    assert opener == page


async def test_opener_should_return_null_if_parent_page_has_been_closed(page):
    [popup, _] = await asyncio.gather(
        page.waitForEvent("popup"), page.evaluate("window.open('about:blank')"),
    )
    await page.close()
    opener = await popup.opener()
    assert opener is None


async def test_domcontentloaded_should_fire_when_expected(page, server):
    future = asyncio.ensure_future(page.goto("about:blank"))
    await page.waitForEvent("domcontentloaded")
    await future


async def test_wait_for_request(page, server):
    await page.goto(server.EMPTY_PAGE)
    [request, _] = await asyncio.gather(
        page.waitForRequest(server.PREFIX + "/digits/2.png"),
        page.evaluate(
            """() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }"""
        ),
    )
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_wait_for_request_should_work_with_predicate(page, server):
    await page.goto(server.EMPTY_PAGE)
    [request, _] = await asyncio.gather(
        page.waitForEvent(
            "request", lambda request: request.url == server.PREFIX + "/digits/2.png"
        ),
        page.evaluate(
            """() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }"""
        ),
    )
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_wait_for_request_should_timeout(page, server):
    with pytest.raises(Error) as exc_info:
        await page.waitForEvent("request", timeout=1)
    assert exc_info.type is TimeoutError


async def test_wait_for_request_should_respect_default_timeout(page, server):
    page.setDefaultTimeout(1)
    with pytest.raises(Error) as exc_info:
        await page.waitForEvent("request", lambda _: False)
    assert exc_info.type is TimeoutError


async def test_wait_for_request_should_work_with_no_timeout(page, server):
    await page.goto(server.EMPTY_PAGE)
    [request, _] = await asyncio.gather(
        page.waitForRequest(server.PREFIX + "/digits/2.png", timeout=0),
        page.evaluate(
            """() => setTimeout(() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }, 50)"""
        ),
    )
    assert request.url == server.PREFIX + "/digits/2.png"


async def test_wait_for_request_should_work_with_url_match(page, server):
    await page.goto(server.EMPTY_PAGE)
    [request, _] = await asyncio.gather(
        page.waitForRequest(re.compile(r"digits\/\d\.png")),
        page.evaluate("fetch('/digits/1.png')"),
    )
    assert request.url == server.PREFIX + "/digits/1.png"


async def test_wait_for_event_should_fail_with_error_upon_disconnect(page, server):
    future = asyncio.ensure_future(page.waitForEvent("download"))
    await page.close()
    with pytest.raises(Error) as exc_info:
        await future
    assert "Page closed" in exc_info.value.message


async def test_wait_for_response_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    [response, _] = await asyncio.gather(
        page.waitForResponse(server.PREFIX + "/digits/2.png"),
        page.evaluate(
            """() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }"""
        ),
    )
    assert response.url == server.PREFIX + "/digits/2.png"


async def test_wait_for_response_should_respect_timeout(page, server):
    with pytest.raises(Error) as exc_info:
        await page.waitForEvent("response", timeout=1)
    assert exc_info.type is TimeoutError


async def test_wait_for_response_should_respect_default_timeout(page, server):
    page.setDefaultTimeout(1)
    with pytest.raises(Error) as exc_info:
        await page.waitForEvent("response", lambda _: False)
    assert exc_info.type is TimeoutError


async def test_wait_for_response_should_work_with_predicate(page, server):
    await page.goto(server.EMPTY_PAGE)
    [response, _] = await asyncio.gather(
        page.waitForEvent(
            "response", lambda response: response.url == server.PREFIX + "/digits/2.png"
        ),
        page.evaluate(
            """() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }"""
        ),
    )
    assert response.url == server.PREFIX + "/digits/2.png"


async def test_wait_for_response_should_work_with_no_timeout(page, server):
    await page.goto(server.EMPTY_PAGE)
    [response, _] = await asyncio.gather(
        page.waitForResponse(server.PREFIX + "/digits/2.png", timeout=0),
        page.evaluate(
            """() => setTimeout(() => {
                fetch('/digits/1.png')
                fetch('/digits/2.png')
                fetch('/digits/3.png')
            }, 50)"""
        ),
    )
    assert response.url == server.PREFIX + "/digits/2.png"


async def test_expose_binding(page):
    binding_source = []

    def binding(source, a, b):
        binding_source.append(source)
        return a + b

    await page.exposeBinding("add", lambda source, a, b: binding(source, a, b))

    result = await page.evaluate("add(5, 6)")

    assert binding_source[0]["context"] == page.context
    assert binding_source[0]["page"] == page
    assert binding_source[0]["frame"] == page.mainFrame
    assert result == 11


async def test_expose_function(page, server):
    await page.exposeFunction("compute", lambda a, b: a * b)
    result = await page.evaluate("compute(9, 4)")
    assert result == 36


async def test_expose_function_should_throw_exception_in_page_context(page, server):
    def throw():
        raise Exception("WOOF WOOF")

    await page.exposeFunction("woof", lambda: throw())
    result = await page.evaluate(
        """async() => {
            try {
                await woof()
            } catch (e) {
                return {message: e.message, stack: e.stack}
            }
        }"""
    )
    assert result["message"] == "WOOF WOOF"
    assert __file__ in result["stack"]


async def test_expose_function_should_be_callable_from_inside_add_init_script(page):
    called = []
    await page.exposeFunction("woof", lambda: called.append(True))
    await page.addInitScript("woof()")
    await page.reload()
    assert called == [True]


async def test_expose_function_should_survive_navigation(page, server):
    await page.exposeFunction("compute", lambda a, b: a * b)
    await page.goto(server.EMPTY_PAGE)
    result = await page.evaluate("compute(9, 4)")
    assert result == 36


async def test_expose_function_should_await_returned_promise(page):
    async def mul(a, b):
        return a * b

    await page.exposeFunction("compute", lambda a, b: asyncio.ensure_future(mul(a, b)))
    assert await page.evaluate("compute(3, 5)") == 15


async def test_expose_function_should_work_on_frames(page, server):
    await page.exposeFunction("compute", lambda a, b: a * b)
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    frame = page.frames[1]
    assert await frame.evaluate("compute(3, 5)") == 15


async def test_expose_function_should_work_on_frames_before_navigation(page, server):
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    await page.exposeFunction("compute", lambda a, b: a * b)
    frame = page.frames[1]
    assert await frame.evaluate("compute(3, 5)") == 15


async def test_expose_function_should_work_after_cross_origin_navigation(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.exposeFunction("compute", lambda a, b: a * b)
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert await page.evaluate("compute(9, 4)") == 36


async def test_expose_function_should_work_with_complex_objects(page, server):
    await page.exposeFunction("complexObject", lambda a, b: dict(x=a["x"] + b["x"]))
    result = await page.evaluate("complexObject({x: 5}, {x: 2})")
    assert result["x"] == 7


async def test_page_error_should_fire(page, server, is_webkit):
    [error, _] = await asyncio.gather(
        page.waitForEvent("pageerror"), page.goto(server.PREFIX + "/error.html"),
    )
    assert error.message == "Fancy error!"
    stack = await page.evaluate("window.e.stack")
    # Note that WebKit reports the stack of the 'throw' statement instead of the Error constructor call.
    if is_webkit:
        stack = stack.replace("14:25", "15:19")
    assert error.stack == stack


async def test_page_error_should_handle_odd_values(page, is_firefox):
    cases = [["null", "null"], ["undefined", "undefined"], ["0", "0"], ['""', ""]]
    for [value, message] in cases:
        [error, _] = await asyncio.gather(
            page.waitForEvent("pageerror"),
            page.evaluate(f"() => setTimeout(() => {{ throw {value}; }}, 0)"),
        )
        assert (
            error.message == ("uncaught exception: " + message) if is_firefox else value
        )


@pytest.mark.skip_browser("firefox")
async def test_page_error_should_handle_object(page, is_chromium):
    # Firefox just does not report this error.
    [error, _] = await asyncio.gather(
        page.waitForEvent("pageerror"),
        page.evaluate("() => setTimeout(() => { throw {}; }, 0)"),
    )
    assert error.message == "Object" if is_chromium else "[object Object]"


@pytest.mark.skip_browser("firefox")
async def test_page_error_should_handle_window(page, is_chromium):
    # Firefox just does not report this error.
    [error, _] = await asyncio.gather(
        page.waitForEvent("pageerror"),
        page.evaluate("() => setTimeout(() => { throw window; }, 0)"),
    )
    assert error.message == "Window" if is_chromium else "[object Window]"


expected_output = "<html><head></head><body><div>hello</div></body></html>"


async def test_set_content_should_work(page, server):
    await page.setContent("<div>hello</div>")
    result = await page.content()
    assert result == expected_output


async def test_set_content_should_work_with_domcontentloaded(page, server):
    await page.setContent("<div>hello</div>", waitUntil="domcontentloaded")
    result = await page.content()
    assert result == expected_output


async def test_set_content_should_work_with_doctype(page, server):
    doctype = "<!DOCTYPE html>"
    await page.setContent(f"{doctype}<div>hello</div>")
    result = await page.content()
    assert result == f"{doctype}{expected_output}"


async def test_set_content_should_work_with_HTML_4_doctype(page, server):
    doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
    await page.setContent(f"{doctype}<div>hello</div>")
    result = await page.content()
    assert result == f"{doctype}{expected_output}"


async def test_set_content_should_respect_timeout(page, server):
    img_path = "/img.png"
    # stall for image
    server.set_route(img_path, lambda request: None)
    with pytest.raises(Error) as exc_info:
        await page.setContent(
            '<img src="${server.PREFIX + img_path}"></img>', timeout=1
        )
    assert exc_info.type is TimeoutError


async def test_set_content_should_respect_default_navigation_timeout(page, server):
    page.setDefaultNavigationTimeout(1)
    img_path = "/img.png"
    # stall for image
    await page.route(img_path, lambda route, request: None)

    with pytest.raises(Error) as exc_info:
        await page.setContent(f'<img src="{server.PREFIX + img_path}"></img>')
    assert "Timeout 1ms exceeded during" in exc_info.value.message
    assert exc_info.type is TimeoutError


async def test_set_content_should_await_resources_to_load(page, server):
    img_path = "/img.png"
    img_route = asyncio.Future()
    await page.route(img_path, lambda route, request: img_route.set_result(route))
    loaded = []

    async def load():
        await page.setContent(f'<img src="{server.PREFIX + img_path}"></img>')
        loaded.append(True)

    content_promise = asyncio.ensure_future(load())
    route = await img_route
    assert loaded == []
    asyncio.ensure_future(route.continue_())
    await content_promise


async def test_set_content_should_work_with_tricky_content(page):
    await page.setContent("<div>hello world</div>" + "\x7F")
    assert await page.evalOnSelector("div", "div => div.textContent") == "hello world"


async def test_set_content_should_work_with_accents(page):
    await page.setContent("<div>aberración</div>")
    assert await page.evalOnSelector("div", "div => div.textContent") == "aberración"


async def test_set_content_should_work_with_emojis(page):
    await page.setContent("<div>🐥</div>")
    assert await page.evalOnSelector("div", "div => div.textContent") == "🐥"


async def test_set_content_should_work_with_newline(page):
    await page.setContent("<div>\n</div>")
    assert await page.evalOnSelector("div", "div => div.textContent") == "\n"


async def test_add_script_tag_should_work_with_a_url(page, server):
    await page.goto(server.EMPTY_PAGE)
    script_handle = await page.addScriptTag(url="/injectedfile.js")
    assert script_handle.asElement()
    assert await page.evaluate("__injected") == 42


async def test_add_script_tag_should_work_with_a_url_and_type_module(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.addScriptTag(url="/es6/es6import.js", type="module")
    assert await page.evaluate("__es6injected") == 42


async def test_add_script_tag_should_work_with_a_path_and_type_module(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.addScriptTag(
        path=os.path.join(__dirname, "assets", "es6", "es6pathimport.js"), type="module"
    )
    await page.waitForFunction("window.__es6injected")
    assert await page.evaluate("__es6injected") == 42


async def test_add_script_tag_should_work_with_a_content_and_type_module(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.addScriptTag(
        content="import num from '/es6/es6module.js';window.__es6injected = num;",
        type="module",
    )
    await page.waitForFunction("window.__es6injected")
    assert await page.evaluate("__es6injected") == 42


async def test_add_script_tag_should_throw_an_error_if_loading_from_url_fail(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        await page.addScriptTag(url="/nonexistfile.js")
    assert exc_info.value


async def test_add_script_tag_should_work_with_a_path(page, server):
    await page.goto(server.EMPTY_PAGE)
    script_handle = await page.addScriptTag(
        path=os.path.join(__dirname, "assets", "injectedfile.js")
    )
    assert script_handle.asElement()
    assert await page.evaluate("__injected") == 42


@pytest.mark.skip_browser("webkit")
async def test_add_script_tag_should_include_source_url_when_path_is_provided(
    page, server
):
    # Lacking sourceURL support in WebKit
    await page.goto(server.EMPTY_PAGE)
    await page.addScriptTag(path=os.path.join(__dirname, "assets", "injectedfile.js"))
    result = await page.evaluate("__injectedError.stack")
    assert os.path.join("assets", "injectedfile.js") in result


async def test_add_script_tag_should_work_with_content(page, server):
    await page.goto(server.EMPTY_PAGE)
    script_handle = await page.addScriptTag(content="window.__injected = 35;")
    assert script_handle.asElement()
    assert await page.evaluate("__injected") == 35


@pytest.mark.skip_browser("firefox")
async def test_add_script_tag_should_throw_when_added_with_content_to_the_csp_page(
    page, server
):
    # Firefox fires onload for blocked script before it issues the CSP console error.
    await page.goto(server.PREFIX + "/csp.html")
    with pytest.raises(Error) as exc_info:
        await page.addScriptTag(content="window.__injected = 35;")
    assert exc_info.value


async def test_add_script_tag_should_throw_when_added_with_URL_to_the_csp_page(
    page, server
):
    await page.goto(server.PREFIX + "/csp.html")
    with pytest.raises(Error) as exc_info:
        await page.addScriptTag(url=server.CROSS_PROCESS_PREFIX + "/injectedfile.js")
    assert exc_info.value


async def test_add_script_tag_should_throw_a_nice_error_when_the_request_fails(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/this_does_not_exist.js"
    with pytest.raises(Error) as exc_info:
        await page.addScriptTag(url=url)
    assert url in exc_info.value.message


async def test_add_style_tag_should_work_with_a_url(page, server):
    await page.goto(server.EMPTY_PAGE)
    style_handle = await page.addStyleTag(url="/injectedstyle.css")
    assert style_handle.asElement()
    assert (
        await page.evaluate(
            "window.getComputedStyle(document.querySelector('body')).getPropertyValue('background-color')"
        )
        == "rgb(255, 0, 0)"
    )


async def test_add_style_tag_should_throw_an_error_if_loading_from_url_fail(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        await page.addStyleTag(url="/nonexistfile.js")
    assert exc_info.value


async def test_add_style_tag_should_work_with_a_path(page, server):
    await page.goto(server.EMPTY_PAGE)
    style_handle = await page.addStyleTag(
        path=os.path.join(__dirname, "assets", "injectedstyle.css")
    )
    assert style_handle.asElement()
    assert (
        await page.evaluate(
            "window.getComputedStyle(document.querySelector('body')).getPropertyValue('background-color')"
        )
        == "rgb(255, 0, 0)"
    )


async def test_add_style_tag_should_include_sourceURL_when_path_is_provided(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.addStyleTag(path=os.path.join(__dirname, "assets", "injectedstyle.css"))
    style_handle = await page.querySelector("style")
    style_content = await page.evaluate("style => style.innerHTML", style_handle)
    assert os.path.join("assets", "injectedstyle.css") in style_content


async def test_add_style_tag_should_work_with_content(page, server):
    await page.goto(server.EMPTY_PAGE)
    style_handle = await page.addStyleTag(content="body { background-color: green; }")
    assert style_handle.asElement()
    assert (
        await page.evaluate(
            "window.getComputedStyle(document.querySelector('body')).getPropertyValue('background-color')"
        )
        == "rgb(0, 128, 0)"
    )


async def test_add_style_tag_should_throw_when_added_with_content_to_the_CSP_page(
    page, server
):
    await page.goto(server.PREFIX + "/csp.html")
    with pytest.raises(Error) as exc_info:
        await page.addStyleTag(content="body { background-color: green; }")
    assert exc_info.value


async def test_add_style_tag_should_throw_when_added_with_URL_to_the_CSP_page(
    page, server
):
    await page.goto(server.PREFIX + "/csp.html")
    with pytest.raises(Error) as exc_info:
        await page.addStyleTag(url=server.CROSS_PROCESS_PREFIX + "/injectedstyle.css")
    assert exc_info.value


async def test_url_should_work(page, server):
    assert page.url == "about:blank"
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE


async def test_url_should_include_hashes(page, server):
    await page.goto(server.EMPTY_PAGE + "#hash")
    assert page.url == server.EMPTY_PAGE + "#hash"
    await page.evaluate("window.location.hash = 'dynamic'")
    assert page.url == server.EMPTY_PAGE + "#dynamic"


async def test_title_should_return_the_page_title(page, server):
    await page.goto(server.PREFIX + "/title.html")
    assert await page.title() == "Woof-Woof"


async def test_select_option_should_select_single_option(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", "blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_option_should_select_single_option_by_value(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", {"value": "blue"})
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_option_should_select_single_option_by_label(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", {"label": "Indigo"})
    assert await page.evaluate("result.onInput") == ["indigo"]
    assert await page.evaluate("result.onChange") == ["indigo"]


async def test_select_option_should_select_single_option_by_handle(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", await page.querySelector("[id=whiteOption]"))
    assert await page.evaluate("result.onInput") == ["white"]
    assert await page.evaluate("result.onChange") == ["white"]


async def test_select_option_should_select_single_option_by_index(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", {"index": 2})
    assert await page.evaluate("result.onInput") == ["brown"]
    assert await page.evaluate("result.onChange") == ["brown"]


async def test_select_option_should_select_single_option_by_multiple_attributes(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", {"value": "green", "label": "Green"})
    assert await page.evaluate("result.onInput") == ["green"]
    assert await page.evaluate("result.onChange") == ["green"]


async def test_select_option_should_not_select_single_option_when_some_attributes_do_not_match(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", {"value": "green", "label": "Brown"})
    assert await page.evaluate("document.querySelector('select').value") == ""


async def test_select_option_should_select_only_first_option(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", "blue", "green", "red")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]


async def test_select_option_should_not_throw_when_select_causes_navigation(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evalOnSelector(
        "select",
        "select => select.addEventListener('input', () => window.location = '/empty.html')",
    )
    await asyncio.gather(
        page.selectOption("select", "blue"), page.waitForNavigation(),
    )
    assert "empty.html" in page.url


async def test_select_option_should_select_multiple_options(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    await page.selectOption("select", ["blue", "green", "red"])
    assert await page.evaluate("result.onInput") == ["blue", "green", "red"]
    assert await page.evaluate("result.onChange") == ["blue", "green", "red"]


async def test_select_option_should_select_multiple_options_with_attributes(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    await page.selectOption("select", ["blue", {"label": "Green"}, {"index": 4}])
    assert await page.evaluate("result.onInput") == ["blue", "gray", "green"]
    assert await page.evaluate("result.onChange") == ["blue", "gray", "green"]


async def test_select_option_should_respect_event_bubbling(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", "blue")
    assert await page.evaluate("result.onBubblingInput") == ["blue"]
    assert await page.evaluate("result.onBubblingChange") == ["blue"]


async def test_select_option_should_throw_when_element_is_not_a__select_(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    with pytest.raises(Error) as exc_info:
        await page.selectOption("body", "")
    assert "Element is not a <select> element." in exc_info.value.message


async def test_select_option_should_return_on_no_matched_values(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.selectOption("select", ["42", "abc"])
    assert result == []


async def test_select_option_should_return_an_array_of_matched_values(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    result = await page.selectOption("select", ["blue", "black", "magenta"])
    assert result == ["black", "blue", "magenta"]


async def test_select_option_should_return_an_array_of_one_element_when_multiple_is_not_set(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.selectOption("select", ["42", "blue", "black", "magenta"])
    assert len(result) == 1


async def test_select_option_should_return_on_no_values(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    result = await page.selectOption("select", [])
    assert result == []


async def test_select_option_should_not_allow_null_items(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    with pytest.raises(Error) as exc_info:
        await page.selectOption("select", ["blue", None, "black", "magenta"])
    assert "Value items must not be null" in exc_info.value.message


async def test_select_option_should_unselect_with_null(page, server):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    result = await page.selectOption("select", ["blue", "black", "magenta"])
    assert result == ["black", "blue", "magenta"]
    await page.selectOption("select", None)
    assert await page.evalOnSelector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


async def test_select_option_should_deselect_all_options_when_passed_no_values_for_a_multiple_select(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("makeMultiple()")
    await page.selectOption("select", ["blue", "black", "magenta"])
    await page.selectOption("select", [])
    assert await page.evalOnSelector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


async def test_select_option_should_deselect_all_options_when_passed_no_values_for_a_select_without_multiple(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.selectOption("select", ["blue", "black", "magenta"])
    await page.selectOption("select", [])
    assert await page.evalOnSelector(
        "select",
        "select => Array.from(select.options).every(option => !option.selected)",
    )


async def test_select_option_should_throw_if_passed_wrong_types(page, server):
    await page.setContent('<select><option value="12"/></select>')

    with pytest.raises(Error) as exc_info:
        await page.selectOption("select", 12)
    assert "Values must be strings" in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        await page.selectOption("select", {"value": 12})
    assert "Values must be strings" in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        await page.selectOption("select", {"label": 12})
    assert "Labels must be strings" in exc_info.value.message

    with pytest.raises(Error) as exc_info:
        await page.selectOption("select", {"index": "12"})
    assert "Indices must be numbers" in exc_info.value.message


async def test_select_option_should_work_when_re_defining_top_level_event_class(
    page, server
):
    await page.goto(server.PREFIX + "/input/select.html")
    await page.evaluate("window.Event = null")
    await page.selectOption("select", "blue")
    assert await page.evaluate("result.onInput") == ["blue"]
    assert await page.evaluate("result.onChange") == ["blue"]
