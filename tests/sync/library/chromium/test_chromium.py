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

"""Port of tests/library/chromium/chromium.spec.ts."""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import pytest

from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Dialog,
    Error,
    Page,
    Playwright,
    Request,
    Route,
    sync_playwright,
)
from tests.helpers.har import read_har_log
from tests.server import Server, TestServerRequest, find_free_port

pytestmark = pytest.mark.only_browser("chromium")

T = TypeVar("T")


def poll(actual: Callable[[], Any], expected: Any, timeout: float = 10000) -> None:
    """Port of `await expect.poll(actual).toBe(expected)`."""
    deadline = time.monotonic() + timeout / 1000
    value = actual()
    while value != expected and time.monotonic() < deadline:
        time.sleep(0.1)
        value = actual()
    assert value == expected


def run_with_env_playwright(
    monkeypatch: pytest.MonkeyPatch,
    env: Dict[str, str],
    body: Callable[[Playwright], T],
) -> T:
    """Runs body with a new Playwright whose driver has env in its environment.

    Upstream sets process.env in the test process, which runs the Playwright server.
    The Python driver is another process, and it reads its environment when it starts.
    A thread can run only one sync Playwright, so the new one runs in a thread of its own.
    """

    def run() -> T:
        with sync_playwright() as playwright:
            return body(playwright)

    with monkeypatch.context() as patch:
        for name, value in env.items():
            patch.setenv(name, value)
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(run).result()


def update_demo_routes(server: Server) -> None:
    """The /worker.js and /home routes of the service worker update tests."""
    version = 0

    def handle_worker(request: TestServerRequest) -> None:
        nonlocal version
        request.setResponseCode(200, b"OK")
        request.setHeader("Content-Type", "text/javascript")
        request.write(f"self.PW_VERSION = {version};".encode())
        version += 1
        request.finish()

    def handle_home(request: TestServerRequest) -> None:
        request.write(
            b"""
      <!DOCTYPE html>
      <html>
        <head>
          <title>Service Worker Update Demo</title>
        </head>
        <body>
          <button id="update" disabled>update service worker</button>
          <script>
            const updateBtn = document.getElementById('update');
            updateBtn.addEventListener('click', evt => {
              evt.preventDefault();
              registration.then(r => r.update());
            });

            const registration = new Promise(r => navigator.serviceWorker.register('/worker.js').then(r));
            registration.then(() => updateBtn.disabled = false);
          </script>
        </body>
      </html>
    """
        )
        request.finish()

    server.set_route("/worker.js", handle_worker)
    server.set_route("/home", handle_home)


REQUEST_TABLE_HEADER = "| Event                             | Owner            | URL                            | Routed | [`method: Response.fromServiceWorker`] |"


def format_request(scope: str, r: Request, routed: List[Request]) -> str:
    event = (
        "[`event: Page.request`]"
        if scope == "page"
        else "[`event: BrowserContext.request`]"
    ).ljust(len("[`event: BrowserContext.request`]"))
    owner = (
        "Service [Worker]"
        if r.service_worker
        else "[Frame]".ljust(len("Service [Worker]"))
    )
    url = r.url.split("/")[-1].ljust(30)
    is_routed = ("Yes" if any(x is r for x in routed) else "").ljust(len("Routed"))
    response = r.response()
    assert response
    from_service_worker = ("Yes" if response.from_service_worker else "").ljust(
        len("[`method: Response.fromServiceWorker`]")
    )
    return f"| {event} | {owner} | {url} | {is_routed} | {from_service_worker} |"


def track_requests(
    context: BrowserContext, page: Page
) -> Tuple[List[Request], List[Tuple[str, Request]]]:
    """Routes and records the requests, as the network annotation tests do."""
    routed: List[Request] = []

    def handle(route: Route) -> None:
        routed.append(route.request)
        route.continue_()

    context.route("**", handle)
    page.route("**", handle)
    requests: List[Tuple[str, Request]] = []
    page.on("request", lambda r: requests.append(("page", r)))
    context.on("request", lambda r: requests.append(("context", r)))
    return routed, requests


