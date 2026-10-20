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

"""Port of packages/playwright-core/src/client/timeoutSettings.ts.

Python: a channel call takes the timeout as a number, and there is no AbortSignal,
so navigation_timeout(), timeout() and launch_timeout() return the number that
upstream puts in { signal, timeout }.
"""

from typing import Optional

from playwright._impl_v2.isomorphic.time import (
    DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT,
    DEFAULT_PLAYWRIGHT_TIMEOUT,
)
from playwright._impl_v2.utils.debug import debug_mode

# Sentinel for internal calls that intentionally opt out of a deadline.
NO_TIMEOUT: float = 0


class TimeoutSettings:
    def __init__(self, parent: Optional["TimeoutSettings"] = None) -> None:
        self._parent = parent
        self._default_timeout: Optional[float] = None
        self._default_navigation_timeout: Optional[float] = None

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._default_timeout = timeout

    def set_default_navigation_timeout(self, timeout: Optional[float]) -> None:
        self._default_navigation_timeout = timeout

    def default_navigation_timeout(self) -> Optional[float]:
        return self._default_navigation_timeout

    def default_timeout(self) -> Optional[float]:
        return self._default_timeout

    def navigation_timeout(self, timeout: Optional[float]) -> float:
        return self._navigation_timeout(timeout)

    def timeout(self, timeout: Optional[float]) -> float:
        return self._timeout(timeout)

    def launch_timeout(self, timeout: Optional[float]) -> float:
        return self._launch_timeout(timeout)

    def _navigation_timeout(self, timeout: Optional[float]) -> float:
        if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
            return timeout
        if self._default_navigation_timeout is not None:
            return self._default_navigation_timeout
        if debug_mode() == "inspector":
            return 0
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent._navigation_timeout(timeout)
        return DEFAULT_PLAYWRIGHT_TIMEOUT

    def _timeout(self, timeout: Optional[float]) -> float:
        if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
            return timeout
        if debug_mode() == "inspector":
            return 0
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent._timeout(timeout)
        return DEFAULT_PLAYWRIGHT_TIMEOUT

    def _launch_timeout(self, timeout: Optional[float]) -> float:
        if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
            return timeout
        if debug_mode() == "inspector":
            return 0
        if self._parent:
            return self._parent._launch_timeout(timeout)
        return DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT
