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
import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Sequence, Union, cast

from playwright._impl._api_structures import (
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    ViewportSize,
)
from playwright._impl._browser import Browser
from playwright._impl._browser_context import (
    BrowserContext,
    to_accept_downloads_params,
    to_record_video_params,
)
from playwright._impl._connection import ChannelOwner, Connection, from_channel
from playwright._impl._errors import Error, TargetClosedError
from playwright._impl._headers import serialize_headers
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    Env,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
)
from playwright._impl._json_pipe import JsonPipeTransport
from playwright._impl._network import (
    to_client_certificates_protocol,
    to_http_credentials_protocol,
    validate_headers,
)
from playwright._impl._time import monotonic_time
from playwright._impl._timeout_settings import TimeoutSettings

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._playwright import Playwright
    from playwright._impl._protocol_channels import BrowserTypeChannel


class BrowserType(ChannelOwner):
    _channel: "BrowserTypeChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._playwright: "Playwright"

    def __repr__(self) -> str:
        return f"<BrowserType name={self.name} executable_path={self.executable_path}>"

    @property
    def name(self) -> str:
        return self._initializer["name"]

    @property
    def executable_path(self) -> str:
        return self._initializer["executablePath"]

    async def launch(
        self,
        executable_path: Optional[Union[str, Path]],
        channel: Optional[str],
        args: Optional[Sequence[str]],
        ignore_default_args: Optional[Union[bool, Sequence[str]]],
        handle_sigint: Optional[bool],
        handle_sigterm: Optional[bool],
        handle_sighup: Optional[bool],
        timeout: Optional[float],
        env: Optional[Env],
        headless: Optional[bool],
        proxy: Optional[ProxySettings],
        downloads_path: Optional[Union[str, Path]],
        slow_mo: Optional[float],
        traces_dir: Optional[Union[pathlib.Path, str]],
        artifacts_dir: Optional[Union[pathlib.Path, str]],
        chromium_sandbox: Optional[bool],
        firefox_user_prefs: Optional[Dict[str, Union[str, float, bool]]],
    ) -> Browser:
        result = await self._channel.launch(
            channel=channel,
            executablePath=to_path_param(executable_path),
            args=args,
            ignoreAllDefaultArgs=True if ignore_default_args is True else None,
            ignoreDefaultArgs=(
                None if isinstance(ignore_default_args, bool) else ignore_default_args
            ),
            handleSIGINT=handle_sigint,
            handleSIGTERM=handle_sigterm,
            handleSIGHUP=handle_sighup,
            env=to_env_params(env),
            headless=headless,
            proxy=cast("Optional[channels.BrowserTypeLaunchParamsProxy]", proxy),
            downloadsPath=to_path_param(downloads_path),
            tracesDir=to_path_param(traces_dir),
            artifactsDir=to_path_param(artifacts_dir),
            chromiumSandbox=chromium_sandbox,
            firefoxUserPrefs=firefox_user_prefs,
            cdpPort=None,
            slowMo=slow_mo,
            timeout=TimeoutSettings.launch_timeout(timeout),
        )
        browser = cast(Browser, from_channel(result["browser"]))
        browser._connect_to_browser_type(
            self, str(traces_dir) if traces_dir is not None else None
        )
        return browser

    async def launch_persistent_context(
        self,
        user_data_dir: Union[str, Path],
        channel: Optional[str],
        executable_path: Optional[Union[str, Path]],
        args: Optional[Sequence[str]],
        ignore_default_args: Optional[Union[bool, Sequence[str]]],
        handle_sigint: Optional[bool],
        handle_sigterm: Optional[bool],
        handle_sighup: Optional[bool],
        timeout: Optional[float],
        env: Optional[Env],
        headless: Optional[bool],
        proxy: Optional[ProxySettings],
        downloads_path: Optional[Union[str, Path]],
        slow_mo: Optional[float],
        viewport: Optional[ViewportSize],
        screen: Optional[ViewportSize],
        no_viewport: Optional[bool],
        ignore_https_errors: Optional[bool],
        java_script_enabled: Optional[bool],
        bypass_csp: Optional[bool],
        user_agent: Optional[str],
        locale: Optional[str],
        timezone_id: Optional[str],
        geolocation: Optional[Geolocation],
        permissions: Optional[Sequence[str]],
        extra_http_headers: Optional[Dict[str, str]],
        offline: Optional[bool],
        http_credentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
        device_scale_factor: Optional[float],
        is_mobile: Optional[bool],
        has_touch: Optional[bool],
        color_scheme: Optional[ColorScheme],
        reduced_motion: Optional[ReducedMotion],
        forced_colors: Optional[ForcedColors],
        contrast: Optional[Contrast],
        accept_downloads: Optional[bool],
        traces_dir: Optional[Union[pathlib.Path, str]],
        artifacts_dir: Optional[Union[pathlib.Path, str]],
        chromium_sandbox: Optional[bool],
        firefox_user_prefs: Optional[Dict[str, Union[str, float, bool]]],
        record_har_path: Optional[Union[Path, str]],
        record_har_omit_content: Optional[bool],
        record_video_dir: Optional[Union[Path, str]],
        record_video_size: Optional[ViewportSize],
        base_url: Optional[str],
        strict_selectors: Optional[bool],
        service_workers: Optional[ServiceWorkersPolicy],
        record_har_url_filter: Optional[Union[Pattern[str], str]],
        record_har_mode: Optional[HarMode],
        record_har_content: Optional[HarContentPolicy],
        client_certificates: Optional[List[ClientCertificate]],
        record_video_fps: Optional[int],
    ) -> BrowserContext:
        if extra_http_headers:
            validate_headers(extra_http_headers)
        selectors = self._playwright.selectors
        result = await self._channel.launchPersistentContext(
            channel=channel,
            executablePath=to_path_param(executable_path),
            args=args,
            ignoreAllDefaultArgs=True if ignore_default_args is True else None,
            ignoreDefaultArgs=(
                None if isinstance(ignore_default_args, bool) else ignore_default_args
            ),
            handleSIGINT=handle_sigint,
            handleSIGTERM=handle_sigterm,
            handleSIGHUP=handle_sighup,
            env=to_env_params(env),
            headless=headless,
            proxy=cast(
                "Optional[channels.BrowserTypeLaunchPersistentContextParamsProxy]",
                proxy,
            ),
            downloadsPath=to_path_param(downloads_path),
            tracesDir=to_path_param(traces_dir),
            artifactsDir=to_path_param(artifacts_dir),
            chromiumSandbox=chromium_sandbox,
            firefoxUserPrefs=firefox_user_prefs,
            cdpPort=None,
            noDefaultViewport=True if no_viewport else None,
            viewport=viewport,
            screen=screen,
            ignoreHTTPSErrors=ignore_https_errors,
            clientCertificates=cast(
                "Optional[List[channels.BrowserTypeLaunchPersistentContextParamsClientCertificates]]",
                await to_client_certificates_protocol(client_certificates),
            ),
            javaScriptEnabled=java_script_enabled,
            bypassCSP=bypass_csp,
            userAgent=user_agent,
            locale=locale,
            timezoneId=timezone_id,
            geolocation=cast(
                "Optional[channels.BrowserTypeLaunchPersistentContextParamsGeolocation]",
                geolocation,
            ),
            permissions=permissions,
            extraHTTPHeaders=(
                serialize_headers(extra_http_headers)
                if extra_http_headers is not None
                else None
            ),
            offline=offline,
            httpCredentials=cast(
                "Optional[List[channels.HttpCredentials]]",
                to_http_credentials_protocol(http_credentials),
            ),
            deviceScaleFactor=device_scale_factor,
            isMobile=is_mobile,
            hasTouch=has_touch,
            colorScheme="no-override" if color_scheme == "null" else color_scheme,
            reducedMotion=(
                "no-override" if reduced_motion == "null" else reduced_motion
            ),
            forcedColors="no-override" if forced_colors == "null" else forced_colors,
            acceptDownloads=to_accept_downloads_params(accept_downloads),
            contrast="no-override" if contrast == "null" else contrast,
            baseURL=base_url,
            recordVideo=to_record_video_params(
                record_video_dir, record_video_size, record_video_fps
            ),
            strictSelectors=strict_selectors,
            serviceWorkers=service_workers,
            selectorEngines=selectors._selector_engines,
            testIdAttributeName=selectors._test_id_attribute_name,
            userDataDir=self._user_data_dir(user_data_dir),
            slowMo=slow_mo,
            timeout=TimeoutSettings.launch_timeout(timeout),
        )
        browser = cast(Browser, from_channel(result["browser"]))
        browser._connect_to_browser_type(
            self, str(traces_dir) if traces_dir is not None else None
        )
        context = cast(BrowserContext, from_channel(result["context"]))
        await context._initialize_har_from_options(
            record_har_content=record_har_content,
            record_har_mode=record_har_mode,
            record_har_omit_content=record_har_omit_content,
            record_har_path=record_har_path,
            record_har_url_filter=record_har_url_filter,
        )
        return context

    def _user_data_dir(self, user_data_dir: Optional[Union[str, Path]]) -> str:
        if not user_data_dir:
            return ""
        if not Path(user_data_dir).is_absolute():
            return str(Path(user_data_dir).resolve())
        return str(Path(user_data_dir))

    async def connect_over_cdp(
        self,
        endpoint_url: str,
        timeout: Optional[float],
        slow_mo: Optional[float],
        headers: Optional[Dict[str, str]],
        is_local: Optional[bool],
        no_defaults: Optional[bool],
        artifacts_dir: Optional[Union[str, Path]],
    ) -> Browser:
        # Port of BrowserType.connectOverCDP() in client/browserType.ts.
        if self.name != "chromium" and self.name != "webkit":
            raise Error("Connecting over CDP is only supported in Chromium and WebKit.")
        result = await self._channel.connectOverCDP(
            endpointURL=endpoint_url,
            headers=serialize_headers(headers) if headers is not None else None,
            slowMo=slow_mo,
            isLocal=is_local,
            noDefaults=no_defaults,
            isWebView=None,
            artifactsDir=str(artifacts_dir) if artifacts_dir is not None else None,
            transport=None,
            timeout=TimeoutSettings.launch_timeout(timeout),
        )
        browser = cast(Browser, from_channel(result["browser"]))
        browser._connect_to_browser_type(self, None)

        return browser

    async def connect(
        self,
        endpoint: str,
        timeout: Optional[float],
        slow_mo: Optional[float],
        headers: Optional[Dict[str, str]],
        expose_network: Optional[str],
    ) -> Browser:
        # Like @apiCall() in client/browserType.ts: the errors that the client
        # raises itself also start with "BrowserType.connect: ".
        return await self._connection.wrap_api_call(
            lambda: self._connect(endpoint, timeout, slow_mo, headers, expose_network)
        )

    async def _connect(
        self,
        endpoint: str,
        timeout: Optional[float],
        slow_mo: Optional[float],
        headers: Optional[Dict[str, str]],
        expose_network: Optional[str],
    ) -> Browser:
        # Port of connectToBrowser() and connectToEndpoint() in client/connect.ts.
        if slow_mo is None:
            slow_mo = 0
        if timeout is None:
            timeout = 0
        deadline = monotonic_time() + timeout if timeout else 0

        headers = {**(headers if headers else {}), "x-playwright-browser": self.name}
        local_utils = self._connection.local_utils
        result = await local_utils._channel.connect(
            endpoint=endpoint,
            headers=headers,
            exposeNetwork=expose_network,
            slowMo=slow_mo,
            socksProxyRedirectPortForTest=None,
            timeout=timeout,
        )
        transport = JsonPipeTransport(self._connection._loop, result["pipe"])

        connection = Connection(
            self._connection._dispatcher_fiber,
            self._connection._object_factory,
            transport,
            self._connection._loop,
            local_utils=self._connection.local_utils,
        )
        connection.mark_as_remote()
        playwright_future = connection.playwright_future

        browser = None

        def handle_transport_close(reason: Optional[str]) -> None:
            if browser:
                for context in browser.contexts:
                    for page in context.pages:
                        page._on_close()
                    context._on_close()
            connection.cleanup(reason)
            # cleanup() cancels the initialize call; upstream's connection.close()
            # rejects it with the close error.
            if not playwright_future.done():
                playwright_future.set_exception(
                    connection._closed_error or TargetClosedError(reason)
                )
            # Give a chance to any API call promises to reject upon page/context closure.
            # This happens naturally when we receive page.onClose and browser.onClose from the server
            # in separate tasks. However, upon pipe closure we used to dispatch them all synchronously
            # here and promises did not have a chance to reject.
            # The order of rejects vs closure is a part of the API contract and our test runner
            # relies on it to attribute rejections to the right test.
            # The sync API resumes its greenlet in a callback of the task that it waits
            # for, one loop iteration later, so there the event waits one more iteration.
            if browser:
                if connection._is_sync:
                    connection._loop.call_soon(
                        connection._loop.call_soon, browser._on_close
                    )
                else:
                    connection._loop.call_soon(browser._on_close)

        transport.once("close", handle_transport_close)

        connection._is_sync = self._connection._is_sync
        connection._loop.create_task(connection.run())

        def close_connection() -> None:
            # Port of connection.close() in client/connection.ts, which also closes
            # the transport in client/connect.ts.
            if not playwright_future.done():
                playwright_future.cancel()
            connection.cleanup()
            try:
                transport.request_stop()
            except Error:
                pass

        try:
            done, _ = await asyncio.wait(
                {transport.on_error_future, playwright_future},
                timeout=(
                    max(0, deadline - monotonic_time()) / 1000 if deadline else None
                ),
                return_when=asyncio.FIRST_COMPLETED,
            )
        except BaseException:
            close_connection()
            raise
        if not done:
            close_connection()
            raise Error(f"Timeout {timeout}ms exceeded")
        if not playwright_future.done():
            transport.on_error_future.result()
        playwright: "Playwright" = playwright_future.result()
        pre_launched_browser = playwright._initializer.get("preLaunchedBrowser")
        if not pre_launched_browser:
            close_connection()
            raise Error(
                "Malformed endpoint. Did you use BrowserType.launchServer method?"
            )
        playwright._set_selectors(self._playwright.selectors)
        self._connection._child_ws_connections.append(connection)
        browser = cast(Browser, from_channel(pre_launched_browser))
        browser._should_close_connection_on_close = True
        browser._connect_to_browser_type(self, None)

        return browser


def to_env_params(env: Optional[Env]) -> Optional[List["channels.NameValue"]]:
    if env is None:
        return None
    return [{"name": name, "value": str(value)} for name, value in env.items()]


def to_path_param(path: Optional[Union[str, Path]]) -> Optional[str]:
    return str(Path(path)) if path is not None else None
