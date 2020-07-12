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
import pytest
import re
from playwright import Error, TimeoutError


async def test_close_should_reject_all_promises(context):
    new_page = await context.newPage()
    error = None
    try:
        await asyncio.gather(
            new_page.evaluate("() => new Promise(r => {})"), new_page.close()
        )
    except Error as e:
        error = e
    assert "Protocol error" in error.message


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
    error = None
    try:
        await page.goto(server.EMPTY_PAGE)
    except Error as e:
        error = e
    assert error
    assert __file__ in error.stack


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
    error = None
    try:
        await page.waitForEvent("request", timeout=1)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


async def test_wait_for_request_should_respect_default_timeout(page, server):
    error = None
    page.setDefaultTimeout(1)
    try:
        await page.waitForEvent("request", lambda _: False)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


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
    error = None
    try:
        await future
    except Error as e:
        error = e
    assert "Page closed" in error.message


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
    error = None
    try:
        await page.waitForEvent("response", timeout=1)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


async def test_wait_for_response_should_respect_default_timeout(page, server):
    error = None
    page.setDefaultTimeout(1)
    try:
        await page.waitForEvent("response", lambda _: False)
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


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
    error = None
    try:
        await page.setContent(
            '<img src="${server.PREFIX + img_path}"></img>', timeout=1
        )
    except Error as e:
        error = e
    assert isinstance(error, TimeoutError)


async def test_set_content_should_respect_default_navigation_timeout(page, server):
    page.setDefaultNavigationTimeout(1)
    img_path = "/img.png"
    # stall for image
    await page.route(img_path, lambda route, request: None)

    error = None
    try:
        await page.setContent(f'<img src="{server.PREFIX + img_path}"></img>')
    except Error as e:
        error = e
    assert "Timeout 1ms exceeded during" in error.message
    assert isinstance(error, TimeoutError)


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
