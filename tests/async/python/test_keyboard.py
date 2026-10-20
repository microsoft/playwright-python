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
import pytest

from playwright.async_api import Error, Page
from tests.server import Server


async def test_should_throw_unknown_keys(page: Page, server: Server) -> None:
    with pytest.raises(Error) as exc:
        await page.keyboard.press("NotARealKey")
    assert exc.value.message == 'Keyboard.press: Unknown key: "NotARealKey"'

    with pytest.raises(Error) as exc:
        await page.keyboard.press("ё")
    assert exc.value.message == 'Keyboard.press: Unknown key: "ё"'

    with pytest.raises(Error) as exc:
        await page.keyboard.press("😊")
    assert exc.value.message == 'Keyboard.press: Unknown key: "😊"'
