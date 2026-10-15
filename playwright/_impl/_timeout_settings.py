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

"""Port of packages/playwright-core/src/client/timeoutSettings.ts."""

from typing import Optional

from playwright._impl._time import (
    DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT_IN_MILLISECONDS,
    DEFAULT_PLAYWRIGHT_TIMEOUT_IN_MILLISECONDS,
)


class TimeoutSettings:

    @staticmethod
    def launch_timeout(timeout: Optional[float] = None) -> float:
        return (
            timeout
            if timeout is not None
            else DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT_IN_MILLISECONDS
        )

    def __init__(self, parent: Optional["TimeoutSettings"]) -> None:
        self._parent = parent
        self._default_timeout: Optional[float] = None
        self._default_navigation_timeout: Optional[float] = None

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._default_timeout = timeout

    def timeout(self, timeout: float = None) -> float:
        if timeout is not None:
            return timeout
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent.timeout()
        return DEFAULT_PLAYWRIGHT_TIMEOUT_IN_MILLISECONDS

    def set_default_navigation_timeout(
        self, navigation_timeout: Optional[float]
    ) -> None:
        self._default_navigation_timeout = navigation_timeout

    def default_navigation_timeout(self) -> Optional[float]:
        return self._default_navigation_timeout

    def default_timeout(self) -> Optional[float]:
        return self._default_timeout

    def navigation_timeout(self, timeout: float = None) -> float:
        if timeout is not None:
            return timeout
        if self._default_navigation_timeout is not None:
            return self._default_navigation_timeout
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent.navigation_timeout()
        return DEFAULT_PLAYWRIGHT_TIMEOUT_IN_MILLISECONDS
