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

"""The public error classes of the API: Error, TimeoutError and TargetClosedError.

The generated API and the playwright.async_api and playwright.sync_api packages
export them from here. The client raises them through errors.py, the port of
packages/playwright-core/src/client/errors.ts.
"""

from typing import Any, List, Optional


class Error(Exception):
    def __init__(self, message: str) -> None:
        self._message = message
        self._name: Optional[str] = None
        self._stack: Optional[str] = None
        self._details: Optional[Any] = None
        self._log: Optional[List[str]] = None
        super().__init__(message)

    @property
    def message(self) -> str:
        return self._message

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def stack(self) -> Optional[str]:
        return self._stack


class TimeoutError(Error):
    pass


class TargetClosedError(Error):
    def __init__(self, message: str = None) -> None:
        super().__init__(message or "Target page, context or browser has been closed")
