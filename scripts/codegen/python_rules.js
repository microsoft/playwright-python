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

  // Options that are positional parameters in Python, in every method. Other
  // options are keyword-only, and every `### param` is positional (in docs order).
  positionalOptions: [
    // expect_*(predicate) and wait_for_event(event, predicate).
    'predicate',
  ],

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
  },
};
