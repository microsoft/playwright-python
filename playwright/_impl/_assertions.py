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

"""Python only: the scope of the soft assertions, expect.soft().

pytest-playwright opens a scope for each test with _soft_scope() and reports the
errors that the scope collected; keep this module and its two functions where they
are. The matchers are in assertions.py.
"""

from contextlib import contextmanager
from typing import Iterator, List, Optional

_soft_errors: Optional[List[AssertionError]] = None


@contextmanager
def _soft_scope() -> Iterator[List[AssertionError]]:
    global _soft_errors
    assert _soft_errors is None, "nested soft assertion scopes are not supported"
    _soft_errors = []
    try:
        yield _soft_errors
    finally:
        _soft_errors = None


def _record_soft_or_raise(error: AssertionError, is_soft: bool) -> None:
    __tracebackhide__ = True
    if is_soft:
        if _soft_errors is None:
            raise RuntimeError(
                "expect.soft(...) requires pytest-playwright>=0.7.3 "
                "(or pytest-playwright-asyncio>=0.7.3). Upgrade the plugin, "
                "or use a regular expect(...) assertion."
            )
        _soft_errors.append(error)
        return
    raise error
