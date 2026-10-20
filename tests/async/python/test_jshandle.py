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

from typing import Any, Dict

from playwright.async_api import Page


async def test_jshandle_evaluate_work(page: Page) -> None:
    window_handle = await page.evaluate_handle("window")
    assert window_handle
    assert repr(window_handle) == f"<JSHandle preview={window_handle}>"


async def test_jshandle_evaluate_should_work_for_circular_objects(page: Page) -> None:
    a: Dict[str, Any] = {"x": 1}
    a["y"] = a
    result = await page.evaluate("a => { a.y.x += 1; return a; }", a)
    assert result["x"] == 2
    assert result["y"]["x"] == 2
    assert result == result["y"]
