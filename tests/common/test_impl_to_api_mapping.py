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

from typing import List, Optional

from playwright._impl._impl_to_api_mapping import ImplToApiMapping


def test_wrap_handler_ignores_keyword_only_parameters() -> None:
    calls: List[Optional[int]] = []

    class Input:
        def blur(self, *, timeout: Optional[int] = None) -> None:
            calls.append(timeout)

    ImplToApiMapping().wrap_handler(Input().blur)("locator")

    assert calls == [None]
