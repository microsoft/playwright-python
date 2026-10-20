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

"""Port of DebugLogger in packages/utils/debugLogger.ts.

Python: the `debug` package of Node.js reads DEBUG=pw:api,pw:channel; this reads the
same variable and prints to stderr, without colors.
"""

import os
import sys
from typing import Set

LogName = str


class DebugLogger:
    def __init__(self) -> None:
        self._enabled: Set[str] = set()
        for name in (os.environ.get("DEBUG") or "").split(","):
            name = name.strip()
            if name == "pw:*":
                self._enabled.update({"api", "channel"})
            elif name.startswith("pw:"):
                self._enabled.add(name[3:])

    def log(self, name: LogName, message: object) -> None:
        if self.is_enabled(name):
            print(f"pw:{name} {message}", file=sys.stderr)

    def is_enabled(self, name: LogName) -> bool:
        return name in self._enabled


debug_logger = DebugLogger()
