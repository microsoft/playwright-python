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

"""Port of packages/playwright-core/src/client/browser.ts.

Python differences:

- new_context() and new_page() take the options of the Python API, and pass on a
  dict of the options with their Python names (see browser_context.py). The launch
  options in _options have their Python names too.
- A JS Set keeps the order of insertion: _contexts is a dict with None values.
- There is no logger option, so the logger is always None.
- Not ported: [Symbol.asyncDispose]() (JavaScript only).
"""

import asyncio
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
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
    RecordVideoSize,
    ScreenSize,
    StorageState,
    ViewportSize,
)
from playwright._impl_v2.artifact import Artifact
from playwright._impl_v2.browser_context import (
    BrowserContext,
    prepare_browser_context_params,
    to_options,
    write_file,
)
from playwright._impl_v2.cdp_session import CDPSession
from playwright._impl_v2.channel_owner import ChannelOwner, api_call, from_channel
from playwright._impl_v2.errors import is_target_closed_error
from playwright._impl_v2.events import Events
from playwright._impl_v2.file_utils import mkdir_if_needed
from playwright._impl_v2.timeout_settings import NO_TIMEOUT

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.browser_type import BrowserType
    from playwright._impl_v2.page import Page
    from playwright._impl_v2.protocol_channels import BrowserChannel


