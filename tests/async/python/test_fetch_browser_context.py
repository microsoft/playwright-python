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


"""Python only: tests of v2 (playwright/_impl_v2) that no upstream test covers.

The v1 tests of the same behaviors are in tests/async/legacy, marked @only_v1.
"""

from pathlib import Path

import pytest

from playwright.async_api import BrowserContext, Error, FormData
from tests.server import Server


async def test_should_reject_file_value_in_form(
    context: BrowserContext, server: Server, tmp_path: Path
) -> None:
    file = tmp_path / "f.txt"
    file.write_bytes(b"hello")
    form = FormData()
    form.set("attachment", file)
    with pytest.raises(Error, match="Please use options.multipart instead"):
        await context.request.post(server.EMPTY_PAGE, form=form)
