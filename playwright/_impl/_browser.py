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
    Any,
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
    prepare_browser_context_params,
    prepare_storage_state,
)
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import ChannelOwner, api_call, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._file_utils import mkdir_if_needed
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    async_writefile,
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
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._browser_type: Optional["BrowserType"] = None
        self._is_connected = True
        self._should_close_connection_on_close = False
        self._path: Optional[str] = None

        # In creation order, like the Set in browser.ts.
        self._contexts: List[BrowserContext] = []
        # The launch options, with the protocol names; only tracesDir is read.
        self._options: Dict[str, Any] = {}
        self._channel.onContext(
            lambda event: self._did_create_context(
                cast(BrowserContext, from_channel(event["context"]))
            )
        )
        self._channel.onClose(lambda: self._did_close())
        self._close_reason: Optional[str] = None
        self._closed_future: asyncio.Future = self._loop.create_future()
        self.once(
            Browser.Events.Disconnected,
            lambda browser: self._closed_future.set_result(None),
        )

    def __repr__(self) -> str:
        return f"<Browser type={self._browser_type} version={self.version}>"

    @property
    def browser_type(self) -> "BrowserType":
        assert self._browser_type is not None
        return self._browser_type

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
        # Port of _innerNewContext() in browser.ts.
        assert self._browser_type is not None
        selectors = self._browser_type._playwright.selectors
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
        result = await self._channel.newContext(
            **context_params,
            proxy=cast("Optional[channels.BrowserNewContextParamsProxy]", proxy),
            storageState=(
                await prepare_storage_state(storage_state) if storage_state else None
            ),
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

    def _connect_to_browser_type(
        self, browser_type: "BrowserType", browser_options: Dict[str, Any]
    ) -> None:
        # Note: when using connect(), `browserType` is different from `this._parent`.
        # This is why browser type is not wired up in the constructor,
        # and instead this separate method is called later on.
        self._browser_type = browser_type
        self._options = browser_options
        for context in self._contexts:
            self._setup_browser_context(context)

    def _did_create_context(self, context: BrowserContext) -> None:
        context._browser = self
        self._contexts.append(context)
        # Note: when connecting to a browser, initial contexts arrive before `browserType` is set,
        # and will be configured later in `_connectToBrowserType`.
        if self._browser_type:
            self._setup_browser_context(context)
        self.emit(Browser.Events.Context, context)

    def _setup_browser_context(self, context: BrowserContext) -> None:
        context._tracing._traces_dir = self._options.get("tracesDir")
        context._request._tracing._traces_dir = self._options.get("tracesDir")
        assert self._browser_type is not None
        self._browser_type._playwright.selectors._contexts_for_selectors.add(context)

    @property
    def contexts(self) -> List[BrowserContext]:
        return list(self._contexts)

    @property
    def version(self) -> str:
        return self._initializer["version"]

    async def bind(
        self,
        title: str,
        workspace_dir: Optional[str],
        host: Optional[str],
        port: Optional[int],
    ) -> BrowserBindResult:
        result = await self._channel.startServer(
            title=title, workspaceDir=workspace_dir, metadata=None, host=host, port=port
        )
        return {"endpoint": result["endpoint"]}

    async def unbind(self) -> None:
        await self._channel.stopServer()

    @api_call(title="Create page")
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

    def is_connected(self) -> bool:
        return self._is_connected

    async def new_browser_cdp_session(self) -> CDPSession:
        return from_channel((await self._channel.newBrowserCDPSession())["session"])

    async def start_tracing(
        self,
        page: Optional[Page],
        path: Optional[Union[str, Path]],
        screenshots: Optional[bool],
        categories: Optional[Sequence[str]],
    ) -> None:
        self._path = str(path) if path is not None else None
        await self._channel.startTracing(
            page=page._channel if page else None,
            screenshots=screenshots,
            categories=categories,
        )

    async def stop_tracing(self) -> bytes:
        artifact = cast(
            Artifact, from_channel((await self._channel.stopTracing())["artifact"])
        )
        buffer = await artifact.read_into_buffer()
        await artifact.delete()
        if self._path:
            mkdir_if_needed(self._path)
            await async_writefile(self._path, buffer)
            self._path = None
        return buffer

    async def close(self, reason: Optional[str]) -> None:
        self._close_reason = reason
        try:
            if self._should_close_connection_on_close:
                self._connection.close()
            else:
                await self._channel.close(reason=reason)
            await self._closed_future
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e

    def _did_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected, self)
