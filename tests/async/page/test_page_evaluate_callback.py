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

"""Port of tests/page/page-evaluate-callback.spec.ts."""

import pytest

from playwright.async_api import Error, Page


@pytest.mark.xfail(
    reason="python: a function argument is serialized as undefined instead of throwing",
    strict=True,
)
async def test_EV_112_should_throw_without_the_expose_functions_option(
    page: Page,
) -> None:
    with pytest.raises(
        Error, match=r'Attempting to serialize unexpected value at position "cb": '
    ):
        await page.evaluate("({ cb }) => cb()", {"cb": lambda: None})
