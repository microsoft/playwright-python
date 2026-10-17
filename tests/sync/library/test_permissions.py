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

"""Port of tests/library/permissions.spec.ts."""

from typing import Any, Callable, Dict, List, Optional, Union

import pytest

from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Frame,
    Page,
    Route,
)
from tests.server import Server, TestServerRequest


def get_permission(page: Union[Page, Frame], name: str) -> str:
    return page.evaluate(
        "name => navigator.permissions.query({ name }).then(result => result.state)",
        name,
    )


@pytest.fixture
def skip_on_windows_webkit(browser_name: str, is_win: bool) -> None:
    """The fixme of the 'permissions' describe."""
    if browser_name == "webkit" and is_win:
        pytest.skip("fixme: Permissions API is disabled on Windows WebKit")


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_001_permissions_should_be_prompt_by_default(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    assert get_permission(page, "geolocation") == "prompt"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_002_permissions_should_deny_permission_when_not_listed(
    page: Page,
    context: BrowserContext,
    server: Server,
    browser_name: str,
    is_frozen_webkit: bool,
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen webkit")

    page.goto(server.EMPTY_PAGE)
    context.grant_permissions([], origin=server.EMPTY_PAGE)
    if browser_name == "webkit":
        assert get_permission(page, "geolocation") == "prompt"
        # Since https://github.com/WebKit/WebKit/pull/45470 WebKit only returns actual
        # permission value, if the API has been accessed.
        page.evaluate("() => navigator.geolocation.getCurrentPosition(() => { })")
        assert get_permission(page, "geolocation") == "denied"
    else:
        assert get_permission(page, "geolocation") == "denied"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_003_permissions_should_fail_when_bad_permission_is_given(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        context.grant_permissions(["foo"], origin=server.EMPTY_PAGE)
    assert "Unknown permission: foo" in exc_info.value.message


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_004_permissions_should_grant_geolocation_permission_when_origin_is_listed(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["geolocation"], origin=server.EMPTY_PAGE)
    assert get_permission(page, "geolocation") == "granted"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_005_permissions_should_prompt_for_geolocation_permission_when_origin_is_not_listed(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["geolocation"], origin=server.EMPTY_PAGE)
    page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert get_permission(page, "geolocation") == "prompt"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_006_permissions_should_grant_notifications_permission_when_listed(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["notifications"], origin=server.EMPTY_PAGE)
    assert get_permission(page, "notifications") == "granted"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_007_permissions_should_accumulate_when_adding(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["geolocation"])
    context.grant_permissions(["notifications"])
    assert get_permission(page, "geolocation") == "granted"
    assert get_permission(page, "notifications") == "granted"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_008_permissions_should_clear_permissions(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["geolocation"])
    context.clear_permissions()
    context.grant_permissions(["notifications"])
    assert get_permission(page, "geolocation") != "granted"
    assert get_permission(page, "notifications") == "granted"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_009_permissions_should_grant_permission_when_listed_for_all_domains(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["geolocation"])
    assert get_permission(page, "geolocation") == "granted"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_010_permissions_should_grant_permission_when_creating_context(
    server: Server, browser: Browser
) -> None:
    context = browser.new_context(permissions=["geolocation"])
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    assert get_permission(page, "geolocation") == "granted"
    context.close()


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_011_permissions_should_reset_permissions(
    page: Page, context: BrowserContext, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    context.grant_permissions(["geolocation"], origin=server.EMPTY_PAGE)
    assert get_permission(page, "geolocation") == "granted"
    context.clear_permissions()
    assert get_permission(page, "geolocation") == "prompt"


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_012_permissions_should_trigger_permission_onchange(
    page: Page,
    context: BrowserContext,
    server: Server,
    browser_name: str,
    request: pytest.FixtureRequest,
) -> None:
    if browser_name == "webkit":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: it.fail(browserName === 'webkit')", strict=True
            )
        )

    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
      window['events'] = [];
      return navigator.permissions.query({ name: 'geolocation' }).then(function(result) {
        window['events'].push(result.state);
        result.onchange = function() {
          window['events'].push(result.state);
        };
      });
    }"""
    )
    expected_events = ["prompt"]
    assert page.evaluate("() => window['events']") == expected_events
    context.grant_permissions([], origin=server.EMPTY_PAGE)
    expected_events.append("denied")
    assert page.evaluate("() => window['events']") == expected_events
    context.grant_permissions(["geolocation"], origin=server.EMPTY_PAGE)
    expected_events.append("granted")
    assert page.evaluate("() => window['events']") == expected_events
    context.clear_permissions()
    expected_events.append("prompt")
    assert page.evaluate("() => window['events']") == expected_events


@pytest.mark.usefixtures("skip_on_windows_webkit")
def test_PE_013_permissions_should_isolate_permissions_between_browser_contexts(
    server: Server, browser: Browser, browser_name: str, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen webkit")

    context = browser.new_context()
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    other_context = browser.new_context()
    other_page = other_context.new_page()
    other_page.goto(server.EMPTY_PAGE)
    assert get_permission(page, "geolocation") == "prompt"
    assert get_permission(other_page, "geolocation") == "prompt"

    context.grant_permissions([], origin=server.EMPTY_PAGE)
    other_context.grant_permissions(["geolocation"], origin=server.EMPTY_PAGE)
    if browser_name == "webkit":
        assert get_permission(page, "geolocation") == "prompt"
        # Since https://github.com/WebKit/WebKit/pull/45470 WebKit only returns actual
        # permission value, if the API has been accessed.
        page.evaluate("() => navigator.geolocation.getCurrentPosition(() => { })")
        assert get_permission(page, "geolocation") == "denied"
    else:
        assert get_permission(page, "geolocation") == "denied"
    assert get_permission(other_page, "geolocation") == "granted"

    context.clear_permissions()
    if browser_name == "webkit":
        # Since https://github.com/WebKit/WebKit/pull/45470 WebKit returns the cached
        # permission value, if the geolocation API has been accessed.
        # TODO: We can probably reset the cached state in the Web Process when resetting
        # permissions.
        assert get_permission(page, "geolocation") == "denied"

        # Geolocation API in the new page in the same context has not been accessed yet,
        # so the permission status should be prompt.
        page2 = context.new_page()
        page2.goto(server.EMPTY_PAGE)
        assert get_permission(page2, "geolocation") == "prompt"
        page2.close()
    else:
        assert get_permission(page, "geolocation") == "prompt"
    assert get_permission(other_page, "geolocation") == "granted"
    other_context.close()
    context.close()


def test_PE_014_should_support_clipboard_read(
    page: Page,
    context: BrowserContext,
    server: Server,
    browser_name: str,
    is_headless_shell: bool,
    request: pytest.FixtureRequest,
) -> None:
    if browser_name == "firefox":
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: No such permissions (requires flag) in Firefox",
                strict=True,
            )
        )

    page.goto(server.EMPTY_PAGE)
    # There is no 'clipboard-read' permission in WebKit Web API.
    if browser_name != "webkit":
        assert get_permission(page, "clipboard-read") == "prompt"

    if is_headless_shell:
        # Chromium (but not headless-shell) shows a dialog and does not resolve the promise.
        with pytest.raises(Error) as exc_info:
            page.evaluate("() => navigator.clipboard.readText()")
        assert "denied" in str(exc_info.value)

    context.grant_permissions(["clipboard-read"])
    if browser_name != "webkit":
        assert get_permission(page, "clipboard-read") == "granted"
    # There is no 'clipboard-write' permission in WebKit Web API.
    if browser_name == "chromium":
        context.grant_permissions(["clipboard-write"])
    page.evaluate("() => navigator.clipboard.writeText('test content')")
    assert page.evaluate("() => navigator.clipboard.readText()") == "test content"


def test_PE_015_should_isolate_the_headless_clipboard_from_the_operating_system(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    browser_name: str,
    is_frozen_webkit: bool,
) -> None:
    if is_frozen_webkit:
        pytest.skip("needs recent webkit")

    # Each headless browser gets its own clipboard, so neither can see the clipboard of the operating system nor of another browser.
    browser1 = browser_type.launch(**{**launch_arguments, "headless": True})
    browser2 = browser_type.launch(**{**launch_arguments, "headless": True})

    def open_page(browser: Browser) -> Page:
        context = browser.new_context()
        # There is no 'clipboard-write' permission in WebKit Web API and no clipboard permission at all in Firefox.
        if browser_name == "chromium":
            context.grant_permissions(["clipboard-read", "clipboard-write"])
        elif browser_name == "webkit":
            context.grant_permissions(["clipboard-read"])
        page = context.new_page()
        page.goto(server.EMPTY_PAGE)
        return page

    page1, page2 = [open_page(browser) for browser in [browser1, browser2]]

    page1.evaluate("() => navigator.clipboard.writeText('first')")
    assert page1.evaluate("() => navigator.clipboard.readText()") == "first"

    page2.evaluate("() => navigator.clipboard.writeText('second')")
    assert page2.evaluate("() => navigator.clipboard.readText()") == "second"

    assert page1.evaluate("() => navigator.clipboard.readText()") == "first"

    browser1.close()
    browser2.close()


def test_PE_016_storage_access(
    page: Page, context: BrowserContext, server: Server, browser_name: str
) -> None:
    if browser_name != "chromium":
        pytest.skip("chromium-only api")

    context.grant_permissions(["storage-access"])
    assert get_permission(page, "storage-access") == "granted"

    def handle_set_cookie(request: TestServerRequest) -> None:
        request.setHeader("Set-Cookie", "name=value; Path=/; SameSite=Strict; Secure")
        request.finish()

    server.set_route("/set-cookie.html", handle_set_cookie)

    def handle_my_frame(request: TestServerRequest) -> None:
        request.setHeader("Content-type", "text/html")
        request.write(
            f'<iframe src="{server.CROSS_PROCESS_PREFIX + "/empty.html"}"></iframe>'.encode()
        )
        request.finish()

    server.set_route("/my-frame.html", handle_my_frame)

    # Navigate once to the domain as top level.
    page.goto(server.CROSS_PROCESS_PREFIX + "/set-cookie.html")
    page.goto(server.PREFIX + "/my-frame.html")

    frame = page.frames[1]
    assert get_permission(frame, "storage-access") == "granted"
    access = frame.evaluate(
        "() => document.requestStorageAccess().then(() => true, () => false)"
    )
    assert access is True
    assert frame.evaluate("() => document.hasStorageAccess()") is True


def test_PE_017_should_be_able_to_use_the_local_fonts_api(
    context_factory: Callable[..., BrowserContext],
    https_server: Server,
    browser_name: str,
    browser_channel: Optional[str],
    headless: bool,
) -> None:
    if browser_name != "chromium":
        pytest.skip("chromium-only api")
    if browser_channel and browser_channel.startswith("msedge"):
        pytest.skip("always times out in edge")
    if not headless:
        pytest.skip("fixme: times out in headed")

    # Secure context
    context = context_factory(ignore_https_errors=True)
    page = context.new_page()
    page.goto(https_server.EMPTY_PAGE)
    assert get_permission(page, "local-fonts") == "prompt"
    context.grant_permissions(["local-fonts"])
    assert get_permission(page, "local-fonts") == "granted"
    assert (
        page.evaluate("async () => (await window.queryLocalFonts()).length > 0") is True
    )


def test_PE_018_local_network_request_is_allowed_from_public_origin(
    page: Page,
    context: BrowserContext,
    server: Server,
    browser_name: str,
    browser_major_version: int,
) -> None:
    if browser_name == "webkit":
        pytest.skip("webkit")
    if browser_name == "chromium" and browser_major_version < 145:
        pytest.skip(
            "local-network-access permission support has changed between versions"
        )

    if browser_name == "chromium" or browser_name == "firefox":
        context.grant_permissions(["local-network-access"])
    server_requests: List[str] = []

    def handle_cors(request: TestServerRequest) -> None:
        server_requests.append(f"{request.method.decode()} {request.uri.decode()}")
        if request.method == b"OPTIONS":
            request.setResponseCode(204)
            request.setHeader("Access-Control-Allow-Origin", "*")
            request.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            request.setHeader("Access-Control-Allow-Headers", "*")
            request.finish()
            return
        request.setResponseCode(200)
        request.setHeader("Content-type", "text/plain")
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(b"Hello there!")
        request.finish()

    server.set_route("/cors", handle_cors)
    client_requests: List[str] = []
    # Has to be a public origin.
    page.goto("https://demo.playwright.dev/todomvc/")
    page.on(
        "request",
        lambda request: client_requests.append(f"{request.method} {request.url}"),
    )
    try:
        response: Any = page.evaluate(
            """async url => {
    const response = await fetch(url, {
      method: 'POST',
      body: '',
      headers: {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'test-value'
      }
    });
    return await response.text();
  }""",
            server.CROSS_PROCESS_PREFIX + "/cors",
        )
    except Error as e:
        response = e.message
    assert response == "Hello there!"
    assert server_requests == [
        "OPTIONS /cors",
        "POST /cors",
    ]
    assert client_requests == [
        f"POST {server.CROSS_PROCESS_PREFIX}/cors",
    ]


def test_PE_019_can_request_screen_wake_lock(
    page: Page, context: BrowserContext
) -> None:
    context.grant_permissions(["screen-wake-lock"])

    def handle(route: Route) -> None:
        route.fulfill(
            status=200, body="<div>Hello there!</div>", content_type="text/html"
        )

    page.route("**/*", handle)
    page.goto("https://example.com")
    page.evaluate("() => navigator.wakeLock.request('screen')")


@pytest.fixture
def skip_camera_and_microphone(
    browser_name: str, is_win: bool, browser_channel: Optional[str]
) -> None:
    """The skips of the 'camera and microphone' describe."""
    # WebKit exposes deterministic mock capture devices; capture is gated on the
    # 'camera'/'microphone' permissions. Chromium needs --use-fake-device-for-media-stream
    # and Firefox has no camera/microphone permission mapping, so scope to WebKit.
    if browser_name != "webkit":
        pytest.skip("WebKit mock-capture-device based test")
    # Native Windows WebKit is built without a media-capture backend, so getUserMedia is
    # unavailable there; WSL runs the Linux build, which does have mock capture.
    if is_win and browser_channel != "webkit-wsl":
        pytest.skip("WebKit has no media capture on Windows")


def get_user_media(page: Page, constraints: Dict[str, bool]) -> Any:
    return page.evaluate(
        """async constraints => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        const tracks = stream.getTracks().map(track => ({ kind: track.kind, live: track.readyState === 'live' }));
        stream.getTracks().forEach(track => track.stop());
        tracks.sort((a, b) => a.kind.localeCompare(b.kind));
        return { tracks };
      } catch (error) {
        return { error: error.name };
      }
    }""",
        constraints,
    )


@pytest.mark.usefixtures("skip_camera_and_microphone")
def test_PE_020_camera_and_microphone_should_capture_when_camera_and_microphone_are_granted(
    page: Page, context: BrowserContext, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("Mock capture device support requires a newer WebKit build")

    context.grant_permissions(["camera", "microphone"], origin=server.PREFIX)
    page.goto(server.EMPTY_PAGE)
    assert get_user_media(page, {"video": True, "audio": True}) == {
        "tracks": [
            {"kind": "audio", "live": True},
            {"kind": "video", "live": True},
        ],
    }


@pytest.mark.usefixtures("skip_camera_and_microphone")
def test_PE_021_camera_and_microphone_should_reject_when_no_permission_is_granted(
    page: Page, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("Mock capture device support requires a newer WebKit build")

    page.goto(server.EMPTY_PAGE)
    assert get_user_media(page, {"video": True, "audio": True}) == {
        "error": "NotAllowedError"
    }


@pytest.mark.usefixtures("skip_camera_and_microphone")
def test_PE_022_camera_and_microphone_should_gate_audio_and_video_independently(
    page: Page, context: BrowserContext, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("Mock capture device support requires a newer WebKit build")

    context.grant_permissions(["camera"], origin=server.PREFIX)
    page.goto(server.EMPTY_PAGE)
    # Camera-only request is allowed.
    assert get_user_media(page, {"video": True}) == {
        "tracks": [{"kind": "video", "live": True}]
    }
    # Microphone request is rejected because it was not granted.
    assert get_user_media(page, {"audio": True}) == {"error": "NotAllowedError"}


@pytest.mark.usefixtures("skip_camera_and_microphone")
def test_PE_023_camera_and_microphone_should_stop_capturing_after_permissions_are_cleared(
    page: Page, context: BrowserContext, server: Server, is_frozen_webkit: bool
) -> None:
    if is_frozen_webkit:
        pytest.skip("Mock capture device support requires a newer WebKit build")

    context.grant_permissions(["camera"], origin=server.PREFIX)
    page.goto(server.EMPTY_PAGE)
    assert get_user_media(page, {"video": True}) == {
        "tracks": [{"kind": "video", "live": True}]
    }
    context.clear_permissions()
    assert get_user_media(page, {"video": True}) == {"error": "NotAllowedError"}
