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

"""Port of packages/playwright-core/src/client/browserType.ts.

Python differences:

- The API methods take the options of the Python API, and pass on a dict of the
  options with their Python names (see browser_context.py). _launch_params() lists
  the launch options that `{ ...options }` spreads into the parameters of the
  protocol.
- A path can be a pathlib.Path; the options have it as a string.
- A JS Set keeps the order of insertion: _contexts is a dict with None values.
- There is no logger option, so the logger is always None.
- Not ported, JavaScript only: launchServer() with BrowserServerLauncher and
  BrowserServer, connect(options) with options.wsEndpoint, and connectOverCDP()
  with an options object or a ConnectOverCDPTransport, with isConnectionTransport().
"""

import os
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Union,
)

from playwright._impl._api_structures import (
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    RecordVideoSize,
    ScreenSize,
    ViewportSize,
)
from playwright._impl_v2.browser import Browser
from playwright._impl_v2.browser_context import (
    BrowserContext,
    prepare_browser_context_params,
    to_options,
)
from playwright._impl_v2.channel_owner import ChannelOwner, api_call, from_channel
from playwright._impl_v2.client_helper import env_object_to_array
from playwright._impl_v2.connect import connect_to_browser
from playwright._impl_v2.errors import Error
from playwright._impl_v2.isomorphic.headers import headers_object_to_array
from playwright._impl_v2.timeout_settings import TimeoutSettings
from playwright._impl_v2.worker import Worker

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.playwright import Playwright
    from playwright._impl_v2.protocol_channels import BrowserTypeChannel

# Not ported: the BrowserServerLauncher and BrowserServer interfaces, for
# launchServer() (JavaScript only).


