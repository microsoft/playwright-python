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
import re
import sys
from typing import List, Pattern

LogName = str


class DebugLogger:
    def __init__(self) -> None:
        # Python: the names of the `debug` npm package, which debugLogger.ts uses:
        # DEBUG is a list of names, split on commas and spaces; `*` in a name
        # matches anything; a name that starts with `-` turns its matches off.
        self._names: List[Pattern[str]] = []
        self._skips: List[Pattern[str]] = []
        for name in re.split(r"[\s,]+", (os.environ.get("DEBUG") or "").strip()):
            if not name:
                continue
            if name.startswith("-"):
                self._skips.append(_template(name[1:]))
            else:
                self._names.append(_template(name))

    def log(self, name: LogName, message: object) -> None:
        if self.is_enabled(name):
            print(f"pw:{name} {message}", file=sys.stderr)

    def is_enabled(self, name: LogName) -> bool:
        full_name = "pw:" + name
        if any(skip.match(full_name) for skip in self._skips):
            return False
        return any(enabled.match(full_name) for enabled in self._names)


def _template(name: str) -> Pattern[str]:
    # matchesTemplate() of the `debug` package: `*` matches any text.
    return re.compile(
        "^" + ".*".join(re.escape(part) for part in name.split("*")) + "$"
    )


debug_logger = DebugLogger()