class Browser(ChannelOwner):
    _channel: "BrowserChannel"

    @staticmethod
    def from_(browser: "BrowserChannel") -> "Browser":
        return from_channel(browser)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.BrowserInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        # Python: the fields, in the order of their declarations.
        self._contexts: Dict[BrowserContext, None] = {}
        self._is_connected = True
        self._closed_promise: "asyncio.Future[None]"
        self._should_close_connection_on_close = False
        # Python: _browserType!, which _connect_to_browser_type() sets.
        self._browser_type: "BrowserType" = cast("BrowserType", None)
        self._options: Dict[str, Any] = {}
        self._name: str
        self._browser_name: Literal["chromium", "webkit", "firefox"]
        self._path: Optional[Union[str, Path]] = None
        self._close_reason: Optional[str] = None

        self._name = initializer["name"]
        self._browser_name = initializer["browserName"]
        self._channel.onContext(
            lambda event: self._did_create_context(
                BrowserContext.from_(event["context"])
            )
        )
        self._channel.onClose(lambda: self._did_close())
        self._closed_promise = self._loop.create_future()
        self.once(
            Events.Browser.Disconnected,
            lambda browser: self._closed_promise.set_result(None),
        )

    @property
    def browser_type(self) -> "BrowserType":
        return self._browser_type

    async def new_context(
        self,
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
        default_browser_type: Optional[str],
        proxy: Optional[ProxySettings],
        record_har_path: Optional[Union[str, Path]],
        record_har_omit_content: Optional[bool],
        record_video_dir: Optional[Union[str, Path]],
        record_video_size: Optional[RecordVideoSize],
        record_video_fps: Optional[int],
        storage_state: Optional[Union[StorageState, str, Path]],
        base_url: Optional[str],
        strict_selectors: Optional[bool],
        service_workers: Optional[Literal["allow", "block"]],
        record_har_url_filter: Optional[Union[str, Pattern[str]]],
        record_har_mode: Optional[Literal["full", "minimal"]],
        record_har_content: Optional[Literal["attach", "embed", "omit"]],
        client_certificates: Optional[Sequence[ClientCertificate]],
    ) -> BrowserContext:
        # Python: the options object, with the Python names of the options.
        # default_browser_type is the browser of a device descriptor; it is not an
        # option of the context.
        options = to_options(
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
            proxy=proxy,
            record_har_path=record_har_path,
            record_har_omit_content=record_har_omit_content,
            record_video_dir=record_video_dir,
            record_video_size=record_video_size,
            record_video_fps=record_video_fps,
            storage_state=storage_state,
            base_url=base_url,
            strict_selectors=strict_selectors,
            service_workers=service_workers,
            record_har_url_filter=record_har_url_filter,
            record_har_mode=record_har_mode,
            record_har_content=record_har_content,
            client_certificates=client_certificates,
        )
        return await self._inner_new_context(options, False)

    async def _new_context_for_reuse(self, options: Dict[str, Any]) -> BrowserContext:
        return await self._inner_new_context(options, True)

    async def _disconnect_from_reused_context(self, reason: str) -> None:
        context = next(
            (context for context in self._contexts if context._for_reuse), None
        )
        if not context:
            return
        await self._instrumentation.run_before_close_browser_context(context)
        for page in context.pages:
            page._on_close()
        context._on_close()
        await self._channel.disconnectFromReusedContext(
            reason=reason, timeout=NO_TIMEOUT
        )

    async def _inner_new_context(
        self, user_options: Dict[str, Any], for_reuse: bool
    ) -> BrowserContext:
        options = self._browser_type._playwright.selectors._with_selector_options(
            user_options
        )
        await self._instrumentation.run_before_create_browser_context(options)
        context_options = await prepare_browser_context_params(options)
        response = (
            await self._channel.newContextForReuse(
                **context_options, timeout=NO_TIMEOUT
            )
            if for_reuse
            else await self._channel.newContext(**context_options, timeout=NO_TIMEOUT)
        )
        context = BrowserContext.from_(response["context"])
        if for_reuse:
            context._for_reuse = True
        # Not ported: the logger option (JavaScript only).
        await context._initialize_har_from_options(
            record_har_path=options.get("record_har_path"),
            record_har_omit_content=options.get("record_har_omit_content"),
            record_har_content=options.get("record_har_content"),
            record_har_mode=options.get("record_har_mode"),
            record_har_url_filter=options.get("record_har_url_filter"),
        )
        await self._instrumentation.run_after_create_browser_context(context)
        return context

    def _connect_to_browser_type(
        self,
        browser_type: "BrowserType",
        browser_options: Dict[str, Any],
        logger: Any,
    ) -> None:
        # Note: when using connect(), `browserType` is different from `this._parent`.
        # This is why browser type is not wired up in the constructor,
        # and instead this separate method is called later on.
        self._browser_type = browser_type
        self._options = browser_options
        self._logger = logger
        for context in list(self._contexts):
            self._setup_browser_context(context)

    def _did_create_context(self, context: BrowserContext) -> None:
        context._browser = self
        self._contexts[context] = None
        # Note: when connecting to a browser, initial contexts arrive before `browserType` is set,
        # and will be configured later in `_connectToBrowserType`.
        if self._browser_type:
            self._setup_browser_context(context)
        self.emit(Events.Browser.Context, context)

    def _setup_browser_context(self, context: BrowserContext) -> None:
        context._logger = self._logger
        context.tracing._traces_dir = self._options.get("traces_dir")
        context.request.tracing._traces_dir = self._options.get("traces_dir")
        self._browser_type._contexts[context] = None
        self._browser_type._playwright.selectors._contexts_for_selectors.add(context)
        context.set_default_timeout(
            timeout=self._browser_type._playwright._default_context_timeout
        )
        context.set_default_navigation_timeout(
            timeout=self._browser_type._playwright._default_context_navigation_timeout
        )

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
        # Python: the Python API has no metadata option.
        result = await self._channel.startServer(
            title=title,
            workspaceDir=workspace_dir,
            metadata=None,
            host=host,
            port=port,
            timeout=NO_TIMEOUT,
        )
        endpoint = result["endpoint"]
        return {"endpoint": endpoint}

    async def unbind(self) -> None:
        await self._channel.stopServer(timeout=NO_TIMEOUT)

    @api_call(title="Create page")
    async def new_page(
        self,
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
        default_browser_type: Optional[str],
        proxy: Optional[ProxySettings],
        record_har_path: Optional[Union[str, Path]],
        record_har_omit_content: Optional[bool],
        record_video_dir: Optional[Union[str, Path]],
        record_video_size: Optional[RecordVideoSize],
        record_video_fps: Optional[int],
        storage_state: Optional[Union[StorageState, str, Path]],
        base_url: Optional[str],
        strict_selectors: Optional[bool],
        service_workers: Optional[Literal["allow", "block"]],
        record_har_url_filter: Optional[Union[str, Pattern[str]]],
        record_har_mode: Optional[Literal["full", "minimal"]],
        record_har_content: Optional[Literal["attach", "embed", "omit"]],
        client_certificates: Optional[Sequence[ClientCertificate]],
    ) -> "Page":
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
            record_video_fps=record_video_fps,
            storage_state=storage_state,
            base_url=base_url,
            strict_selectors=strict_selectors,
            service_workers=service_workers,
            record_har_url_filter=record_har_url_filter,
            record_har_mode=record_har_mode,
            record_har_content=record_har_content,
            client_certificates=client_certificates,
        )
        page = await context.new_page()
        page._owned_context = context
        context._owner_page = page
        return page

    def is_connected(self) -> bool:
        return self._is_connected

    async def new_browser_cdp_session(self) -> CDPSession:
        return CDPSession.from_(
            (await self._channel.newBrowserCDPSession(timeout=NO_TIMEOUT))["session"]
        )

    async def start_tracing(
        self,
        page: Optional["Page"],
        path: Optional[Union[str, Path]],
        screenshots: Optional[bool],
        categories: Optional[Sequence[str]],
    ) -> None:
        self._path = path
        # Python: the options of the protocol; path is not one of them.
        await self._channel.startTracing(
            page=page._channel if page else None,
            screenshots=screenshots,
            categories=categories,
            timeout=NO_TIMEOUT,
        )

    async def stop_tracing(self) -> bytes:
        artifact = Artifact.from_(
            (await self._channel.stopTracing(timeout=NO_TIMEOUT))["artifact"]
        )
        buffer = await artifact.read_into_buffer()
        await artifact.delete()
        if self._path:
            await mkdir_if_needed(self._path)
            await write_file(self._path, buffer)
            self._path = None
        return buffer

    # Not ported: [Symbol.asyncDispose](). Python: the generated API is an async
    # context manager that calls close().

    async def close(self, reason: Optional[str]) -> None:
        self._close_reason = reason
        try:
            if self._should_close_connection_on_close:
                self._connection.close()
            else:
                await self._channel.close(reason=reason, timeout=NO_TIMEOUT)
            await self._closed_promise
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e

    def _did_close(self) -> None:
        self._is_connected = False
        self.emit(Events.Browser.Disconnected, self)

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<Browser type={self._browser_type} version={self.version}>"
