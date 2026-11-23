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

"""Python only: tests of behaviors that no upstream test covers."""

import sys
from types import FrameType
from typing import Any

from playwright._impl.protocol.validator_primitives import t_any, t_optional
from playwright.sync_api import Page


def test_evaluate_should_not_validate_absent_optional_fields(page: Page) -> None:
    # Regression test for https://github.com/microsoft/playwright-python/issues/3362.
    optional_code = getattr(t_optional(t_any), "__code__")
    absent_calls = 0

    def profile(frame: FrameType, event: str, arg: Any) -> None:
        nonlocal absent_calls
        if event == "call" and frame.f_code is optional_code:
            path = frame.f_locals["path"]
            if path.startswith("value.") and frame.f_locals["arg"] is None:
                absent_calls += 1

    previous_profile = sys.getprofile()
    sys.setprofile(profile)
    try:
        result = page.evaluate(
            """Array.from({length: 200}, (_, i) => ({
                id: i, name: 'item ' + i, price: i * 1.5,
                url: 'https://example.com/' + i, tags: ['a', 'b']
            }))"""
        )
    finally:
        sys.setprofile(previous_profile)

    assert result == [
        {
            "id": i,
            "name": f"item {i}",
            "price": i * 1.5,
            "url": f"https://example.com/{i}",
            "tags": ["a", "b"],
        }
        for i in range(200)
    ]
    assert absent_calls == 0
