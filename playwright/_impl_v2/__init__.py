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
the same order. utils/ and isomorphic/ hold the ports of the parts of
packages/utils and packages/isomorphic that the client uses and that playwright/_impl
does not have yet; the other pure modules come from playwright/_impl.

What differs from the JS code is marked with a "Python:" comment. The rules:

- Names are snake_case. Implementation methods take the arguments that the
  generated API passes (snake_case, no defaults), not the JS options object.
- A channel call sends its message at once and returns a future, as a JS channel
  call returns a promise (protocol_channels.py, generated).
- An async function runs when it is awaited, not when it is called. Where the JS code
  starts a promise and awaits it later, the port starts a task.
- Python has no AbortSignal: the `signal` options are not ported. Cancelling the task
  that waits for a call aborts the call, as an aborted signal does.
- There is no sync code here: no greenlet, no sync waits.
"""
