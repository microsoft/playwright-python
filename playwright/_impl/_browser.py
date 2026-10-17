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
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Pattern,
    Sequence,
    Union,
    cast,
)

from playwright._impl._api_structures import (
    BrowserBindResult,
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    StorageState,
    ViewportSize,
)
from playwright._impl._artifact import Artifact
from playwright._impl._browser_context import (
    BrowserContext,
    to_accept_downloads_params,
    to_record_video_params,
    to_storage_state_params,
)
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._headers import serialize_headers
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    make_dirs_for_file,
)
from playwright._impl._network import (
    to_client_certificates_protocol,
    to_http_credentials_protocol,
    validate_headers,
)
from playwright._impl._page import Page

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._browser_type import BrowserType
    from playwright._impl._protocol_channels import BrowserChannel


class Browser(ChannelOwner):
    _channel: "BrowserChannel"

    Events = SimpleNamespace(
        Context="context",
        Disconnected="disconnected",
    )

    def __init__(
        self, parent: "BrowserType", type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._browser_type: Optional["BrowserType"] = None
        self._is_connected = True
        self._should_close_connection_on_close = False
        self._cr_tracing_path: Optional[str] = None

        # In creation order, like the Set in browser.ts.
        self._contexts: List[BrowserContext] = []
        self._traces_dir: Optional[str] = None
        self._channel.onContext(
            lambda event: self._did_create_context(
                cast(BrowserContext, from_channel(event["context"]))
            )
        )
        self._channel.onClose(lambda: self._on_close())
        self._close_reason: Optional[str] = None
        self._closed_future: asyncio.Future = self._loop.create_future()

    def __repr__(self) -> str:
        return f"<Browser type={self._browser_type} version={self.version}>"

    def _connect_to_browser_type(
        self,
        browser_type: "BrowserType",
        traces_dir: Optional[str] = None,
    ) -> None:
        # Note: when using connect(), `browserType` is different from `this.parent`.
        # This is why browser type is not wired up in the constructor, and instead this separate method is called later on.
        self._browser_type = browser_type
        self._traces_dir = traces_dir
        for context in self._contexts:
            self._setup_browser_context(context)

    def _did_create_context(self, context: BrowserContext) -> None:
        context._browser = self
        self._contexts.append(context)
        # Note: when connecting to a browser, initial contexts arrive before `_browserType` is set,
        # and will be configured later in `ConnectToBrowserType`.
        if self._browser_type:
            self._setup_browser_context(context)
        self.emit(Browser.Events.Context, context)

    def _setup_browser_context(self, context: BrowserContext) -> None:
        context._tracing._traces_dir = self._traces_dir
        context._request._tracing._traces_dir = self._traces_dir
        assert self._browser_type is not None
        self._browser_type._playwright.selectors._contexts_for_selectors.add(context)

    def _on_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected, self)
        if not self._closed_future.done():
            self._closed_future.set_result(None)

    @property
    def contexts(self) -> List[BrowserContext]:
        return list(self._contexts)

    @property
    def browser_type(self) -> "BrowserType":
        assert self._browser_type is not None
        return self._browser_type

    def is_connected(self) -> bool:
        return self._is_connected

    async def new_context(
        self,
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
        default_browser_type: Optional[str],  # Not a protocol parameter; not sent.
        proxy: Optional[ProxySettings],
        record_har_path: Optional[Union[Path, str]],
        record_har_omit_content: Optional[bool],
        record_video_dir: Optional[Union[Path, str]],
        record_video_size: Optional[ViewportSize],
        storage_state: Optional[Union[StorageState, str, Path]],
        base_url: Optional[str],
        strict_selectors: Optional[bool],
        service_workers: Optional[ServiceWorkersPolicy],
        record_har_url_filter: Optional[Union[Pattern[str], str]],
        record_har_mode: Optional[HarMode],
        record_har_content: Optional[HarContentPolicy],
        client_certificates: Optional[List[ClientCertificate]],
        record_video_fps: Optional[int],
    ) -> BrowserContext:
        assert self._browser_type is not None
        if extra_http_headers:
            validate_headers(extra_http_headers)
        selectors = self._browser_type._playwright.selectors
        result = await self._channel.newContext(
            noDefaultViewport=True if no_viewport else None,
            viewport=viewport,
            screen=screen,
            ignoreHTTPSErrors=ignore_https_errors,
            clientCertificates=cast(
                "Optional[List[channels.BrowserNewContextParamsClientCertificates]]",
                await to_client_certificates_protocol(client_certificates),
            ),
            javaScriptEnabled=java_script_enabled,
            bypassCSP=bypass_csp,
            userAgent=user_agent,
            locale=locale,
            timezoneId=timezone_id,
            geolocation=cast(
                "Optional[channels.BrowserNewContextParamsGeolocation]", geolocation
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
            proxy=cast("Optional[channels.BrowserNewContextParamsProxy]", proxy),
            storageState=await to_storage_state_params(storage_state),
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

    async def new_page(
        self,
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
        forced_colors: Optional[ForcedColors],
        contrast: Optional[Contrast],
        reduced_motion: Optional[ReducedMotion],
        accept_downloads: Optional[bool],
        default_browser_type: Optional[str],
        proxy: Optional[ProxySettings],
        record_har_path: Optional[Union[Path, str]],
        record_har_omit_content: Optional[bool],
        record_video_dir: Optional[Union[Path, str]],
        record_video_size: Optional[ViewportSize],
        storage_state: Optional[Union[StorageState, str, Path]],
        base_url: Optional[str],
        strict_selectors: Optional[bool],
        service_workers: Optional[ServiceWorkersPolicy],
        record_har_url_filter: Optional[Union[Pattern[str], str]],
        record_har_mode: Optional[HarMode],
        record_har_content: Optional[HarContentPolicy],
        client_certificates: Optional[List[ClientCertificate]],
        record_video_fps: Optional[int],
    ) -> Page:
        async def inner() -> Page:
            context = await self.new_context(
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
                default_browser_type=default_browser_type,
                proxy=proxy,
                record_har_path=record_har_path,
                record_har_omit_content=record_har_omit_content,
                record_video_dir=record_video_dir,
                record_video_size=record_video_size,
                storage_state=storage_state,
                base_url=base_url,
                strict_selectors=strict_selectors,
                service_workers=service_workers,
                record_har_url_filter=record_har_url_filter,
                record_har_mode=record_har_mode,
                record_har_content=record_har_content,
                client_certificates=client_certificates,
                record_video_fps=record_video_fps,
            )
            page = await context.new_page()
            page._owned_context = context
            context._owner_page = page
            return page

        return await self._connection.wrap_api_call(inner, title="Create page")

    async def close(self, reason: Optional[str]) -> None:
        # Port of Browser.close() in client/browser.ts: it returns after the
        # "disconnected" event.
        self._close_reason = reason
        try:
            if self._should_close_connection_on_close:
                await self._connection.stop_async()
            else:
                await self._channel.close(reason=reason)
            await self._closed_future
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    @property
    def version(self) -> str:
        return self._initializer["version"]

    async def new_browser_cdp_session(self) -> CDPSession:
        return from_channel((await self._channel.newBrowserCDPSession())["session"])

    async def bind(
        self,
        title: str,
        workspace_dir: Optional[str],
        host: Optional[str],
        port: Optional[int],
    ) -> BrowserBindResult:
        return await self._channel.startServer(
            title=title, workspaceDir=workspace_dir, metadata=None, host=host, port=port
        )

    async def unbind(self) -> None:
        await self._channel.stopServer()

    async def start_tracing(
        self,
        page: Optional[Page],
        path: Optional[Union[str, Path]],
        screenshots: Optional[bool],
        categories: Optional[Sequence[str]],
    ) -> None:
        # The client writes the trace to `path` in stop_tracing().
        if path:
            self._cr_tracing_path = str(path)
        await self._channel.startTracing(
            page=page._channel if page else None,
            screenshots=screenshots,
            categories=categories,
        )

    async def stop_tracing(self) -> bytes:
        artifact = cast(
            Artifact, from_channel((await self._channel.stopTracing())["artifact"])
        )
        buffer = await artifact.read_info_buffer()
        await artifact.delete()
        if self._cr_tracing_path:
            make_dirs_for_file(self._cr_tracing_path)
            with open(self._cr_tracing_path, "wb") as f:
                f.write(buffer)
            self._cr_tracing_path = None
        return buffer