class BrowserType(ChannelOwner):
    _channel: "BrowserTypeChannel"

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.BrowserTypeInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Python: the fields, in the order of their declarations.
        # Not ported: _serverLauncher, for launchServer() (JavaScript only).
        self._contexts: Dict[BrowserContext, None] = {}
        # Python: _playwright!, which the Playwright object sets.
        self._playwright: "Playwright"

    @staticmethod
    def from_(browser_type: "BrowserTypeChannel") -> "BrowserType":
        return from_channel(browser_type)

    @property
    def executable_path(self) -> str:
        if not self._initializer.get("executablePath"):
            raise Error("Browser is not supported on current platform")
        return self._initializer["executablePath"]

    @property
    def name(self) -> str:
        return self._initializer["name"]

    @api_call()
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
        env: Optional[Dict[str, Union[str, float, bool]]],
        headless: Optional[bool],
        proxy: Optional[ProxySettings],
        downloads_path: Optional[Union[str, Path]],
        slow_mo: Optional[float],
        traces_dir: Optional[Union[str, Path]],
        artifacts_dir: Optional[Union[str, Path]],
        chromium_sandbox: Optional[bool],
        firefox_user_prefs: Optional[Dict[str, Union[str, float, bool]]],
    ) -> Browser:
        # Python: the options object, with the Python names of the options.
        options = to_options(
            executable_path=_to_path_string(executable_path),
            channel=channel,
            args=args,
            ignore_default_args=ignore_default_args,
            handle_sigint=handle_sigint,
            handle_sigterm=handle_sigterm,
            handle_sighup=handle_sighup,
            timeout=timeout,
            env=env,
            headless=headless,
            proxy=proxy,
            downloads_path=_to_path_string(downloads_path),
            slow_mo=slow_mo,
            traces_dir=_to_path_string(traces_dir),
            artifacts_dir=_to_path_string(artifacts_dir),
            chromium_sandbox=chromium_sandbox,
            firefox_user_prefs=firefox_user_prefs,
        )
        # Python: the Python API has no userDataDir and port options, so these never
        # fail.
        assert not options.get(
            "user_data_dir"
        ), "userDataDir option is not supported in `browserType.launch`. Use `browserType.launchPersistentContext` instead"
        assert not options.get(
            "port"
        ), "Cannot specify a port without launching as a server."

        # Not ported: the logger option (JavaScript only).
        options = {**(self._playwright._default_launch_options or {}), **options}
        launch_options = {
            **_launch_params(options),
            "ignoreDefaultArgs": (
                options["ignore_default_args"]
                if _is_array(options.get("ignore_default_args"))
                else None
            ),
            "ignoreAllDefaultArgs": bool(options.get("ignore_default_args"))
            and not _is_array(options.get("ignore_default_args")),
            "env": (
                env_object_to_array(options["env"])
                if options.get("env") is not None
                else None
            ),
        }
        browser = Browser.from_(
            (
                await self._channel.launch(
                    **launch_options,
                    timeout=TimeoutSettings().launch_timeout(options.get("timeout")),
                )
            )["browser"]
        )
        browser._connect_to_browser_type(self, options, None)
        return browser

    # Not ported: launchServer() (JavaScript only).

    @api_call()
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
        env: Optional[Dict[str, Union[str, float, bool]]],
        headless: Optional[bool],
        proxy: Optional[ProxySettings],
        downloads_path: Optional[Union[str, Path]],
        slow_mo: Optional[float],
        viewport: Optional[ViewportSize],
        screen: Optional[ScreenSize],
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
        color_scheme: Optional[Literal["dark", "light", "no-preference", "null"]],
        reduced_motion: Optional[Literal["no-preference", "null", "reduce"]],
        forced_colors: Optional[Literal["active", "none", "null"]],
        contrast: Optional[Literal["more", "no-preference", "null"]],
        accept_downloads: Optional[bool],
        traces_dir: Optional[Union[str, Path]],
        artifacts_dir: Optional[Union[str, Path]],
        chromium_sandbox: Optional[bool],
        firefox_user_prefs: Optional[Dict[str, Union[str, float, bool]]],
        record_har_path: Optional[Union[str, Path]],
        record_har_omit_content: Optional[bool],
        record_video_dir: Optional[Union[str, Path]],
        record_video_size: Optional[RecordVideoSize],
        record_video_fps: Optional[int],
        base_url: Optional[str],
        strict_selectors: Optional[bool],
        service_workers: Optional[Literal["allow", "block"]],
        record_har_url_filter: Optional[Union[str, Pattern[str]]],
        record_har_mode: Optional[Literal["full", "minimal"]],
        record_har_content: Optional[Literal["attach", "embed", "omit"]],
        client_certificates: Optional[Sequence[ClientCertificate]],
    ) -> BrowserContext:
        # Python: the options object, with the Python names of the options.
        options = to_options(
            channel=channel,
            executable_path=_to_path_string(executable_path),
            args=args,
            ignore_default_args=ignore_default_args,
            handle_sigint=handle_sigint,
            handle_sigterm=handle_sigterm,
            handle_sighup=handle_sighup,
            timeout=timeout,
            env=env,
            headless=headless,
            proxy=proxy,
            downloads_path=_to_path_string(downloads_path),
            slow_mo=slow_mo,
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
            traces_dir=_to_path_string(traces_dir),
            artifacts_dir=_to_path_string(artifacts_dir),
            chromium_sandbox=chromium_sandbox,
            firefox_user_prefs=firefox_user_prefs,
            record_har_path=record_har_path,
            record_har_omit_content=record_har_omit_content,
            record_video_dir=record_video_dir,
            record_video_size=record_video_size,
            record_video_fps=record_video_fps,
            base_url=base_url,
            strict_selectors=strict_selectors,
            service_workers=service_workers,
            record_har_url_filter=record_har_url_filter,
            record_har_mode=record_har_mode,
            record_har_content=record_har_content,
            client_certificates=client_certificates,
        )
        # Python: the Python API has no port option, so this never fails.
        assert not options.get(
            "port"
        ), "Cannot specify a port without launching as a server."
        options = self._playwright.selectors._with_selector_options(
            {
                **(self._playwright._default_launch_options or {}),
                **options,
            }
        )
        await self._instrumentation.run_before_create_browser_context(options)

        # Not ported: the logger option (JavaScript only).
        context_params = await prepare_browser_context_params(options)
        # Python: the path can be a pathlib.Path.
        user_data_dir = str(user_data_dir)
        persistent_params = {
            **context_params,
            # Python: { ...contextParams } has the launch options too upstream, as
            # prepareBrowserContextParams() spreads all the options.
            **_launch_params(options),
            "ignoreDefaultArgs": (
                options["ignore_default_args"]
                if _is_array(options.get("ignore_default_args"))
                else None
            ),
            "ignoreAllDefaultArgs": bool(options.get("ignore_default_args"))
            and not _is_array(options.get("ignore_default_args")),
            "env": (
                env_object_to_array(options["env"])
                if options.get("env") is not None
                else None
            ),
            "channel": options.get("channel"),
            "userDataDir": (
                user_data_dir
                if os.path.isabs(user_data_dir) or not user_data_dir
                else os.path.abspath(user_data_dir)
            ),
        }
        # Python: launchPersistentContext() has no storageState parameter; upstream,
        # the validator drops it.
        del persistent_params["storageState"]
        result = await self._channel.launchPersistentContext(
            **persistent_params,
            timeout=TimeoutSettings().launch_timeout(options.get("timeout")),
        )
        browser = Browser.from_(result["browser"])
        browser._connect_to_browser_type(self, options, None)
        context = BrowserContext.from_(result["context"])
        await context._initialize_har_from_options(
            record_har_path=options.get("record_har_path"),
            record_har_omit_content=options.get("record_har_omit_content"),
            record_har_content=options.get("record_har_content"),
            record_har_mode=options.get("record_har_mode"),
            record_har_url_filter=options.get("record_har_url_filter"),
        )
        await self._instrumentation.run_after_create_browser_context(context)
        return context

    @api_call()
    async def connect(
        self,
        endpoint: str,
        timeout: Optional[float],
        slow_mo: Optional[float],
        headers: Optional[Dict[str, str]],
        expose_network: Optional[str],
    ) -> Browser:
        # Not ported: connect(options) with options.wsEndpoint (JavaScript only).
        # Python: the options object, with the Python names of the options.
        options = to_options(
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            expose_network=expose_network,
        )
        return await self._connect({**options, "endpoint": endpoint})

    async def _connect(self, params: Dict[str, Any]) -> Browser:
        browser = await connect_to_browser(
            self._playwright, {"browser_name": self.name, **params}
        )
        browser._connect_to_browser_type(self, {}, None)
        return browser

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
        # Not ported: connectOverCDP() with an options object or with a
        # ConnectOverCDPTransport (JavaScript only), so there is no transport.
        # Python: endpoint_url is the string form, and params is the options object,
        # with the Python names of the options.
        params = to_options(
            timeout=timeout,
            slow_mo=slow_mo,
            headers=headers,
            is_local=is_local,
            no_defaults=no_defaults,
            artifacts_dir=_to_path_string(artifacts_dir),
        )
        if endpoint_url and self.name != "chromium" and self.name != "webkit":
            raise Error("Connecting over CDP is only supported in Chromium and WebKit.")

        result = await self._channel.connectOverCDP(
            endpointURL=endpoint_url,
            transport=None,
            headers=(
                headers_object_to_array(params["headers"])
                if params.get("headers") is not None
                else None
            ),
            slowMo=params.get("slow_mo"),
            isLocal=params.get("is_local"),
            noDefaults=params.get("no_defaults"),
            # Python: the Python API has no isWebView option.
            isWebView=None,
            artifactsDir=params.get("artifacts_dir"),
            timeout=TimeoutSettings().timeout(params.get("timeout")),
        )
        return await self._browser_from_connect_result(result)

    async def _browser_from_connect_result(
        self, result: "channels.BrowserTypeConnectOverCDPResult"
    ) -> Browser:
        browser = Browser.from_(result["browser"])
        browser._connect_to_browser_type(self, {}, None)
        if result["defaultContext"]:
            await self._instrumentation.run_after_create_browser_context(
                BrowserContext.from_(result["defaultContext"])
            )
        return browser

    async def _connect_to_worker(
        self, endpoint: str, timeout: Optional[float]
    ) -> Worker:
        if self.name != "chromium":
            raise Error("Connecting to workers is only supported in Chromium.")
        result = await self._channel.connectToWorker(
            endpoint=endpoint,
            timeout=TimeoutSettings().timeout(timeout),
        )
        return Worker.from_(result["worker"])

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<BrowserType name={self.name} executable_path={self.executable_path}>"


