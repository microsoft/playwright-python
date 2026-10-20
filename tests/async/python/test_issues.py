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

from asyncio import FIRST_COMPLETED, CancelledError, create_task, wait

import pytest

from playwright.async_api import Page


async def test_connection_task_cancel(page: Page) -> None:
    await page.set_content("<input />")
    done, pending = await wait(
        {
            create_task(page.wait_for_selector("input")),
            create_task(page.wait_for_selector("#will-never-resolve")),
        },
        return_when=FIRST_COMPLETED,
    )
    assert len(done) == 1
    assert len(pending) == 1
    for task in pending:
        task.cancel()
        with pytest.raises(CancelledError):
            await task
    assert list(pending)[0].cancelled()
