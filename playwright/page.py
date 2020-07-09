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
import base64
from playwright.accessibility import Accessibility
from playwright.connection import Channel, ChannelOwner, ConnectionScope, from_channel, from_nullable_channel
from playwright.console_message import ConsoleMessage
from playwright.dialog import Dialog
from playwright.download import Download
from playwright.element_handle import ElementHandle, ValuesToSelect
from playwright.file_chooser import FileChooser
from playwright.helper import locals_to_params
from playwright.input import Keyboard, Mouse
from playwright.js_handle import JSHandle
from playwright.frame import Frame
from playwright.helper import is_function_body, parse_error, serialize_error, Error, FilePayload, FrameMatch, FunctionWithSource, Optional, PendingWaitEvent, RouteHandler, RouteHandlerEntry, SelectOption, TimeoutSettings, URLMatch, URLMatcher
from playwright.network import Request, Response, Route
from playwright.worker import Worker
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict, List, Union, TYPE_CHECKING

if TYPE_CHECKING:
  from playwright.browser_context import BrowserContext

class Page(ChannelOwner):

  Events = SimpleNamespace(
    Close='close',
    Crash='crash',
    Console='console',
    Dialog='dialog',
    Download='download',
    FileChooser='filechooser',
    DOMContentLoaded='domcontentloaded',
    PageError='pageerror',
    Request='request',
    Response='response',
    RequestFailed='requestfailed',
    RequestFinished='requestfinished',
    FrameAttached='frameattached',
    FrameDetached='framedetached',
    FrameNavigated='framenavigated',
    Load='load',
    Popup='popup',
    Worker='worker',
  )

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)
    self.accessibility = Accessibility(self._channel)
    self.keyboard = Keyboard(self._channel)
    self.mouse = Mouse(self._channel)

    self._main_frame: Frame = from_channel(initializer['mainFrame'])
    self._main_frame._page = self
    self._frames = [self._main_frame]
    self._viewport_size = initializer['viewportSize']
    self._is_closed = False
    self._workers: List[Worker] = list()
    self._bindings: Dict[str, Any] = dict()
    self._pending_wait_for_events: List[PendingWaitEvent] = list()
    self._routes: List[RouteHandlerEntry] = list()
    self._owned_context: Optional['BrowserContext'] = None

    self._channel.on('bindingCall', lambda binding_call: self._on_binding(from_channel(binding_call)))
    self._channel.on('close', lambda _: self._on_close())
    self._channel.on('console', lambda message: self.emit(Page.Events.Console, from_channel(message)))
    self._channel.on('crash', lambda _: self._on_crash())
    self._channel.on('dialog', lambda dialog: self.emit(Page.Events.Dialog, from_channel(dialog)))
    self._channel.on('domcontentloaded', lambda _: self.emit(Page.Events.DOMContentLoaded))
    self._channel.on('download', lambda download: self.emit(Page.Events.Download, from_channel(download)))
    self._channel.on('fileChooser', lambda params: self.emit(Page.Events.FileChooser, FileChooser(self, from_channel(params['element']), params['isMultiple'])))
    self._channel.on('frameAttached', lambda frame: self._on_frame_attached(from_channel(frame)))
    self._channel.on('frameDetached', lambda frame: self._on_frame_detached(from_channel(frame)))
    self._channel.on('frameNavigated', lambda params: self._on_frame_navigated(from_channel(params['frame']), params['url'], params['name']))
    self._channel.on('load', lambda _: self.emit(Page.Events.Load))
    self._channel.on('pageError', lambda params: self.emit(Page.Events.PageError, parse_error(params['error'])))
    self._channel.on('popup', lambda popup: self.emit(Page.Events.Popup, from_channel(popup)))
    self._channel.on('request', lambda request: self.emit(Page.Events.Request, from_channel(request)))
    self._channel.on('requestFailed', lambda params: self._on_request_failed(from_channel(params['request']), params['failureText']))
    self._channel.on('requestFinished', lambda request: self.emit(Page.Events.RequestFinished, from_channel(request)))
    self._channel.on('response', lambda response: self.emit(Page.Events.Response, from_channel(response)))
    self._channel.on('route', lambda params: self._on_route(from_channel(params['route']), from_channel(params['request'])))
    self._channel.on('worker', lambda worker: self._on_worker(from_channel(worker)))

  def _set_browser_context(self, context: 'BrowserContext') -> None:
    self._browser_context = context
    self._timeout_settings = TimeoutSettings(context._timeout_settings)

  def _on_request_failed(self, request: Request, failure_text: str = None) -> None:
    request._failure_text = failure_text
    self.emit(Page.Events.RequestFailed,  request)

  def _on_frame_attached(self, frame: Frame) -> None:
    frame._page = self
    self._frames.append(frame)
    self.emit(Page.Events.FrameAttached, frame)

  def _on_frame_detached(self, frame: Frame) -> None:
    self._frames.remove(frame)
    frame._detached = True
    self.emit(Page.Events.FrameDetached, frame)

  def _on_frame_navigated(self, frame: Frame, url: str, name: str) -> None:
    frame._url = url
    frame._name = name
    self.emit(Page.Events.FrameNavigated, frame)

  def _on_route(self, route: Route, request: Request) -> None:
    for handler_entry in self._routes:
      if handler_entry.matcher.matches(request.url):
        handler_entry.handler(route, request)
        return
    self._browser_context._on_route(route, request)

  def _on_binding(self, binding_call: 'BindingCall') -> None:
    func = self._bindings.get(binding_call._initializer['name'])
    if func:
      binding_call.call(func)
    self._browser_context._on_binding(binding_call)

  def _on_worker(self, worker: Worker) -> None:
    self._workers.append(worker)
    worker._page = self
    self.emit(Page.Events.Worker, worker)

  def _on_close(self) -> None:
    self._is_closed = True
    self._browser_context._pages.remove(self)
    self._reject_pending_operations(False)
    self.emit(Page.Events.Close)

  def _on_crash(self) -> None:
    self._reject_pending_operations(True)
    self.emit(Page.Events.Crash)

  def _reject_pending_operations(self, is_crash: bool) -> None:
    for pending_event in self._pending_wait_for_events:
      if pending_event.event == Page.Events.Close and not is_crash:
        continue
      if pending_event.event == Page.Events.Crash and is_crash:
        continue
      pending_event.future.set_exception(Error('Page crashed' if is_crash else 'Page closed'))
    self._pending_wait_for_events.clear()

  @property
  def context(self) -> 'BrowserContext':
    return self._browser_context

  async def opener(self) -> Optional['Page']:
    return from_nullable_channel(await self._channel.send('opener'))

  @property
  def mainFrame(self) -> Frame:
    return self._main_frame

  def frame(self, name: str = None, url: FrameMatch = None) -> Optional[Frame]:
    matcher = URLMatcher(url) if url else None
    for frame in self._frames:
      if name and frame.name == name:
        return frame
      if url and matcher.matches(frame.url):
        return frame
    return None

  @property
  def frames(self) -> List[Frame]:
    return self._frames.copy()

  def setDefaultNavigationTimeout(self, timeout: int) -> None:
    self._channel.send('setDefaultNavigationTimeoutNoReply', dict(timeout=timeout))

  def setDefaultTimeout(self, timeout: int) -> None:
    self._timeout_settings.set_default_timeout(timeout)
    self._channel.send('setDefaultTimeoutNoReply', dict(timeout=timeout))

  async def querySelector(self, selector: str) -> Optional[ElementHandle]:
    return await self._main_frame.querySelector(selector)

  async def querySelectorAll(self, selector: str) -> List[ElementHandle]:
    return await self._main_frame.querySelectorAll(selector)

  async def waitForSelector(self,
      selector: str,
      timeout: int = None,
      state: str = None, # Literal['attached', 'detached', 'visible', 'hidden'] = None
    ) -> Optional[ElementHandle]:
    return await self._main_frame.waitForSelector(**locals_to_params(locals()))

  async def dispatchEvent(self,
      selector: str,
      type: str,
      eventInit: Dict = None,
      timeout: int = None) -> None:
    return await self._main_frame.dispatchEvent(**locals_to_params(locals()))

  async def evaluate(self, expression: str, arg: Any = None, force_expr: bool = False) -> Any:
    return await self._main_frame.evaluate(expression, arg, force_expr=force_expr)

  async def evaluateHandle(self, expression: str, arg: Any = None, force_expr: bool = False) -> JSHandle:
    return await self._main_frame.evaluateHandle(expression, arg, force_expr=force_expr)

  async def evalOnSelector(self, selector: str, expression: str, arg: Any = None, force_expr: bool = False) -> Any:
    return await self._main_frame.evalOnSelector(selector, expression, arg, force_expr=force_expr)

  async def evalOnSelectorAll(self, selector: str, expression: str, arg: Any = None, force_expr: bool = False) -> Any:
    return await self._main_frame.evalOnSelectorAll(selector, expression, arg, force_expr=force_expr)

  async def addScriptTag(self,
      url: str = None,
      path: str = None,
      content: str = None,
      type: str = None) -> ElementHandle:
    return await self._main_frame.addScriptTag(**locals_to_params(locals()))

  async def addStyleTag(self,
      url: str = None,
      path: str = None,
      content: str = None) -> ElementHandle:
    return await self._main_frame.addStyleTag(**locals_to_params(locals()))

  async def exposeFunction(self, name: str, binding: Callable[..., Any]) -> None:
    await self.exposeBinding(name, lambda source, *args: binding(*args))

  async def exposeBinding(self, name: str, binding: FunctionWithSource) -> None:
    if name in self._bindings:
      raise Error(f'Function "{name}" has been already registered')
    if name in self._browser_context._bindings:
      raise Error(f'Function "{name}" has been already registered in the browser context')
    self._bindings[name] = binding
    await self._channel.send('exposeBinding', dict(name=name))

  async def setExtraHTTPHeaders(self, headers: Dict) -> None:
    await self._channel.send('setExtraHTTPHeaders', dict(headers=headers))

  @property
  def url(self) -> str:
    return self._main_frame.url

  async def content(self) -> str:
    return await self._main_frame.content()

  async def setContent(self,
      html: str, timeout: int = None,
      waitUntil: str = None, # Literal['load', 'domcontentloaded', 'networkidle'] = None
    ) -> None:
    return await self._main_frame.setContent(**locals_to_params(locals()))

  async def goto(self,
      url: str,
      timeout: int = None,
      waitUntil: str = None, # Literal['load', 'domcontentloaded', 'networkidle'] = None,
      referer: str = None) -> Optional[Response]:
    return await self._main_frame.goto(**locals_to_params(locals()))

  async def reload(self,
      timeout: int = None,
      waitUntil: str = None # Literal['load', 'domcontentloaded', 'networkidle'] = None
    ) -> Optional[Response]:
    return from_nullable_channel(await self._channel.send('reload', locals_to_params(locals())))

  async def waitForLoadState(self,
      state: str = 'load',
      timeout: int = None) -> None:
    return await self._main_frame.waitForLoadState(**locals_to_params(locals()))

  async def waitForNavigation(self,
      timeout: int = None,
      waitUntil: str = None, # Literal['load', 'domcontentloaded', 'networkidle'] = None,
      url: str = None # TODO: add url, callback
    ) -> Optional[Response]:
    return await self._main_frame.waitForNavigation(locals_to_params(locals()))

  async def waitForRequest(self, urlOrPredicate: Union[str, Callable[[Request], bool]]) -> Optional[Request]:
    matcher = URLMatcher(urlOrPredicate) if isinstance(urlOrPredicate, str) else None
    def predicate(request: Request):
      if matcher:
        return matcher.matches(request.url())
      return urlOrPredicate(request)
    params = locals_to_params(locals())
    params['predicate'] = predicate
    return self.waitForEvent(Page.Events.Request, **params)

  async def waitForResponse(self, urlOrPredicate: Union[str, Callable[[Request], bool]]) -> Optional[Response]:
    matcher = URLMatcher(urlOrPredicate) if isinstance(urlOrPredicate, str) else None
    def predicate(request: Request):
      if matcher:
        return matcher.matches(request.url())
      return urlOrPredicate(request)
    params = locals_to_params(locals())
    params['predicate'] = predicate
    return await self.waitForEvent(Page.Events.Response, **params)

  async def waitForEvent(self, event: str) -> Any:
    # TODO: support timeout
    future = self._scope._loop.create_future()
    self.once(event, lambda e: future.set_result(e))
    pending_event = PendingWaitEvent(event, future)
    self._pending_wait_for_events.append(pending_event)
    result = await future
    self._pending_wait_for_events.remove(pending_event)
    return result

  async def goBack(self,
      timeout: int = None,
      waitUntil: str = None # Literal['load', 'domcontentloaded', 'networkidle']
    ) -> Optional[Response]:
    return from_nullable_channel(await self._channel.send('goBack', locals_to_params(locals())))

  async def goForward(self,
      timeout: int = None,
      waitUntil: str = None # Literal['load', 'domcontentloaded', 'networkidle'] = None
    ) -> Optional[Response]:
    return from_nullable_channel(await self._channel.send('goForward', locals_to_params(locals())))

  async def emulateMedia(self,
      media: str = None, # Literal['screen', 'print']
      colorScheme: str = None # Literal['dark', 'light', 'no-preference']
    ) -> None:
    await self._channel.send('emulateMedia', locals_to_params(locals()))

  async def setViewportSize(self, viewport_size: Dict) -> None:
    self._viewport_size = viewport_size
    await self._channel.send('setViewportSize', dict(viewportSize=viewport_size))

  def viewportSize(self) -> Optional[Dict]:
    return self._viewport_size

  async def addInitScript(self, source: str = None, path: str = None) -> None:
    if path:
      with open(path, 'r') as file:
        source = file.read()
    if not isinstance(source, str):
      raise Error('Either path or source parameter must be specified')
    await self._channel.send('addInitScript', dict(source=source))

  async def route(self, match: URLMatch, handler: RouteHandler) -> None:
    self._routes.append(RouteHandlerEntry(URLMatcher(match), handler))
    if len(self._routes) == 1:
      await self._channel.send('setNetworkInterceptionEnabled', dict(enabled=True))

  async def unroute(self, match: URLMatch, handler: Optional[RouteHandler]) -> None:
    self._routes = filter(lambda r: r.matcher.match != match or (handler and r.handler != handler), self._routes)
    if len(self._routes) == 0:
      await self._channel.send('setNetworkInterceptionEnabled', dict(enabled=False))

  async def screenshot(self,
      timeout: int = None,
      type: str = None, # Literal['png', 'jpeg'] = None,
      path: str = None,
      quality: int = None,
      omitBackground: bool = None,
      fullPage: bool = None,
      clip: Dict = None) -> bytes:
    binary = await self._channel.send('screenshot', locals_to_params(locals()))
    return base64.b64decode(binary)

  async def title(self) -> str:
    return await self._main_frame.title()

  async def close(self, runBeforeUnload: bool = None) -> None:
    await self._channel.send('close', locals_to_params(locals()))
    if self._owned_context:
      await self._owned_context.close()

  def isClosed(self) -> bool:
    return self._is_closed

  async def click(self,
      selector: str,
      modifiers: List[str] = None, # Literal['Alt', 'Control', 'Meta', 'Shift']] = None,
      position: Dict = None,
      delay: int = None,
      button: str = None, # Literal['left', 'right', 'middle'] = None,
      clickCount: int = None,
      timeout: int = None,
      force: bool = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.click(**locals_to_params(locals()))

  async def dblclick(self,
      selector: str,
      modifiers: List[str] = None, # Literal['Alt', 'Control', 'Meta', 'Shift']] = None,
      position: Dict = None,
      delay: int = None,
      button: str = None, # Literal['left', 'right', 'middle'] = None,
      timeout: int = None,
      force: bool = None) -> None:
    return await self._main_frame.dblclick(**locals_to_params(locals()))

  async def fill(self,
      selector: str,
      value: str,
      timeout: int = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.fill(**locals_to_params(locals()))

  async def focus(self,
      selector: str,
      timeout: int = None) -> None:
    return await self._main_frame.focus(**locals_to_params(locals()))

  async def textContent(self,
      selector: str,
      timeout: int = None) -> str:
    return await self._main_frame.textContent(**locals_to_params(locals()))

  async def innerText(self,
      selector: str,
      timeout: int = None) -> str:
    return await self._main_frame.innerText(**locals_to_params(locals()))

  async def innerHTML(self,
      selector: str,
      timeout: int = None) -> str:
    return await self._main_frame.innerHTML(**locals_to_params(locals()))

  async def getAttribute(self,
      selector: str,
      name: str,
      timeout: int = None) -> str:
    return await self._main_frame.getAttribute(**locals_to_params(locals()))

  async def hover(self,
      selector: str,
      modifiers: List[str] = None, # Literal['Alt', 'Control', 'Meta', 'Shift']] = None,
      position: Dict = None,
      timeout: int = None,
      force: bool = None) -> None:
    return await self._main_frame.hover(**locals_to_params(locals()))

  async def selectOption(self,
      selector: str,
      values: ValuesToSelect,
      timeout: int = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.selectOption(**locals_to_params(locals()))

  async def setInputFiles(self,
      selector: str,
      files: Union[str, FilePayload, List[str], List[FilePayload]],
      timeout: int = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.setInputFiles(**locals_to_params(locals()))

  async def type(self,
      selector: str,
      text: str,
      delay: int = None,
      timeout: int = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.type(**locals_to_params(locals()))

  async def press(self,
      selector: str,
      key: str,
      delay: int = None,
      timeout: int = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.press(**locals_to_params(locals()))

  async def check(self,
      selector: str,
      timeout: int = None,
      force: bool = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.check(**locals_to_params(locals()))

  async def uncheck(self,
      selector: str,
      timeout: int = None,
      force: bool = None,
      noWaitAfter: bool = None) -> None:
    return await self._main_frame.uncheck(**locals_to_params(locals()))

  async def waitForTimeout(self, timeout: int) -> Awaitable[None]:
    return self._main_frame.waitForTimeout(timeout)

  async def waitForFunction(self,
      expression: str,
      arg: Any = None,
      force_expr: bool = False,
      timeout: int = None,
      polling: Union[int, str] = None # Union[int, Literal["raf"]]
      ) -> JSHandle:
    if not is_function_body(expression):
      force_expr = True
    return await self._main_frame.waitForFunction(**locals_to_params(locals()))

  def workers(self) -> List[Worker]:
    return self._workers.copy()

  # on(event: str | symbol, listener: Listener): self {
  #   if (event === Page.Events.FileChooser) {
  #     if (!self.listenerCount(event))
  #       self._channel.setFileChooserInterceptedNoReply({ intercepted: True });
  #   }
  #   super.on(event, listener);
  #   return self;
  # }

  # removeListener(event: str | symbol, listener: Listener): self {
  #   super.removeListener(event, listener);
  #   if (event === Page.Events.FileChooser && !self.listenerCount(event))
  #     self._channel.setFileChooserInterceptedNoReply({ intercepted: False });
  #   return self;
  # }

  async def pdf(self,
      scale: int = None,
      displayHeaderFooter: bool = None,
      headerTemplate: str = None,
      footerTemplate: str = None,
      printBackground: bool = None,
      landscape: bool = None,
      pageRanges: str = None,
      format: str = None,
      width: Union[str, float] = None,
      height: Union[str, float] = None,
      preferCSSPageSize: bool = None,
      margin: Dict = None,
      path: str = None) -> bytes:
    binary = await self._channel.send('pdf', locals_to_params(locals()))
    return base64.b64decode(binary)

class BindingCall(ChannelOwner):

  def __init__(self, scope: ConnectionScope, guid: str, initializer: Dict) -> None:
    super().__init__(scope, guid, initializer)

  def call(self, func: FunctionWithSource) -> None:
    try:
      frame = from_channel(self._initializer['frame'])
      source = dict(context=frame._page.context, page=frame._page, frame=frame)
      result = func(source, *self._initializer['args'])
      asyncio.ensure_future(self._channel.send('resolve', dict(result=result)))
    except BaseException as e:
      asyncio.ensure_future(self._channel.send('reject', dict(error=serialize_error(e))))
