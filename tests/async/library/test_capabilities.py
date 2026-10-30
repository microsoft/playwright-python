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

"""Port of tests/library/capabilities.spec.ts."""

import asyncio
import re
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

import pytest

from playwright.async_api import BrowserContext, Error, Page, Route, expect
from tests.server import Server, TestServerRequest


async def test_CA_001_shared_array_buffer_should_work_smoke(
    context_factory: Callable[..., Awaitable[BrowserContext]], https_server: Server
) -> None:
    context = await context_factory(ignore_https_errors=True)
    page = await context.new_page()

    def handle(request: TestServerRequest) -> None:
        request.setHeader("Cross-Origin-Opener-Policy", "same-origin")
        request.setHeader("Cross-Origin-Embedder-Policy", "require-corp")
        # Note: without 'onload', Firefox sometimes does not fire the load event
        # over the protocol. The reason is unclear.
        request.write(
            b"""
      <div>Hello there!</div>
      <script>window.onload = () => console.log('onload')</script>
    """
        )
        request.finish()

    https_server.set_route("/sharedarraybuffer", handle)
    await page.goto(https_server.PREFIX + "/sharedarraybuffer")
    assert await page.evaluate("() => typeof SharedArrayBuffer") == "function"


async def test_CA_002_web_assembly_should_work_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/wasm/table2.html")
    assert await page.evaluate("loadTable()") == "42, 83"


async def test_CA_003_web_socket_should_work_smoke(page: Page, server: Server) -> None:
    server.send_on_web_socket_connection(b"incoming")
    value = await page.evaluate(
        """host => {
      let cb;
      const result = new Promise(f => cb = f);
      const ws = new WebSocket('ws://' + host + '/ws');
      ws.addEventListener('message', data => { ws.close(); cb(data.data); });
      ws.addEventListener('error', error => cb('Error'));
      return result;
    }""",
        server.HOST,
    )
    assert value == "incoming"


async def test_CA_004_should_respect_csp_smoke(page: Page, server: Server) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Security-Policy", "script-src 'unsafe-inline';")
        request.write(
            b"""
      <script>
        window.testStatus = 'SUCCESS';
        window.testStatus = eval("'FAILED'");
      </script>"""
        )
        request.finish()

    server.set_route("/empty.html", handle)

    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("() => window['testStatus']") == "SUCCESS"


async def test_CA_005_should_play_video_smoke(
    page: Page, assetdir: Path, browser_name: str, is_win: bool
) -> None:
    if browser_name == "webkit" and is_win:
        pytest.skip(
            "passes locally but fails on GitHub Action bot, apparently due to a Media Pack issue in the Windows Server"
        )

    # Safari only plays mp4 so we test WebKit with an .mp4 clip.
    file_name = "video_mp4.html" if browser_name == "webkit" else "video.html"
    absolute_path = assetdir / file_name
    # Our test server doesn't support range requests required to play on Mac,
    # so we load the page using a file url.
    await page.goto(absolute_path.as_uri())
    await page.eval_on_selector("video", "v => v.play()")
    await page.eval_on_selector("video", "v => v.pause()")


