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

"""Port of createCallIdGenerator() in packages/isomorphic/trace/traceUtils.ts."""

import random
from typing import Callable

_last_id_ordinal = 0


def create_call_id_generator() -> Callable[[], str]:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    prefix = ""
    for _ in range(4):
        prefix += alphabet[random.randrange(len(alphabet))]

    def next_call_id() -> str:
        global _last_id_ordinal
        _last_id_ordinal += 1
        return f"{prefix}@{_last_id_ordinal}"

    return next_call_id