def test_CR_001_should_create_a_worker_from_a_service_worker(
    page: Page, server: Server
) -> None:
    with page.context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    worker = worker_info.value
    assert (
        worker.evaluate("() => self.toString()") == "[object ServiceWorkerGlobalScope]"
    )


def test_CR_002_should_create_a_worker_from_service_worker_with_noop_routing(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handle(route: Route) -> None:
        route.continue_()

    context.route("**", handle)
    with page.context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    worker = worker_info.value
    assert (
        worker.evaluate("() => self.toString()") == "[object ServiceWorkerGlobalScope]"
    )


def test_CR_003_should_emit_new_service_worker_on_update(
    context: BrowserContext, page: Page, server: Server
) -> None:
    update_demo_routes(server)

    with context.expect_event("serviceworker") as sw_info:
        page.goto(server.PREFIX + "/home")
    sw = sw_info.value

    poll(lambda: sw.evaluate("() => self['PW_VERSION']"), 0)

    with context.expect_event("serviceworker") as updated_sw_info:
        page.click("#update")
    updated_sw = updated_sw_info.value

    poll(lambda: updated_sw.evaluate("() => self['PW_VERSION']"), 1)


def test_CR_004_http_credentials_http_credentials(
    context_factory: Callable[..., BrowserContext], server: Server
) -> None:
    # Port of test.use({ httpCredentials: { username: 'user', password: 'pass' } }).
    context = context_factory(http_credentials={"username": "user", "password": "pass"})
    page = context.new_page()
    server.set_auth("/serviceworkers/fetch/sw.html", "user", "pass")
    server.set_auth("/empty.html", "user", "pass")
    with context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    worker = worker_info.value

    page.evaluate("() => window['activationPromise']")
    assert worker.evaluate("() => fetch('/empty.html').then(r => r.status)") == 200


def test_CR_005_service_workers_should_return_current_workers(
    page: Page, server: Server
) -> None:
    context = page.context
    with context.expect_event("serviceworker") as worker1_info:
        page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    worker1 = worker1_info.value
    workers = context.service_workers
    assert len(workers) == 1

    with context.expect_event("serviceworker") as worker2_info:
        page.goto(server.CROSS_PROCESS_PREFIX + "/serviceworkers/empty/sw.html")
    worker2 = worker2_info.value
    workers = context.service_workers
    assert len(workers) == 2
    assert worker1 in workers
    assert worker2 in workers


def test_CR_006_should_not_create_a_worker_from_a_shared_worker(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    service_worker_created = False

    def on_service_worker(worker: Any) -> None:
        nonlocal service_worker_created
        service_worker_created = True

    page.context.once("serviceworker", on_service_worker)
    page.evaluate(
        """() => {
        new SharedWorker('data:text/javascript,console.log("hi")');
      }"""
    )
    assert not service_worker_created


def test_CR_008_should_close_service_worker_together_with_the_context(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    browser = browser_type.launch(**launch_arguments)
    context = browser.new_context()
    page = context.new_page()
    with context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    worker = worker_info.value
    messages: List[str] = []
    context.on("close", lambda _: messages.append("context"))
    worker.on("close", lambda _: messages.append("worker"))
    context.close()
    assert "|".join(messages) == "worker|context"
    browser.close()


def test_CR_009_should_pass_args_with_spaces(
    browser_type: BrowserType,
    launch_arguments: Dict,
    create_user_data_dir: Callable[[], Any],
) -> None:
    browser = browser_type.launch_persistent_context(
        create_user_data_dir(),
        **{**launch_arguments, "args": ["--user-agent=I am Foo"]},
    )
    page = browser.new_page()
    user_agent = page.evaluate("() => navigator.userAgent")
    browser.close()
    assert user_agent == "I am Foo"


def test_CR_010_service_worker_and_from_service_worker_work(
    context: BrowserContext, page: Page, server: Server
) -> None:
    with context.expect_event("serviceworker") as worker_info:
        with context.expect_event(
            "request", lambda r: r.url.endswith("/sw.html")
        ) as html_info:
            with context.expect_event(
                "request", lambda r: r.url.endswith("/sw.js")
            ) as main_info:
                with context.expect_event(
                    "request",
                    lambda r: r.url.endswith("/request-from-within-worker.txt"),
                ) as in_worker_info:
                    page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    worker = worker_info.value
    html = html_info.value
    main = main_info.value
    in_worker = in_worker_info.value

    assert html.frame
    assert html.service_worker is None
    html_response = html.response()
    assert html_response
    assert html_response.from_service_worker is False

    with pytest.raises(Error):
        main.frame
    assert main.service_worker == worker
    main_response = main.response()
    assert main_response
    assert main_response.from_service_worker is False

    with pytest.raises(Error):
        in_worker.frame
    assert in_worker.service_worker == worker
    in_worker_response = in_worker.response()
    assert in_worker_response
    assert in_worker_response.from_service_worker is False

    page.evaluate("() => window['activationPromise']")
    with context.expect_event(
        "request", lambda r: r.url.endswith("/inner.txt") and bool(r.service_worker)
    ) as inner_sw_info:
        with context.expect_event(
            "request",
            lambda r: r.url.endswith("/inner.txt") and not r.service_worker,
        ) as inner_page_info:
            page.evaluate("() => fetch('/inner.txt')")
    inner_sw = inner_sw_info.value
    inner_page = inner_page_info.value
    assert inner_page.service_worker is None
    inner_page_response = inner_page.response()
    assert inner_page_response
    assert inner_page_response.from_service_worker is True

    assert inner_sw.service_worker == worker
    inner_sw_response = inner_sw.response()
    assert inner_sw_response
    assert inner_sw_response.from_service_worker is False


def test_CR_011_should_intercept_service_worker_requests_main_and_within(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.route(
        "**/request-from-within-worker",
        lambda route: route.fulfill(
            content_type="application/json",
            status=200,
            body='"intercepted!"',
        ),
    )

    context.route(
        "**/sw.js",
        lambda route: route.fulfill(
            content_type="text/javascript",
            status=200,
            body="""
          self.contentPromise = new Promise(res => fetch('/request-from-within-worker').then(r => r.json()).then(res));
        """,
        ),
    )

    with context.expect_event("serviceworker") as sw_info:
        with context.expect_event(
            "response", lambda r: r.url.endswith("/request-from-within-worker")
        ):
            with context.expect_event(
                "request",
                lambda r: r.url.endswith("sw.js") and bool(r.service_worker),
            ):
                with context.expect_event(
                    "response",
                    lambda r: r.url.endswith("sw.js") and not r.from_service_worker,
                ):
                    page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    sw = sw_info.value

    assert sw.evaluate("() => self['contentPromise']") == "intercepted!"


def test_CR_012_should_report_failure_due_to_content_type_of_main_service_worker_request(
    server: Server, page: Page, context: BrowserContext, browser_major_version: int
) -> None:
    if browser_major_version < 104:
        pytest.skip("Requires http://crrev.com/1012503 or later.")

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200, b"OK")
        request.setHeader("Content-Type", "text/html")
        request.write(b"console.log('hi from sw');")
        request.finish()

    server.set_route("/serviceworkers/fetch/sw.js", handle)
    with server.expect_request("/serviceworkers/fetch/sw.js"):
        with context.expect_event(
            "request", lambda r: r.url.endswith("sw.js")
        ) as main_info:
            page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    main = main_info.value
    # This will timeout today
    main.response()


def test_CR_013_should_report_failure_due_to_redirect_of_main_service_worker_request(
    server: Server, page: Page, context: BrowserContext, browser_major_version: int
) -> None:
    if browser_major_version < 104:
        pytest.skip("Requires http://crrev.com/1012503 or later.")
    server.set_redirect("/serviceworkers/empty/sw.js", "/dev/null")
    with server.expect_request("/serviceworkers/empty/sw.js"):
        with context.expect_event(
            "request", lambda r: r.url.endswith("sw.js")
        ) as main_info:
            page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    main = main_info.value
    # This will timeout today
    resp = main.response()
    assert resp
    assert resp.status == 302


def test_CR_014_should_intercept_service_worker_import_scripts(
    context: BrowserContext, page: Page, server: Server
) -> None:
    context.route(
        "**/import.js",
        lambda route: route.fulfill(
            content_type="text/javascript",
            status=200,
            body="self.exportedValue = 47;",
        ),
    )

    context.route(
        "**/sw.js",
        lambda route: route.fulfill(
            content_type="text/javascript",
            status=200,
            body="""
          importScripts('/import.js');
          self.importedValue = self.exportedValue;
        """,
        ),
    )

    with context.expect_event("serviceworker") as sw_info:
        with context.expect_event("response", lambda r: r.url.endswith("/import.js")):
            page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    sw = sw_info.value

    assert sw.evaluate("() => self['importedValue']") == 47


def test_CR_015_should_report_intercepted_service_worker_requests_in_har(
    context_factory: Callable[..., BrowserContext],
    server: Server,
    tmp_path: Any,
) -> None:
    # Port of the pageWithHar fixture.
    har_path = tmp_path / "test.har"
    context = context_factory(record_har_path=har_path, ignore_https_errors=True)
    page = context.new_page()
    context.route(
        "**/request-from-within-worker",
        lambda route: route.fulfill(
            content_type="application/json",
            headers={
                "x-pw-test": "request-within-worker",
            },
            status=200,
            body='"intercepted!"',
        ),
    )

    context.route(
        "**/sw.js",
        lambda route: route.fulfill(
            content_type="text/javascript",
            headers={
                "x-pw-test": "intercepted-main",
            },
            status=200,
            body="""
          self.contentPromise = new Promise(res => fetch('/request-from-within-worker').then(r => r.json()).then(res));
        """,
        ),
    )

    with context.expect_event("serviceworker") as sw_info:
        with context.expect_event(
            "response", lambda r: r.url.endswith("/request-from-within-worker")
        ):
            page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    sw = sw_info.value

    assert sw.evaluate("() => self['contentPromise']") == "intercepted!"

    context.close()
    log = read_har_log(har_path)
    sw_entries = [e for e in log["entries"] if e["request"]["url"].endswith("sw.js")]
    assert len(sw_entries) == 1
    assert [
        v for v in sw_entries[0]["response"]["headers"] if v["name"] == "x-pw-test"
    ] == [{"name": "x-pw-test", "value": "intercepted-main"}]
    req = [
        e
        for e in log["entries"]
        if e["request"]["url"].endswith("request-from-within-worker")
    ]
    assert len(req) == 1
    assert [v for v in req[0]["response"]["headers"] if v["name"] == "x-pw-test"] == [
        {"name": "x-pw-test", "value": "request-within-worker"}
    ]
    assert req[0]["response"]["content"]["text"] == '"intercepted!"'


def test_CR_016_should_intercept_only_serviceworker_request_not_page(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handle(route: Route) -> None:
        if route.request.service_worker:
            route.fulfill(
                content_type="text/plain",
                status=200,
                body="from sw",
            )
        else:
            route.continue_()

    context.route("**/data.json", handle)

    with context.expect_event("serviceworker") as sw_info:
        page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    sw = sw_info.value
    page.evaluate("() => window['activationPromise']")
    response = page.evaluate("() => fetch('/data.json').then(r => r.text())")
    [url] = sw.evaluate("() => self['intercepted']")
    assert re.search(r"/data\.json$", url)
    assert response == "from sw"


def test_CR_017_should_produce_network_events_routing_and_annotations_for_service_worker(
    page: Page, context: BrowserContext, server: Server
) -> None:
    def handle_index(request: TestServerRequest) -> None:
        request.write(
            b"""
      <script>
        window.registrationPromise = navigator.serviceWorker.register('/transparent-service-worker.js');
      </script>
    """
        )
        request.finish()

    def handle_sw(request: TestServerRequest) -> None:
        request.setResponseCode(200, b"OK")
        request.setHeader("Content-Type", "text/javascript")
        request.write(
            b"""
      self.addEventListener("fetch", (event) => {
        // actually make the request
        const responsePromise = fetch(event.request);
        // send it back to the page
        event.respondWith(responsePromise);
      });

      self.addEventListener("activate", (event) => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    server.set_route("/index.html", handle_index)
    server.set_route("/transparent-service-worker.js", handle_sw)

    routed, requests = track_requests(context, page)

    with context.expect_event("serviceworker") as sw_info:
        page.goto(server.PREFIX + "/index.html")
    sw = sw_info.value

    poll(lambda: sw.evaluate("() => self.registration.active?.state"), "activated")

    page.evaluate("() => fetch('/data.json')")

    assert [
        REQUEST_TABLE_HEADER,
        *[format_request(scope, r, routed) for scope, r in requests],
    ] == [
        "| Event                             | Owner            | URL                            | Routed | [`method: Response.fromServiceWorker`] |",
        "| [`event: BrowserContext.request`] | [Frame]          | index.html                     | Yes    |                                        |",
        "| [`event: Page.request`]           | [Frame]          | index.html                     | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | Service [Worker] | transparent-service-worker.js  | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | Service [Worker] | data.json                      | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | [Frame]          | data.json                      |        | Yes                                    |",
        "| [`event: Page.request`]           | [Frame]          | data.json                      |        | Yes                                    |",
    ]


def test_CR_018_should_produce_network_events_routing_and_annotations_for_service_worker_advanced(
    page: Page, context: BrowserContext, server: Server
) -> None:
    def handle_index(request: TestServerRequest) -> None:
        request.write(
            b"""
      <script>
        window.registrationPromise = navigator.serviceWorker.register('/complex-service-worker.js');
      </script>
    """
        )
        request.finish()

    def handle_sw(request: TestServerRequest) -> None:
        request.setResponseCode(200, b"OK")
        request.setHeader("Content-Type", "text/javascript")
        request.write(
            b"""
      self.addEventListener("install", function (event) {
        event.waitUntil(
          caches.open("v1").then(function (cache) {
            // 1. Pre-fetches and caches /addressbook.json
            return cache.add("/addressbook.json");
          })
        );
      });

      // Opt to handle FetchEvent's from the page
      self.addEventListener("fetch", (event) => {
        event.respondWith(
          (async () => {
            // 1. Try to first serve directly from caches
            let response = await caches.match(event.request);
            if (response) return response;

            // 2. Re-write request for /foo to /bar
            if (event.request.url.endsWith("foo")) return fetch("./bar");

            // 3. Prevent tracker.js from being retrieved, and returns a placeholder response
            if (event.request.url.endsWith("tracker.js"))
              return new Response('console.log("no trackers!")', {
                status: 200,
                headers: { "Content-Type": "text/javascript" },
              });

            // 4. Otherwise, fallthrough, perform the fetch and respond
            return fetch(event.request);
          })()
        );
      });

      self.addEventListener("activate", (event) => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    def handle_addressbook(request: TestServerRequest) -> None:
        request.write(b"{}")
        request.finish()

    server.set_route("/index.html", handle_index)
    server.set_route("/complex-service-worker.js", handle_sw)
    server.set_route("/addressbook.json", handle_addressbook)

    routed, requests = track_requests(context, page)

    with context.expect_event("serviceworker") as sw_info:
        page.goto(server.PREFIX + "/index.html")
    sw = sw_info.value

    poll(lambda: sw.evaluate("() => self.registration.active?.state"), "activated")

    page.evaluate("() => fetch('/addressbook.json')")
    page.evaluate("() => fetch('/foo')")
    page.evaluate("() => fetch('/tracker.js')")
    page.evaluate("() => fetch('/fallthrough.txt')")

    assert [
        REQUEST_TABLE_HEADER,
        *[format_request(scope, r, routed) for scope, r in requests],
    ] == [
        "| Event                             | Owner            | URL                            | Routed | [`method: Response.fromServiceWorker`] |",
        "| [`event: BrowserContext.request`] | [Frame]          | index.html                     | Yes    |                                        |",
        "| [`event: Page.request`]           | [Frame]          | index.html                     | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | Service [Worker] | complex-service-worker.js      | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | Service [Worker] | addressbook.json               | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | [Frame]          | addressbook.json               |        | Yes                                    |",
        "| [`event: Page.request`]           | [Frame]          | addressbook.json               |        | Yes                                    |",
        "| [`event: BrowserContext.request`] | Service [Worker] | bar                            | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | [Frame]          | foo                            |        | Yes                                    |",
        "| [`event: Page.request`]           | [Frame]          | foo                            |        | Yes                                    |",
        "| [`event: BrowserContext.request`] | [Frame]          | tracker.js                     |        | Yes                                    |",
        "| [`event: Page.request`]           | [Frame]          | tracker.js                     |        | Yes                                    |",
        "| [`event: BrowserContext.request`] | Service [Worker] | fallthrough.txt                | Yes    |                                        |",
        "| [`event: BrowserContext.request`] | [Frame]          | fallthrough.txt                |        | Yes                                    |",
        "| [`event: Page.request`]           | [Frame]          | fallthrough.txt                |        | Yes                                    |",
    ]


def test_CR_019_should_intercept_service_worker_update_requests(
    context: BrowserContext, page: Page, server: Server
) -> None:
    pytest.skip("fixme: https://github.com/microsoft/playwright/issues/14711")

    update_demo_routes(server)

    with context.expect_event("serviceworker") as sw_info:
        page.goto(server.PREFIX + "/home")
    sw = sw_info.value

    poll(lambda: sw.evaluate("() => self['PW_VERSION']"), 0)

    # Before triggering, let's intercept the update request
    def handle(route: Route) -> None:
        route.fulfill(
            status=200,
            body='self.PW_VERSION = "intercepted";',
            content_type="text/javascript",
        )

    context.route("**/worker.js", handle)

    with context.expect_event("serviceworker") as updated_sw_info:
        # currently times out here
        with context.expect_event("request", lambda r: r.url.endswith("worker.js")):
            page.click("#update")
    updated_sw = updated_sw_info.value

    poll(lambda: updated_sw.evaluate("() => self['PW_VERSION']"), "intercepted")


def test_CR_020_set_offline(
    context: BrowserContext, page: Page, server: Server
) -> None:
    with context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    worker = worker_info.value

    page.evaluate("() => window['activationPromise']")
    context.set_offline(True)
    with context.expect_event(
        "request", lambda r: r.url.endswith("/inner.txt") and bool(r.service_worker)
    ):
        error = worker.evaluate(
            "() => fetch('/inner.txt').catch(e => `REJECTED: ${e}`)"
        )
    assert re.search(r"REJECTED.*Failed to fetch", error)


def test_CR_021_set_extra_http_headers(
    context: BrowserContext, page: Page, server: Server
) -> None:
    with context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    worker = worker_info.value

    page.evaluate("() => window['activationPromise']")
    context.set_extra_http_headers({"x-custom-header": "custom!"})
    with server.expect_request("/inner.txt") as request_info:
        worker.evaluate("() => fetch('/inner.txt')")
    req = request_info.value
    assert req.getHeader("x-custom-header") == "custom!"


def test_CR_022_should_throw_when_connecting_twice_to_an_already_running_persistent_context_remote_debugging_port(
    browser_type: BrowserType,
    launch_arguments: Dict,
    create_user_data_dir: Callable[[], Any],
    platform: str,
    is_headless_shell: bool,
    browser_channel: Optional[str],
) -> None:
    if is_headless_shell:
        pytest.skip("Headless shell does not create a ProcessSingleton")
    if platform == "win32":
        pytest.skip(
            "fixme: Windows does not print something to the console when the profile is already in use by another instance of Chromium."
        )
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("Edge does not print the ProcessSingleton line")
    user_data_dir = create_user_data_dir()
    # Upstream uses the ports 9222 and 9223.
    browser = browser_type.launch_persistent_context(
        user_data_dir,
        **{
            **launch_arguments,
            "args": [f"--remote-debugging-port={find_free_port()}"],
        },
    )
    try:
        with pytest.raises(Error) as exc_info:
            browser_type.launch_persistent_context(
                user_data_dir,
                **{
                    **launch_arguments,
                    "args": [f"--remote-debugging-port={find_free_port()}"],
                },
            )
        assert (
            "This usually means that the profile is already in use by another instance of Chromium."
            in exc_info.value.message
        )
    finally:
        browser.close()


def test_CR_023_should_throw_when_connecting_twice_to_an_already_running_persistent_context_remote_debugging_pipe(
    browser_type: BrowserType,
    launch_arguments: Dict,
    create_user_data_dir: Callable[[], Any],
    platform: str,
    is_headless_shell: bool,
    browser_channel: Optional[str],
) -> None:
    if is_headless_shell:
        pytest.skip("Headless shell does not create a ProcessSingleton")
    if platform == "win32":
        pytest.skip(
            "fixme: Windows does not print something to the console when the profile is already in use by another instance of Chromium."
        )
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("Edge does not print the ProcessSingleton line")
    user_data_dir = create_user_data_dir()
    browser = browser_type.launch_persistent_context(user_data_dir, **launch_arguments)
    try:
        with pytest.raises(Error) as exc_info:
            browser_type.launch_persistent_context(user_data_dir, **launch_arguments)
        assert (
            "This usually means that the profile is already in use by another instance of Chromium."
            in exc_info.value.message
        )
    finally:
        browser.close()


def test_CR_024_playwright_disable_service_worker_network(
    launch_arguments: Dict, server: Server, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The driver reads the variable: start one with the variable set, and use its
    # context and page.

    def body(playwright: Playwright) -> None:
        browser = playwright.chromium.launch(**launch_arguments)
        context = browser.new_context()
        page = context.new_page()

        urls: List[str] = []
        service_workers: List[Any] = []

        def on_request(r: Request) -> None:
            service_workers.append(r.service_worker)
            urls.append(r.url)

        context.on("request", on_request)

        with context.expect_event("serviceworker"):
            page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
        assert urls == [
            server.PREFIX + "/serviceworkers/fetch/sw.html",
            server.PREFIX + "/serviceworkers/fetch/style.css",
        ]

        page.evaluate("() => window['activationPromise']")
        page.evaluate("() => fetch('./inner.txt')")
        assert urls == [
            server.PREFIX + "/serviceworkers/fetch/sw.html",
            server.PREFIX + "/serviceworkers/fetch/style.css",
            server.PREFIX + "/serviceworkers/fetch/inner.txt",
        ]
        assert service_workers == [None] * len(urls)
        browser.close()

    run_with_env_playwright(
        monkeypatch, {"PLAYWRIGHT_DISABLE_SERVICE_WORKER_NETWORK": "1"}, body
    )


def test_CR_025_should_emit_console_messages_from_service_worker(
    page: Page, context: BrowserContext, server: Server
) -> None:
    empty_page = context.new_page()
    empty_page.goto(server.EMPTY_PAGE)
    empty_page_messages: List[Any] = []
    empty_page.on("console", lambda message: empty_page_messages.append(message))

    with context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    worker = worker_info.value

    with worker.expect_event("console") as message_info:
        with page.expect_event("console") as page_message_info:
            worker.evaluate(
                """() => console.log('hello from service worker', {
              i: 'am',
              am: 1,
              complex: {
                yup: true,
              },
            })"""
            )
    message = message_info.value
    page_message = page_message_info.value

    assert message is page_message
    assert len(empty_page_messages) == 0

    # Should be able to access the message after closing the page.
    page.close()

    assert "hello from service worker" in message.text
    assert message.type == "log"
    args = message.args
    assert len(args) == 2
    assert args[0].json_value() == "hello from service worker"
    assert args[1].json_value() == {
        "i": "am",
        "am": 1,
        "complex": {
            "yup": True,
        },
    }


def test_CR_026_should_capture_console_log_from_service_worker_start(
    context: BrowserContext, page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200, b"OK")
        request.setHeader("Content-Type", "text/javascript")
        request.write(b"console.log('Hello from the first line of sw.js');")
        request.finish()

    server.set_route("/serviceworkers/empty/sw.js", handle)

    with context.expect_event("serviceworker") as worker_info:
        page.goto(server.PREFIX + "/serviceworkers/empty/sw.html")
    worker = worker_info.value

    with worker.expect_event("console") as console_message_info:
        pass
    console_message = console_message_info.value
    assert console_message.text == "Hello from the first line of sw.js"
    assert console_message.type == "log"


def is_edge(channel: Optional[str]) -> bool:
    return bool(channel and channel.startswith("msedge"))


def goto_error(page: Page, url: str) -> str:
    try:
        page.goto(url)
        return ""
    except Error as e:
        return e.message


def test_CR_027_web_ui_navigation_should_refuse_web_ui_pages_that_crash_the_browser_in_an_isolated_context(
    browser: Browser, page: Page, browser_channel: Optional[str]
) -> None:
    if is_edge(browser_channel):
        pytest.skip("Edge only disallows chrome://history")

    hosts = ["apps", "extensions", "help", "history", "password-manager", "settings"]
    for url in [
        *[f"chrome://{host}" for host in hosts],
        "chrome://extensions/",
        "chrome://settings/help",
        "chrome://SETTINGS",
        "chrome:settings",
        "chrome:///settings",
        "view-source:chrome://settings",
    ]:
        assert f'Cannot navigate to "{url}"' in goto_error(page, url)
    # The refusal only matters because it keeps the browser process alive.
    assert browser.is_connected() is True
    assert page.evaluate("() => 1 + 1") == 2


def test_CR_028_web_ui_navigation_should_refuse_web_ui_pages_that_crash_edge_in_an_isolated_context(
    browser: Browser, page: Page, browser_channel: Optional[str]
) -> None:
    if not is_edge(browser_channel):
        pytest.skip("Edge has its own list of pages disallowed in InPrivate")

    for url in ["edge://history", "chrome://history", "view-source:edge://history"]:
        assert f'Cannot navigate to "{url}"' in goto_error(page, url)
    # Edge does allow these in InPrivate, so they must not be refused.
    for url in ["edge://settings", "edge://extensions"]:
        assert "Cannot navigate to" not in goto_error(page, url)
    assert browser.is_connected() is True


def test_CR_029_web_ui_navigation_should_navigate_to_web_ui_pages_that_work_in_an_isolated_context(
    page: Page, headless: bool
) -> None:
    if headless:
        pytest.skip("WebUI pages are not available in headless")

    response = page.goto("chrome://version")
    assert response
    assert response.status == 200


def test_CR_030_web_ui_navigation_should_navigate_to_any_web_ui_page_in_a_persistent_context(
    browser_type: BrowserType,
    launch_arguments: Dict,
    create_user_data_dir: Callable[[], Any],
    headless: bool,
) -> None:
    if headless:
        pytest.skip("WebUI pages are not available in headless")

    context = browser_type.launch_persistent_context(
        create_user_data_dir(), **launch_arguments
    )
    try:
        page = context.new_page()
        # Committing the navigation is all this asserts - waiting for the WebUI to load is slow and beside the point.
        response = page.goto("chrome://extensions", wait_until="commit")
        assert response
        assert response.status == 200
    finally:
        context.close()


def test_CR_031_should_fire_dialogclosed_event_when_dialog_is_closed_out_of_band(
    page: Page, sync_gather: Callable
) -> None:
    # Establish the CDP session up front: creating one while a dialog is blocking the page hangs.
    client = page.context.new_cdp_session(page)
    client.send("Page.enable")

    def close_dialog_out_of_band() -> Dialog:
        dialog = page.wait_for_event("dialog")
        # Handle the dialog out of band, similar to the user closing it in the headed browser.
        client.send("Page.handleJavaScriptDialog", {"accept": True})
        return dialog

    # The sync API waits for the dialog while page.evaluate() runs.
    with page.expect_event("dialogclosed") as closed_info:
        dialog, _ = sync_gather(
            close_dialog_out_of_band, lambda: page.evaluate("() => alert('yo')")
        )
    assert closed_info.value is dialog
