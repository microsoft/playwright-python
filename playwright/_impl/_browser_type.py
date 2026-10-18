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

import os
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
    prepare_browser_context_params,
)
from playwright._impl._connect import connect_to_browser
from playwright._impl._connection import ChannelOwner, api_call, from_channel
from playwright._impl._errors import Error
from playwright._impl._headers import headers_object_to_array
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    Env,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    env_object_to_array,
)
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
        if not self._initializer.get("executablePath"):
            raise Error("Browser is not supported on current platform")
        return self._initializer["executablePath"]

    @api_call
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
            ignoreAllDefaultArgs=ignore_default_args is True,
            ignoreDefaultArgs=(
                None if isinstance(ignore_default_args, bool) else ignore_default_args
            ),
            handleSIGINT=handle_sigint,
            handleSIGTERM=handle_sigterm,
            handleSIGHUP=handle_sighup,
            env=env_object_to_array(env) if env is not None else None,
            headless=headless,
            proxy=cast("Optional[channels.BrowserTypeLaunchParamsProxy]", proxy),
            downloadsPath=to_path_param(downloads_path),
            tracesDir=to_path_param(traces_dir),
            artifactsDir=to_path_param(artifacts_dir),
            chromiumSandbox=chromium_sandbox,
            firefoxUserPrefs=firefox_user_prefs,
            cdpPort=None,
            slowMo=slow_mo,
            timeout=TimeoutSettings(None).launch_timeout(timeout),
        )
        browser = cast(Browser, from_channel(result["browser"]))
        browser._connect_to_browser_type(self, {"tracesDir": to_path_param(traces_dir)})
        return browser

    @api_call
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
        selectors = self._playwright.selectors
        context_params = await prepare_browser_context_params(
            viewport=viewport,
            screen=screen,
            no_viewport=no_viewport,
            ignore_https_errors=ignore_https_errors,
            java_script_enabled=java_script_enabled,
            bypass_csp=bypass_csp,
            user_agent=user_agent,
            locale=locale,
            timezone_id=timezone_id,
            geolocation=geolocation,
            permissions=permissions,
            extra_http_headers=extra_http_headers,
            offline=offline,
            http_credentials=http_credentials,
            device_scale_factor=device_scale_factor,
            is_mobile=is_mobile,
            has_touch=has_touch,
            color_scheme=color_scheme,
            reduced_motion=reduced_motion,
            forced_colors=forced_colors,
            contrast=contrast,
            accept_downloads=accept_downloads,
            base_url=base_url,
            record_video_dir=record_video_dir,
            record_video_size=record_video_size,
            record_video_fps=record_video_fps,
            strict_selectors=strict_selectors,
            service_workers=service_workers,
            client_certificates=client_certificates,
            **selectors._with_selector_options(),
        )
        user_data_dir = str(user_data_dir)
        result = await self._channel.launchPersistentContext(
            **context_params,
            channel=channel,
            executablePath=to_path_param(executable_path),
            args=args,
            ignoreAllDefaultArgs=ignore_default_args is True,
            ignoreDefaultArgs=(
                None if isinstance(ignore_default_args, bool) else ignore_default_args
            ),
            handleSIGINT=handle_sigint,
            handleSIGTERM=handle_sigterm,
            handleSIGHUP=handle_sighup,
            env=env_object_to_array(env) if env is not None else None,
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
            userDataDir=(
                user_data_dir
                if os.path.isabs(user_data_dir) or not user_data_dir
                else os.path.abspath(user_data_dir)
            ),
            slowMo=slow_mo,
            timeout=TimeoutSettings(None).launch_timeout(timeout),
        )
        browser = cast(Browser, from_channel(result["browser"]))
        browser._connect_to_browser_type(self, {"tracesDir": to_path_param(traces_dir)})
        context = cast(BrowserContext, from_channel(result["context"]))
        await context._initialize_har_from_options(
            record_har_content=record_har_content,
            record_har_mode=record_har_mode,
            record_har_omit_content=record_har_omit_content,
            record_har_path=record_har_path,
            record_har_url_filter=record_har_url_filter,
        )
        return context

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
        if endpoint_url and self.name != "chromium" and self.name != "webkit":
            raise Error("Connecting over CDP is only supported in Chromium and WebKit.")
        result = await self._channel.connectOverCDP(
            endpointURL=endpoint_url,
            transport=None,
            headers=headers_object_to_array(headers) if headers is not None else None,
            slowMo=slow_mo,
            isLocal=is_local,
            noDefaults=no_defaults,
            isWebView=None,
            artifactsDir=to_path_param(artifacts_dir),
            timeout=TimeoutSettings(None).timeout(timeout),
        )
        return self._browser_from_connect_result(result)

    def _browser_from_connect_result(
        self, result: "channels.BrowserTypeConnectOverCDPResult"
    ) -> Browser:
        browser = cast(Browser, from_channel(result["browser"]))
        browser._connect_to_browser_type(self, {})
        return browser

    @api_call
    async def connect(
        self,
        endpoint: str,
        timeout: Optional[float],
        slow_mo: Optional[float],
        headers: Optional[Dict[str, str]],
        expose_network: Optional[str],
    ) -> Browser:
        return await self._connect(
            endpoint=endpoint,
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            expose_network=expose_network,
        )

    async def _connect(
        self,
        endpoint: str,
        timeout: Optional[float],
        slow_mo: Optional[float],
        headers: Optional[Dict[str, str]],
        expose_network: Optional[str],
    ) -> Browser:
        browser = await connect_to_browser(
            self._playwright,
            browser_name=self.name,
            endpoint=endpoint,
            headers=headers,
            expose_network=expose_network,
            slow_mo=slow_mo,
            timeout=timeout,
        )
        browser._connect_to_browser_type(self, {})
        return browser


def to_path_param(path: Optional[Union[str, Path]]) -> Optional[str]:
    return str(path) if path is not None else None
