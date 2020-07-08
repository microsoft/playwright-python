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
from playwright.connection import Channel, ChannelOwner, ConnectionScope, from_channel, from_nullable_channel
from playwright.helper import Cookie, Error, FunctionWithSource, PendingWaitEvent, RouteHandler, RouteHandlerEntry, TimeoutSettings, URLMatch, URLMatcher
from playwright.network import Request, Response, Route
from playwright.page import BindingCall, Page
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
  from playwright.browser import Browser

class BrowserContext(ChannelOwner):

  Events = SimpleNamespace(
    Close='close',
    Page='page',
  )

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer, True)
    self._pages: List[Page] = list()
    self._routes: List[RouteHandlerEntry] = list()
    self._bindings: Dict[str, Any] = dict()
    self._pending_wait_for_events: List[PendingWaitEvent] = list()
    self._timeout_settings = TimeoutSettings(None)
    self._browser: Optional['Browser'] = None
    self._owner_page: Optional[Page] = None

    for channel in initializer['pages']:
      page = from_channel(channel)
      self._pages.append(page)
      page._set_browser_context(self)
    self._channel.on('bindingCall', lambda binding_call: self._on_binding(from_channel(binding_call)))
    self._channel.on('close', lambda _: self._on_close())
    self._channel.on('page', lambda page: self._on_page(from_channel(page)))
    self._channel.on('route', lambda event: self._on_route(from_channel(event.get('route')), from_channel(event.get('request'))))

  def _on_page(self, page: Page) -> None:
    page._set_browser_context(self)
    self._pages.append(page)
    self.emit(BrowserContext.Events.Page, page)

  def _on_route(self, route: Route, request: Request) -> None:
    for handler_entry in self._routes:
      if handler_entry.matcher.matches(request.url()):
        handler_entry.handler(route, request)
        return
    asyncio.ensure_future(route.continue_())

  def _on_binding(self, binding_call: BindingCall) -> None:
    func = self._bindings.get(binding_call._initializer['name'])
    if func == None:
      return
    binding_call.call(func)

  def setDefaultNavigationTimeout(self, timeout: int) -> None:
    self._channel.send('setDefaultNavigationTimeoutNoReply', dict(timeout=timeout))

  def setDefaultTimeout(self, timeout: int) -> None:
    self._timeout_settings.set_default_timeout(timeout)
    self._channel.send('setDefaultTimeoutNoReply', dict(timeout=timeout))

  @property
  def pages(self) -> List[Page]:
    return self._pages.copy()

  async def newPage(self) -> Page:
    if self._owner_page:
      raise Error('Please use browser.newContext()')
    return from_channel(await self._channel.send('newPage'))

  async def cookies(self, urls: Union[str, List[str]]) -> List[Cookie]:
    if urls == None:
      urls = list()
    return await self._channel.send('cookies', dict(urls=urls))

  async def addCookies(self, cookies: List[Cookie]) -> None:
    await self._channel.send('addCookies', dict(cookies=cookies))

  async def clearCookies(self) -> None:
    await self._channel.send('clearCookies')

  async def grantPermissions(self, permissions: List[str], origin: str = None) -> None:
    await self._channel.send('grantPermissions', dict(permissions=permissions, origin=origin))

  async def clearPermissions(self) -> None:
    await self._channel.send('clearPermissions')

  async def setGeolocation(self, geolocation: Optional[Dict]) -> None:
    await self._channel.send('setGeolocation', dict(geolocation=geolocation))

  async def setExtraHTTPHeaders(self, headers: Dict) -> None:
    await self._channel.send('setExtraHTTPHeaders', dict(headers=headers))

  async def setOffline(self, offline: bool) -> None:
    await self._channel.send('setOffline', dict(offline=offline))

  async def addInitScript(self, source: str = None, path: str = None) -> None:
    if path:
      with open(path, 'r') as file:
        source = file.read()
    if not isinstance(source, str):
      raise Error('Either path or source parameter must be specified')
    await self._channel.send('addInitScript', dict(source=source))

  async def exposeBinding(self, name: str, binding: FunctionWithSource) -> None:
    for page in self._pages:
      if name in page._bindings:
        raise Error(f'Function "{name}" has been already registered in one of the pages')
    if name in self._bindings:
      raise Error(f'Function "{name}" has been already registered')
    self._bindings[name] = binding
    await self._channel.send('exposeBinding', dict(name=name))

  async def exposeFunction(self, name: str, binding: Callable[..., Any]) -> None:
    await self.exposeBinding(name, lambda source, *args: binding(*args))

  async def route(self, match: URLMatch, handler: RouteHandler) -> None:
    self._routes.append(RouteHandlerEntry(URLMatcher(match), handler))
    if len(self._routes) == 1:
      await self._channel.send('setNetworkInterceptionEnabled', dict(enabled=True))

  async def unroute(self, match: URLMatch, handler: Optional[RouteHandler]) -> None:
    self._routes = filter(lambda r: r.matcher.match != match or (handler and r.handler != handler), self._routes)
    if len(self._routes) == 0:
      await self._channel.send('setNetworkInterceptionEnabled', dict(enabled=False))

  async def waitForEvent(self, event: str) -> None:
    # TODO: implement timeout race
    future = self._scope._loop.create_future()
    self.once(event, lambda e: future.set_result(e))
    pending_event = PendingWaitEvent(event, future)
    self._pending_wait_for_events.append(pending_event)
    result = await future
    self._pending_wait_for_events.remove(pending_event)
    return result

  def _on_close(self):
    if self._browser:
      self._browser._contexts.remove(self)

    for pending_event in self._pending_wait_for_events:
      if pending_event.event == BrowserContext.Events.Close:
        continue
      pending_event.future.set_exception(Error('Context closed'))

    self._pending_wait_for_events.clear()
    self.emit(BrowserContext.Events.Close)
    self._scope.dispose()

  async def close(self) -> None:
    await self._channel.send('close')
