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

from typing import Optional, TypeVar

TARGET_CLOSED_ERROR_MESSAGE = "Target page, context or browser has been closed"

MustType = TypeVar("MustType")


def must(value: Optional[MustType]) -> MustType:
    assert value
    return value


def chromium_version_less_than(a: str, b: str) -> bool:
    left = list(map(int, a.split(".")))
    right = list(map(int, b.split(".")))
    for i in range(4):
        if left[i] > right[i]:
            return False
        if left[i] < right[i]:
            return True
    return False