# Not ported: isConnectionTransport(), for connectOverCDP() with a
# ConnectOverCDPTransport (JavaScript only).

# Python only: helpers that upstream does not need.


def _launch_params(options: Dict[str, Any]) -> Dict[str, Any]:
    """The launch options that `{ ...options }` spreads into the parameters of the
    protocol, by their protocol names. ignoreDefaultArgs, ignoreAllDefaultArgs and env
    are the explicit parameters of launch() and launchPersistentContext()."""
    return {
        "channel": options.get("channel"),
        "executablePath": options.get("executable_path"),
        "args": options.get("args"),
        "handleSIGINT": options.get("handle_sigint"),
        "handleSIGTERM": options.get("handle_sigterm"),
        "handleSIGHUP": options.get("handle_sighup"),
        "headless": options.get("headless"),
        "proxy": options.get("proxy"),
        "downloadsPath": options.get("downloads_path"),
        "tracesDir": options.get("traces_dir"),
        "artifactsDir": options.get("artifacts_dir"),
        "chromiumSandbox": options.get("chromium_sandbox"),
        "firefoxUserPrefs": options.get("firefox_user_prefs"),
        # The Python API has no cdpPort option.
        "cdpPort": None,
        "slowMo": options.get("slow_mo"),
    }


def _is_array(value: Any) -> bool:
    # Array.isArray(): the API takes a list or a tuple.
    return isinstance(value, (list, tuple))


def _to_path_string(path: Optional[Union[str, Path]]) -> Optional[str]:
    return str(path) if path is not None else None
