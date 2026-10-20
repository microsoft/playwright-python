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

"""Python only: helpers of the generated API (playwright/{async,sync}_api/_generated.py)."""

import datetime
from typing import Optional, Union, overload


@overload
def to_milliseconds(value: Union[float, datetime.timedelta]) -> float: ...


@overload
def to_milliseconds(value: None) -> None: ...


@overload
def to_milliseconds(
    value: Union[float, datetime.timedelta, None],
) -> Optional[float]: ...


def to_milliseconds(
    value: Union[float, datetime.timedelta, None],
) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, datetime.timedelta):
        return value / datetime.timedelta(milliseconds=1)
    return value
