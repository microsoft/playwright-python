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

"""Test hook options for browserType.launch(), in both flavors.

Upstream tests pass hooks such as { __testHookSeleniumRemoteURL } as untyped launch
options. The driver accepts __testHook* parameters when PWTEST_UNDER_TEST is set (the
test conftest sets it). The Python launch() has no such keyword, so launch_test_hook()
adds the parameter to the launch message. The test must be marked
@pytest.mark.skip_protocol_check: the parameter is not in the protocol.
"""

from contextlib import contextmanager
from typing import Any, Iterator, Mapping


@contextmanager
def launch_test_hook(browser_type: Any, name: str, value: Any) -> Iterator[None]:
    """While active, browser_type.launch() sends the name parameter with value.

    Works with the BrowserType of either flavor.
    """
    assert name.startswith("__testHook")
    channel = browser_type._impl_obj._channel
    original = channel._call

    async def call(method: str, params: Mapping[str, Any], timeout: float) -> Any:
        if method == "launch":
            params = {**params, name: value}
        return await original(method, params, timeout)

    setattr(channel, "_call", call)
    try:
        yield
    finally:
        delattr(channel, "_call")
