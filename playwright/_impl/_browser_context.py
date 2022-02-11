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
import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Union, cast

from playwright._impl._api_structures import (
    Cookie,
    Geolocation,
    SetCookieParam,
    StorageState,
)
from playwright._impl._api_types import Error
from playwright._impl._artifact import Artifact
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._fetch import APIRequestContext
from playwright._impl._frame import Frame
from playwright._impl._helper import (
    RouteHandler,
    RouteHandlerCallback,
    TimeoutSettings,
    URLMatch,
    URLMatcher,
    async_readfile,
    async_writefile,
    is_safe_close_error,
    locals_to_params,
    to_impl,
)
from playwright._impl._network import Request, Response, Route, serialize_headers
from playwright._impl._page import BindingCall, Page, Worker
from playwright._impl._tracing import Tracing
from playwright._impl._wait_helper import WaitHelper

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser import Browser


class BrowserContext(ChannelOwner):

    Events = SimpleNamespace(
        BackgroundPage="backgroundpage",
        Close="close",
        Page="page",
        ServiceWorker="serviceworker",
        Request="request",
        Response="response",
        RequestFailed="requestfailed",
        RequestFinished="requestfinished",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._pages: List[Page] = []
        self._routes: List[RouteHandler] = []
        self._bindings: Dict[str, Any] = {}
        self._timeout_settings = TimeoutSettings(None)
        self._browser: Optional["Browser"] = None
        self._owner_page: Optional[Page] = None
        self._options: Dict[str, Any] = {}
        self._background_pages: Set[Page] = set()
        self._service_workers: Set[Worker] = set()
        self._tracing = cast(Tracing, from_channel(initializer["tracing"]))
        self._request: APIRequestContext = from_channel(
            initializer["APIRequestContext"]
        )
        self._channel.on(
            "bindingCall",
            lambda params: self._on_binding(from_channel(params["binding"])),
        )
        self._channel.on("close", lambda _: self._on_close())
        self._channel.on(
            "page", lambda params: self._on_page(from_channel(params["page"]))
        )
        self._channel.on(
            "route",
            lambda params: self._on_route(
                from_channel(params.get("route")), from_channel(params.get("request"))
            ),
        )

        self._channel.on(
            "backgroundPage",
            lambda params: self._on_background_page(from_channel(params["page"])),
        )

        self._channel.on(
            "serviceWorker",
            lambda params: self._on_service_worker(from_channel(params["worker"])),
        )
        self._channel.on(
            "request",
            lambda params: self._on_request(
                from_channel(params["request"]),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "response",
            lambda params: self._on_response(
                from_channel(params["response"]),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "requestFailed",
            lambda params: self._on_request_failed(
                from_channel(params["request"]),
                params["responseEndTiming"],
                params.get("failureText"),
                from_nullable_channel(params.get("page")),
            ),
        )
        self._channel.on(
            "requestFinished",
            lambda params: self._on_request_finished(
                from_channel(params["request"]),
                from_nullable_channel(params.get("response")),
                params["responseEndTiming"],
                from_nullable_channel(params.get("page")),
            ),
        )
        self._closed_future: asyncio.Future = asyncio.Future()
        self.once(
            self.Events.Close, lambda context: self._closed_future.set_result(True)
        )

    def __repr__(self) -> str:
        return f"<BrowserContext browser={self.browser}>"

    def _on_page(self, page: Page) -> None:
        self._pages.append(page)
        self.emit(BrowserContext.Events.Page, page)
        if page._opener and not page._opener.is_closed():
            page._opener.emit(Page.Events.Popup, page)

    def _on_route(self, route: Route, request: Request) -> None:
        for handler_entry in self._routes:
            if handler_entry.matches(request.url):
                try:
                    handler_entry.handle(route, request)
                finally:
                    if not handler_entry.is_active:
                        self._routes.remove(handler_entry)
                        if not len(self._routes) == 0:
                            asyncio.create_task(self._disable_interception())
                break
        route._internal_continue()

    def _on_binding(self, binding_call: BindingCall) -> None:
        func = self._bindings.get(binding_call._initializer["name"])
        if func is None:
            return
        asyncio.create_task(binding_call.call(func))

    def set_default_navigation_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_navigation_timeout(timeout)
        self._channel.send_no_reply(
            "setDefaultNavigationTimeoutNoReply", dict(timeout=timeout)
        )

    def set_default_timeout(self, timeout: float) -> None:
        self._timeout_settings.set_timeout(timeout)
        self._channel.send_no_reply("setDefaultTimeoutNoReply", dict(timeout=timeout))

    @property
    def pages(self) -> List[Page]:
        return self._pages.copy()

    @property
    def browser(self) -> Optional["Browser"]:
        return self._browser

    async def new_page(self) -> Page:
        if self._owner_page:
            raise Error("Please use browser.new_context()")
        return from_channel(await self._channel.send("newPage"))

    async def cookies(self, urls: Union[str, List[str]] = None) -> List[Cookie]:
        if urls is None:
            urls = []
        if not isinstance(urls, list):
            urls = [urls]
        return await self._channel.send("cookies", dict(urls=urls))

    async def add_cookies(self, cookies: List[SetCookieParam]) -> None:
        await self._channel.send("addCookies", dict(cookies=cookies))

    async def clear_cookies(self) -> None:
        await self._channel.send("clearCookies")

    async def grant_permissions(
        self, permissions: List[str], origin: str = None
    ) -> None:
        await self._channel.send("grantPermissions", locals_to_params(locals()))

    async def clear_permissions(self) -> None:
        await self._channel.send("clearPermissions")

    async def set_geolocation(self, geolocation: Geolocation = None) -> None:
        await self._channel.send("setGeolocation", locals_to_params(locals()))

    async def set_extra_http_headers(self, headers: Dict[str, str]) -> None:
        await self._channel.send(
            "setExtraHTTPHeaders", dict(headers=serialize_headers(headers))
        )

    async def set_offline(self, offline: bool) -> None:
        await self._channel.send("setOffline", dict(offline=offline))

    async def add_init_script(
        self, script: str = None, path: Union[str, Path] = None
    ) -> None:
        if path:
            script = (await async_readfile(path)).decode()
        if not isinstance(script, str):
            raise Error("Either path or script parameter must be specified")
        await self._channel.send("addInitScript", dict(source=script))

    async def expose_binding(
        self, name: str, callback: Callable, handle: bool = None
    ) -> None:
        for page in self._pages:
            if name in page._bindings:
                raise Error(
                    f'Function "{name}" has been already registered in one of the pages'
                )
        if name in self._bindings:
            raise Error(f'Function "{name}" has been already registered')
        self._bindings[name] = callback
        await self._channel.send(
            "exposeBinding", dict(name=name, needsHandle=handle or False)
        )

    async def expose_function(self, name: str, callback: Callable) -> None:
        await self.expose_binding(name, lambda source, *args: callback(*args))

    async def route(
        self, url: URLMatch, handler: RouteHandlerCallback, times: int = None
    ) -> None:
        self._routes.insert(
            0,
            RouteHandler(URLMatcher(self._options.get("baseURL"), url), handler, times),
        )
        if len(self._routes) == 1:
            await self._channel.send(
                "setNetworkInterceptionEnabled", dict(enabled=True)
            )

    async def unroute(
        self, url: URLMatch, handler: Optional[RouteHandlerCallback] = None
    ) -> None:
        self._routes = list(
            filter(
                lambda r: r.matcher.match != url or (handler and r.handler != handler),
                self._routes,
            )
        )
        if len(self._routes) == 0:
            await self._disable_interception()

    async def _disable_interception(self) -> None:
        await self._channel.send("setNetworkInterceptionEnabled", dict(enabled=False))

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = self._timeout_settings.timeout()
        wait_helper = WaitHelper(self, f"browser_context.expect_event({event})")
        wait_helper.reject_on_timeout(
            timeout, f'Timeout {timeout}ms exceeded while waiting for event "{event}"'
        )
        if event != BrowserContext.Events.Close:
            wait_helper.reject_on_event(
                self, BrowserContext.Events.Close, Error("Context closed")
            )
        wait_helper.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(wait_helper.result())

    def _on_close(self) -> None:
        if self._browser:
            self._browser._contexts.remove(self)

        self.emit(BrowserContext.Events.Close, self)

    async def close(self) -> None:
        try:
            if self._options.get("recordHar"):
                har = cast(
                    Artifact, from_channel(await self._channel.send("harExport"))
                )
                await har.save_as(
                    cast(Dict[str, str], self._options["recordHar"])["path"]
                )
                await har.delete()
            await self._channel.send("close")
            await self._closed_future
        except Exception as e:
            if not is_safe_close_error(e):
                raise e

    async def _pause(self) -> None:
        await self._channel.send("pause")

    async def storage_state(self, path: Union[str, Path] = None) -> StorageState:
        result = await self._channel.send_return_as_dict("storageState")
        if path:
            await async_writefile(path, json.dumps(result))
        return result

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    def expect_page(
        self,
        predicate: Callable[[Page], bool] = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Page]:
        return self.expect_event(BrowserContext.Events.Page, predicate, timeout)

    def _on_background_page(self, page: Page) -> None:
        self._background_pages.add(page)
        self.emit(BrowserContext.Events.BackgroundPage, page)

    def _on_service_worker(self, worker: Worker) -> None:
        worker._context = self
        self._service_workers.add(worker)
        self.emit(BrowserContext.Events.ServiceWorker, worker)

    def _on_request_failed(
        self,
        request: Request,
        response_end_timing: float,
        failure_text: Optional[str],
        page: Optional[Page],
    ) -> None:
        request._failure_text = failure_text
        if request._timing:
            request._timing["responseEnd"] = response_end_timing
        self.emit(BrowserContext.Events.RequestFailed, request)
        if page:
            page.emit(Page.Events.RequestFailed, request)

    def _on_request_finished(
        self,
        request: Request,
        response: Optional[Response],
        response_end_timing: float,
        page: Optional[Page],
    ) -> None:
        if request._timing:
            request._timing["responseEnd"] = response_end_timing
        self.emit(BrowserContext.Events.RequestFinished, request)
        if page:
            page.emit(Page.Events.RequestFinished, request)
        if response:
            response._finished_future.set_result(True)

    def _on_request(self, request: Request, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Request, request)
        if page:
            page.emit(Page.Events.Request, request)

    def _on_response(self, response: Response, page: Optional[Page]) -> None:
        self.emit(BrowserContext.Events.Response, response)
        if page:
            page.emit(Page.Events.Response, response)

    @property
    def background_pages(self) -> List[Page]:
        return list(self._background_pages)

    @property
    def service_workers(self) -> List[Worker]:
        return list(self._service_workers)

    async def new_cdp_session(self, page: Union[Page, Frame]) -> CDPSession:
        page = to_impl(page)
        params = {}
        if isinstance(page, Page):
            params["page"] = page._channel
        elif isinstance(page, Frame):
            params["frame"] = page._channel
        else:
            raise Error("page: expected Page or Frame")
        return from_channel(await self._channel.send("newCDPSession", params))

    @property
    def tracing(self) -> Tracing:
        return self._tracing

    @property
    def request(self) -> "APIRequestContext":
        return self._request
