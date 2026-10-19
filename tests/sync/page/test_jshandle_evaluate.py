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

"""Port of tests/page/jshandle-evaluate.spec.ts."""

from playwright.sync_api import Page


def test_JH_005_should_work_with_function_smoke(page: Page) -> None:
    window_handle = page.evaluate_handle(
        """() => {
        window['foo'] = [1, 2];
        return window;
      }"""
    )
    assert window_handle.evaluate("w => w['foo']") == [1, 2]


def test_JH_006_should_work_with_expression(page: Page) -> None:
    window_handle = page.evaluate_handle(
        """() => {
        window['foo'] = [1, 2];
        return window;
      }"""
    )
    assert window_handle.evaluate("window.foo") == [1, 2]
