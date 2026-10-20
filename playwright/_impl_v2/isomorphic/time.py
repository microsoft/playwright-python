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

"""Port of packages/isomorphic/time.ts."""

import math
import time

DEFAULT_PLAYWRIGHT_TIMEOUT = 30_000
DEFAULT_PLAYWRIGHT_LAUNCH_TIMEOUT = 3 * 60 * 1000  # 3 minutes


def monotonic_time() -> float:
    # Milliseconds, with microsecond precision.
    return math.floor(time.monotonic() * 1000 * 1000) / 1000