async def test_CA_006_should_play_webm_video_smoke(
    page: Page, assetdir: Path, browser_name: str, platform: str
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("not supported")

    absolute_path = assetdir / "video_webm.html"
    # Our test server doesn't support range requests required to play on Mac,
    # so we load the page using a file url.
    await page.goto(absolute_path.as_uri())
    await page.eval_on_selector("video", "v => v.play()")
    await page.eval_on_selector("video", "v => v.pause()")


async def test_CA_007_should_play_audio_smoke(
    page: Page, server: Server, browser_name: str, platform: str, mac_version: int
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("fixme: https://github.com/microsoft/playwright/issues/10892")
    if browser_name == "webkit" and platform == "darwin" and mac_version == 15:
        pytest.skip("audio output is unreliable on hosted macOS 15 runners")

    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f'<audio src="{server.PREFIX}/example.mp3"></audio>')
    await page.eval_on_selector("audio", "e => e.play()")
    await page.wait_for_timeout(3000)
    await page.eval_on_selector("audio", "e => e.pause()")
    assert await page.eval_on_selector("audio", "e => e.currentTime") > 0.1


async def test_CA_008_should_support_webgl_smoke(page: Page) -> None:
    has_web_gl = await page.evaluate(
        """() => {
      const canvas = document.createElement('canvas');
      return !!canvas.getContext('webgl');
    }"""
    )
    assert has_web_gl is True


async def test_CA_009_should_support_webgl_2_smoke(
    page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "firefox" and is_win:
        pytest.skip("fixme")

    has_web_gl2 = await page.evaluate(
        """() => {
      const canvas = document.createElement('canvas');
      return !!canvas.getContext('webgl2');
    }"""
    )
    assert has_web_gl2 is True


async def test_CA_010_should_not_crash_on_page_with_mp4_smoke(
    page: Page, server: Server, platform: str, browser_name: str
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip(
            "fixme: https://github.com/microsoft/playwright/issues/11009, times out in setContent"
        )
    await page.set_content(f'<video><source src="{server.PREFIX}/movie.mp4"/></video>')
    await page.wait_for_timeout(1000)


async def test_CA_011_should_not_crash_on_show_directory_picker(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name != "chromium":
        pytest.skip("showDirectoryPicker is only available in Chromium")
    await page.goto(server.EMPTY_PAGE)
    # "User activation is required to show a file picker." - so we click first.
    await page.locator("body").click()
    await page.evaluate(
        """() => {
      window.showDirectoryPicker().catch(e => { window.__pickerError = String(e); });
    }"""
    )
    # The dialog will not be accepted, so we just wait for some time to
    # to give the browser a chance to crash.
    await page.wait_for_timeout(3_000)
    # In headless it throws (aborted), in headed it stalls and waits for the picker to be accepted.
    error = await page.evaluate("() => window.__pickerError ?? 'stalled'")
    assert re.search(
        r"((DOMException|AbortError): .*The user aborted a request|stalled)", error
    )


async def test_CA_012_should_not_crash_on_storage_get_directory(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)
    error: Optional[Error] = None
    try:
        await page.evaluate(
            """async () => {
        const dir = await navigator.storage.getDirectory();
        return dir.name;
      }"""
        )
    except Error as e:
        error = e
    if browser_name == "webkit":
        assert error is not None
        assert (
            "UnknownError: The operation failed for an unknown transient reason"
            in error.message
        )
    else:
        assert error is None


async def test_CA_013_navigator_clipboard_should_be_present(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    # A JavaScript object is truthy; it serializes to {}.
    assert await page.evaluate("() => navigator.clipboard") is not None


async def test_CA_014_should_set_close_event_was_clean_to_false_when_the_server_terminates_a_web_socket_connection(
    page: Page, server: Server
) -> None:
    server.once_web_socket_connection(lambda socket: socket.terminate())
    was_clean = await page.evaluate(
        """port => new Promise(resolve => {
      const ws = new WebSocket('ws://localhost:' + port + '/ws');
      ws.addEventListener('close', error => resolve(error.wasClean));
    })""",
        server.PORT,
    )
    assert was_clean is False


async def test_CA_015_service_worker_should_intercept_document_request(
    page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "application/javascript")
        request.write(
            b"""
      self.addEventListener('fetch', event => {
        event.respondWith(new Response('intercepted'));
      });
      self.addEventListener('activate', event => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    server.set_route("/sw.js", handle)
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """async () => {
      await navigator.serviceWorker.register('/sw.js');
      await new Promise(resolve => navigator.serviceWorker.oncontrollerchange = resolve);
    }"""
    )
    await page.reload()
    assert await page.text_content("body") == "intercepted"


async def test_CA_016_webkit_should_define_window_safari(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name != "webkit":
        pytest.skip("webkit only")
    await page.goto(server.EMPTY_PAGE)
    defined = await page.evaluate("() => !!window.safari")
    assert defined
    assert (
        await page.evaluate("() => typeof window.safari.pushNotification") == "object"
    )
    assert (
        await page.evaluate("() => window.safari.pushNotification.toString()")
        == "[object SafariRemoteNotification]"
    )


async def test_CA_017_make_sure_that_xml_http_request_upload_events_are_emitted_correctly(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    events = await page.evaluate(
        """async () => {
      const events = [];
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('loadstart', () => events.push('loadstart'));
      xhr.upload.addEventListener('progress', () => events.push('progress'));
      xhr.upload.addEventListener('load', () => events.push('load'));
      xhr.upload.addEventListener('loadend', () => events.push('loadend'));
      xhr.open('POST', '/simple.json');
      xhr.send('hello');
      await new Promise(f => xhr.onload = f);
      return events;
    }"""
    )
    assert events == ["loadstart", "progress", "load", "loadend"]


async def test_CA_018_loading_in_html_image_element_prototype(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    defined = await page.evaluate("() => 'loading' in HTMLImageElement.prototype")
    assert defined


async def test_CA_019_window_gesture_event_in_web_kit(
    page: Page, server: Server, browser_name: str
) -> None:
    await page.goto(server.EMPTY_PAGE)
    defined = await page.evaluate("() => 'GestureEvent' in window")
    assert defined == (browser_name == "webkit")
    type = await page.evaluate("() => typeof window.GestureEvent")
    assert type == ("function" if browser_name == "webkit" else "undefined")


async def test_CA_020_request_fullscreen(
    page: Page, server: Server, browser_name: str, headless: bool
) -> None:
    if browser_name == "firefox" and not headless:
        pytest.skip(
            "fixme: Error: Request for fullscreen was denied because requesting element is not in the currently focused tab"
        )
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
      const result = new Promise(resolve => document.addEventListener('fullscreenchange', resolve));
      void document.documentElement.requestFullscreen().then(() => console.log('success')).catch(e => console.log(e));
      return result;
    }"""
    )
    assert await page.evaluate(
        "() => document.fullscreenElement === document.documentElement"
    )
    await page.evaluate(
        """() => {
      const result = new Promise(resolve => document.addEventListener('fullscreenchange', resolve));
      void document.exitFullscreen().then(() => console.log('success')).catch(e => console.log(e));
      return result;
    }"""
    )
    assert not await page.evaluate("() => !!document.fullscreenElement")


async def test_CA_021_should_send_no_content_length_header_for_get_requests_with_a_content_type(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    with server.expect_request("/empty.html") as request_info:
        await page.evaluate(
            """() => fetch('/empty.html', {
        'headers': { 'Content-Type': 'application/json' },
        'method': 'GET'
      })"""
        )
    request = request_info.value
    assert request.getHeader("content-length") is None


async def test_CA_022_intl_list_format_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    formatted = await page.evaluate(
        """() => {
      const data = ['first', 'second', 'third'];
      const listFormat = new Intl.ListFormat('en', {
        type: 'disjunction',
        style: 'short',
      });
      return listFormat.format(data);
    }"""
    )
    assert formatted == "first, second, or third"


async def test_CA_023_service_worker_should_cover_the_iframe(
    page: Page, server: Server
) -> None:
    def handle_sw_html(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <script>
        window.registrationPromise = navigator.serviceWorker.register('sw.js');
        window.activationPromise = new Promise(resolve => navigator.serviceWorker.oncontrollerchange = resolve);
      </script>
    """
        )
        request.finish()

    def handle_iframe(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(b"<div>from the server</div>")
        request.finish()

    def handle_sw_js(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "application/javascript")
        request.write(
            b"""
      const kIframeHtml = "<div>from the service worker</div>";

      self.addEventListener('fetch', event => {
        if (event.request.url.endsWith('iframe.html')) {
          const blob = new Blob([kIframeHtml], { type: 'text/html' });
          const response = new Response(blob, { status: 200 , statusText: 'OK' });
          event.respondWith(response);
          return;
        }
        event.respondWith(fetch(event.request));
      });

      self.addEventListener('activate', event => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    server.set_route("/sw.html", handle_sw_html)
    server.set_route("/iframe.html", handle_iframe)
    server.set_route("/sw.js", handle_sw_js)

    await page.goto(server.PREFIX + "/sw.html")
    await page.evaluate("() => window['activationPromise']")

    await page.evaluate(
        """() => {
      const iframe = document.createElement('iframe');
      iframe.src = '/iframe.html';
      document.body.appendChild(iframe);
    }"""
    )

    await expect(page.frame_locator("iframe").locator("div")).to_have_text(
        "from the service worker"
    )


async def test_CA_024_service_worker_should_register_in_an_iframe(
    page: Page, server: Server
) -> None:
    def handle_main(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <iframe src='/dir/iframe.html'></iframe>
    """
        )
        request.finish()

    def handle_iframe(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html")
        request.write(
            b"""
      <script>
        window.registrationPromise = navigator.serviceWorker.register('sw.js');
        window.activationPromise = new Promise(resolve => navigator.serviceWorker.oncontrollerchange = resolve);
      </script>
    """
        )
        request.finish()

    def handle_sw_js(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "application/javascript")
        request.write(
            b"""
      const kIframeHtml = "<div>from the service worker</div>";

      self.addEventListener('fetch', event => {
        if (event.request.url.endsWith('html')) {
          event.respondWith(fetch(event.request));
          return;
        }
        const blob = new Blob(['responseFromServiceWorker'], { type: 'text/plain' });
        const response = new Response(blob, { status: 200 , statusText: 'OK' });
        event.respondWith(response);
      });

      self.addEventListener('activate', event => {
        event.waitUntil(clients.claim());
      });
    """
        )
        request.finish()

    server.set_route("/main.html", handle_main)
    server.set_route("/dir/iframe.html", handle_iframe)
    server.set_route("/dir/sw.js", handle_sw_js)

    await page.goto(server.PREFIX + "/main.html")
    iframe = page.frames[1]
    await iframe.evaluate("() => window['activationPromise']")

    response = await iframe.evaluate(
        """async () => {
      const response = await fetch('foo.txt');
      return response.text();
    }"""
    )
    assert response == "responseFromServiceWorker"


async def test_CA_025_should_be_able_to_render_avif_images(
    page: Page,
    server: Server,
    browser_name: str,
    platform: str,
    is_frozen_webkit: bool,
) -> None:
    if browser_name == "webkit" and platform == "win32":
        pytest.skip("webkit on Windows")
    if is_frozen_webkit:
        pytest.skip("frozen webkit")
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        f'<img src="{server.PREFIX}/rgb.avif" onerror="window.error = true">'
    )
    # Port of expect.poll(() => boundingBox()).toEqual(expect.objectContaining({ width: 128, height: 128 })).
    deadline = time.monotonic() + 5
    box = await page.locator("img").bounding_box()
    while not (box and box["width"] == 128 and box["height"] == 128):
        if time.monotonic() > deadline:
            break
        await asyncio.sleep(0.1)
        box = await page.locator("img").bounding_box()
    assert box is not None
    assert box["width"] == 128
    assert box["height"] == 128
    assert await page.evaluate("() => window.error") is None


async def test_CA_026_should_not_crash_when_clicking_a_label_with_a_input_type_file(
    page: Page,
) -> None:
    await page.set_content(
        """
    <form>
      <label>
        A second file
        <input type="file" />
      </label>
    </form>
  """
    )
    async with page.expect_file_chooser() as file_chooser_info:
        await page.get_by_text("A second file").click()
    file_chooser = await file_chooser_info.value
    assert file_chooser.page == page


async def test_CA_027_should_not_crash_when_clicking_a_color_input(
    page: Page,
) -> None:
    await page.set_content('<input type="color">')
    input = page.locator("input")

    await expect(input).to_be_visible()
    await input.click()
    await expect(input).to_be_visible()


async def test_CA_028_should_not_auto_play_audio(
    page: Page, browser_name: str, is_win: bool
) -> None:
    if browser_name == "webkit" and is_win:
        pytest.skip("audio does not play at all")

    async def handle(route: Route) -> None:
        await route.fulfill(
            status=200,
            content_type="text/html",
            body="""
      <script>
        async function onLoad() {
          const log = document.getElementById('log');
          const audioContext = new AudioContext();
          const gainNode = new GainNode(audioContext);
          gainNode.connect(audioContext.destination);
          gainNode.gain.value = 0.025;
          const sineNode = new OscillatorNode(audioContext);
          sineNode.connect(gainNode);
          sineNode.start();
          await new Promise((resolve) => setTimeout(resolve, 1000));
          log.innerHTML = 'State: ' + audioContext.state;
        }
      </script>
      <body onload="onLoad()">
      <div id="log"></div>
      </body>""",
        )

    await page.route("**/*", handle)
    await page.goto("http://127.0.0.1/audio.html")
    if browser_name == "webkit":
        await expect(page.locator("#log")).to_have_text(
            re.compile(r"State: (interrupted|suspended)")
        )
    else:
        await expect(page.locator("#log")).to_have_text("State: suspended")


async def test_CA_029_should_not_crash_on_feature_detection_for_public_key_credential(
    page: Page, server: Server, context: BrowserContext
) -> None:
    await page.goto(server.EMPTY_PAGE)
    assert await page.evaluate("() => typeof PublicKeyCredential") == "function"
    assert (
        await page.evaluate("() => PublicKeyCredential.name") == "PublicKeyCredential"
    )
    assert await page.evaluate("() => ({}) instanceof PublicKeyCredential") is False
    assert (
        await page.evaluate(
            """() => {
      try {
        new PublicKeyCredential();
        return false;
      } catch (e) {
        return e instanceof TypeError;
      }
    }"""
        )
        is True
    )
    await page.evaluate(
        """async () => {
      await PublicKeyCredential.getClientCapabilities();
      await PublicKeyCredential.isConditionalMediationAvailable();
      await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    }"""
    )
    await context.credentials.install()
    assert await page.evaluate("() => typeof PublicKeyCredential") == "function"
