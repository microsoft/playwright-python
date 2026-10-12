/**
 * Copyright (c) Microsoft Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// @ts-check

// Facts about the Python API that the upstream docs (docs/src/api) do not
// contain. The generator applies these on top of the docs.
//
// Policy: the shipped Python API is the reference. Each entry records one place
// where Python differs from the docs. The preferred fix is a docs change
// upstream, after which the generator reports the entry as unused and it must
// be removed. Every entry needs a one-line reason above it.
//
// Keys use docs names: `Class.member` or `Class.member.arg`, where `member`
// and `arg` are the names in the docs (camelCase), not the Python aliases.

module.exports = {
  // Classes that the docs mark for other languages only, but that Python has.
  extraClasses: [
    // Python returns Disposable objects from route(), add_init_script() and others.
    'Disposable',
  ],

  // Classes in the Python view of the docs that are written by hand.
  handWrittenClasses: [
    // playwright/_impl/_errors.py
    'Error',
    'TimeoutError',
    // playwright/_impl/_form_data.py
    'FormData',
  ],

  // Classes that support `async with` / `with` and call close() on exit.
  contextManagerClasses: ['Page', 'BrowserContext', 'Browser', 'Disposable'],

  // Classes whose methods hide themselves from pytest tracebacks.
  tracebackHideClasses: ['PageAssertions', 'LocatorAssertions', 'APIResponseAssertions'],

  // Members that Python has but the docs do not describe. They get no docstring.
  extraMembers: {
    // Python-specific adapter for context manager support.
    'Disposable': [
      { kind: 'method', name: 'close', async: true, args: [], returns: 'void' },
    ],
    // playwright["chromium"] picks a browser type by name.
    'Playwright': [
      { kind: 'method', name: '__getitem__', async: false, args: [{ name: 'value', type: 'string' }], returns: 'BrowserType' },
    ],
  },

  // Options that Python has but the docs do not describe. They get no docstring.
  extraOptions: {
    // Hidden: lets new_context(**playwright.devices["..."]) accept the device's browser type.
    'Browser.newContext': [{ name: 'defaultBrowserType', type: 'string' }],
    // Hidden: lets new_page(**playwright.devices["..."]) accept the device's browser type.
    'Browser.newPage': [{ name: 'defaultBrowserType', type: 'string' }],
  },

  // Arguments that the docs describe but Python does not have.
  skipArgs: {
    // Deprecated and ignored; Python never added it to Frame (Page and Locator have it).
    'Frame.isHidden.timeout': true,
    // Deprecated and ignored; Python never added it to Frame (Page and Locator have it).
    'Frame.isVisible.timeout': true,
  },

  // Arguments whose Python name differs from the docs.
  argNames: {
    // The docs header says `name`, the type line says `description`; Python shipped `name`.
    'LocatorAssertions.NotToHaveAccessibleDescription.name': 'name',
  },

  // Python types that differ from the docs. Keys are argument places
  // (`Class.member.arg`) or member places (`Class.member`, for the return
  // type). Values are docs type expressions, or functions that build a docs
  // Type when the expression parser cannot. In an expression, a function type
  // with a return type must come last in a union: the parser reads everything
  // after `:` as the return type.
  typeOverrides: {
    // One vs two arguments in the callback, Python explicitly unions.
    'BrowserContext.route.handler': '[function]([Route])|[function]([Route], [Request])',
    // One vs two arguments in the callback, Python explicitly unions.
    'BrowserContext.unroute.handler': '[function]([Route])|[function]([Route], [Request])',
    // One vs two arguments in the callback, Python explicitly unions.
    'Page.route.handler': '[function]([Route])|[function]([Route], [Request])',
    // One vs two arguments in the callback, Python explicitly unions.
    'Page.unroute.handler': '[function]([Route])|[function]([Route], [Request])',
    // Zero or one argument in the callback, Python explicitly unions.
    'Page.addLocatorHandler.handler': '[function]([Locator])|[function]():[any]',
    // Python passes a plain dict; the docs type is EvaluationArgument.
    '*.dispatchEvent.eventInit': '[Object]',
    // Python returns None; the docs say it returns a Disposable.
    'Locator.highlight': 'void',
    // Python returns None; the docs say `null|string` but also "returns always `null`".
    'Response.finished': 'void',
    // Binary messages arrive as bytes.
    'WebSocketRoute.onMessage.handler': '[function]([string]|[Buffer]):[any]',
    // Both close() arguments may be missing. The docs parser drops the second
    // argument of a function type when the first one is a union, so the type is
    // built by hand.
    'WebSocketRoute.onClose.handler': ({ parse }) => {
      const type = parse('[function]([int]|[null]):[any]');
      type.args.push(parse('[string]|[null]'));
      return type;
    },
    // The async API also accepts an `async def` predicate.
    'Page.waitForRequest.urlOrPredicate': '[string]|[RegExp]|[function]([Request]):[boolean]|[Promise]<[boolean]>',
    // The async API also accepts an `async def` predicate.
    'Page.waitForResponse.urlOrPredicate': '[string]|[RegExp]|[function]([Response]):[boolean]|[Promise]<[boolean]>',
  },

  // Methods whose positional parameters differ from the docs. By default every
  // `### param` is positional (in docs order) and every `### option` is
  // keyword-only. An entry lists the positional parameters, in order; every
  // other parameter becomes keyword-only. Options named `predicate` are always
  // positional (see `positionalOptions` below).
  positional: {
    // select_option(value, *, index, label, element).
    'ElementHandle.selectOption': ['value'],
    // select_option(selector, value, *, index, label, element).
    'Frame.selectOption': ['selector', 'value'],
    // select_option(value, *, index, label, element).
    'Locator.selectOption': ['value'],
    // select_option(selector, value, *, index, label, element).
    'Page.selectOption': ['selector', 'value'],
    // add_init_script(script, *, path).
    'BrowserContext.addInitScript': ['script'],
    // add_init_script(script, *, path).
    'Page.addInitScript': ['script'],
    // wait_for_function(expression, *, arg).
    'Frame.waitForFunction': ['expression'],
    // wait_for_function(expression, *, arg).
    'Locator.waitForFunction': ['expression'],
    // wait_for_function(expression, *, arg).
    'Page.waitForFunction': ['expression'],
    // start_tracing(*, page).
    'Browser.startTracing': [],
    // frame(name, *, url).
    'Page.frame': ['name'],
  },

  // Options that are positional parameters in Python, in every method.
  positionalOptions: [
    // expect_*(predicate) and wait_for_event(event, predicate).
    'predicate',
  ],

  // Struct (TypedDict) names. The docs name a struct with `* alias:`; these
  // entries map a docs alias to the Python name, when they differ.
  structRenames: {
    // Python name.
    BindResult: 'BrowserBindResult',
    // Python name.
    BoundingBox: 'FloatRect',
    // Python name.
    HttpHeader: 'NameValue',
    // Python name.
    Location: 'DebuggerLocation',
    // Python name.
    Proxy: 'ProxySettings',
    // Python name.
    ScreenSize: 'ViewportSize',
    // Python name.
    WebStorageItem: 'NameValue',
  },

  // Struct names for places where the docs give no alias, or where one docs
  // alias needs two Python names. Keyed by place: `Class.member.arg[.prop]`
  // for parameters and options, `Class.member` for return values and
  // properties. `*` matches one name segment.
  structNamesByPlace: {
    // No docs alias.
    'Page.screenshot.clip': 'FloatRect',
    // No docs alias.
    'ConsoleMessage.location': 'SourceLocation',
    // No docs alias.
    '*.storageState': 'StorageState',
    // No docs alias.
    '*.*.storageState': 'StorageState',
    // No docs alias.
    '*.storageState.cookies': 'StorageStateCookie',
    // No docs alias.
    '*.*.storageState.cookies': 'StorageStateCookie',
    // No docs alias.
    '*.storageState.origins': 'OriginState',
    // No docs alias.
    '*.*.storageState.origins': 'OriginState',
    // The docs alias is `WebStorageItem`, which maps to NameValue elsewhere.
    '*.storageState.origins.localStorage': 'LocalStorageEntry',
    // The docs alias is `WebStorageItem`, which maps to NameValue elsewhere.
    '*.*.storageState.origins.localStorage': 'LocalStorageEntry',
    // No docs alias.
    '*.addCookies.cookies': 'SetCookieParam',
    // No docs alias.
    '*.timing': 'ResourceTiming',
    // No docs alias.
    '*.serverAddr': 'RemoteAddr',
    // No docs alias.
    'Request.sizes': 'RequestSizes',
    // No docs alias.
    '*.*.sourcePosition': 'Position',
    // No docs alias.
    '*.*.targetPosition': 'Position',
    // No docs alias.
    '*.*.viewport': 'ViewportSize',
    // No docs alias.
    '*.*.recordVideoSize': 'ViewportSize',
    // No docs alias.
    'Page.setViewportSize.viewportSize': 'ViewportSize',
    // No docs alias.
    'Screencast.start.size': 'ScreencastSize',
    // No docs alias.
    'APIRequestContext.*.multipart': 'FilePayload',
    // No docs alias.
    'Page.pdf.margin': 'PdfMargins',
    // The docs alias is `Location`, which maps to DebuggerLocation elsewhere.
    'Tracing.group.location': 'TracingGroupLocation',
  },

  // `total=` of a TypedDict, where it differs from the rule "total=False if
  // any field is optional". Keyed by struct name.
  structTotal: {
    // Shipped as total=True, although `line` and `column` are optional.
    DebuggerLocation: true,
    // Shipped as total=True, although every field is optional.
    SecurityDetails: true,
    // Shipped as total=False, although every field is required.
    StorageState: false,
    // Shipped as total=False, although every field is required.
    StorageStateCookie: false,
    // Shipped as total=True, although `line` and `column` are optional.
    TracingGroupLocation: true,
  },

  // Old implementation: the module in playwright/_impl/ that holds each class.
  // Classes not listed are in `_<snake_case name>.py`.
  implModules: {
    APIRequest: '_fetch',
    APIRequestContext: '_fetch',
    APIResponse: '_fetch',
    APIResponseAssertions: '_assertions',
    FrameLocator: '_locator',
    Keyboard: '_input',
    LocatorAssertions: '_assertions',
    Mouse: '_input',
    PageAssertions: '_assertions',
    Request: '_network',
    Response: '_network',
    Route: '_network',
    Touchscreen: '_input',
    WebMCP: '_webmcp',
    WebSocket: '_network',
    WebSocketRoute: '_network',
    Worker: '_page',
  },
};
