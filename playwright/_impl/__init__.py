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

"""A line-by-line port of the JS client, packages/playwright-core/src/client.

Each module is the port of the client file with the same name in snake_case
(page.ts is page.py, browserContext.ts is browser_context.py), with the members in
the same order. isomorphic/, protocol/ and utils/ hold the ports of the parts of
packages/isomorphic, packages/protocol and packages/utils that the client uses.

The modules whose names start with an underscore are Python only. The generated API
(playwright/{async,sync}_api/_generated.py) imports them by these names:
_api_classes.py (the implementation of each API class), _api_structures.py (the
TypedDicts, generated from the docs), _async_base.py and _sync_base.py (the base
classes of the API objects), _impl_to_api_mapping.py, _errors.py (the public error
classes), _form_data.py and _helper.py. _greenlets.py runs the sync API, _driver.py
finds the bundled driver, _protocol_check.py and _protocol.py (generated) check the
messages in the tests, and pytest-playwright uses _assertions.py.

The rules of the port are in transform.md, next to this file. What
differs from the JS code is marked with a "Python:" comment. In short:

- Names are snake_case. Implementation methods take the arguments that the
  generated API passes (snake_case, no defaults), not the JS options object.
- The structure follows the JS; the timing follows asyncio. `await` is `await`; a
  promise that is awaited later is a task; `.catch(() => {})` is fire_and_forget()
  (utils/tasks.py); Promise.all() is asyncio.gather(); Promise.race() is race().
- A channel call sends its message at once and returns an awaitable, as a JS
  channel call returns a promise (protocol_channels.py, generated).
- A JS async function runs up to its first await at the call; a coroutine runs when
  a task runs it. Where a caller depends on that, the method is a plain def that
  runs the prefix and returns the awaitable of the rest (the wait_for_*() methods).
- Python has no AbortSignal: the `signal` options are not ported. Cancelling the task
  that waits for a call aborts the call, as an aborted signal does.
- The sync API runs on greenlets (playwright/sync_api/_context_manager.py,
  _sync_base.py, _greenlets.py): a greenlet runs the event loop, and a sync call
  switches to it. Each object carries `_loop` and `_dispatcher_fiber` for the
  generated API; a user callback that may block runs in a greenlet of its own
  (transform.md, section 13).
"""
