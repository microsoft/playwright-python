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

from datetime import timedelta

import pytest

from playwright.async_api import Page, TimeoutError


async def test_click_should_accept_timedelta_for_timeout(page: Page) -> None:
    with pytest.raises(TimeoutError, match="Timeout 1ms exceeded"):
        await page.click("does-not-exist", timeout=timedelta(milliseconds=1))
