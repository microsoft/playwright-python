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

from typing import Dict

from playwright.async_api import BrowserType


async def test_browser_type_launch_should_accept_ignore_default_args_false(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    # Regression for https://github.com/microsoft/playwright-python/issues/3005:
    # passing False used to crash with "expected array, got boolean".
    browser = await browser_type.launch(**launch_arguments, ignore_default_args=False)
    await browser.close()
