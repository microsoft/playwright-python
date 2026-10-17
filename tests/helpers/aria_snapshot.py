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

"""Helpers for the aria snapshot tests.

unshift() is unshift() in tests/config/utils.ts. assert_contains_yaml() is the
toContainYaml matcher in tests/page/pageTest.ts.
"""

import re


def unshift(snapshot: str) -> str:
    """Removes the empty lines and the common indentation of a YAML template."""
    lines = snapshot.split("\n")
    whitespace_prefix_length = 100
    for line in lines:
        if not line.strip():
            continue
        match = re.match(r"^(\s*)", line)
        if match and len(match[1]) < whitespace_prefix_length:
            whitespace_prefix_length = len(match[1])
    return "\n".join(line[whitespace_prefix_length:] for line in lines if line.strip())


def assert_contains_yaml(received: str, expected: str) -> None:
    """Asserts that received contains expected, without the common indentation."""
    trimmed = [line for line in expected.split("\n") if line.strip()]
    prefix_length = min(len(line) - len(line.lstrip()) for line in trimmed)
    trimmed_expected = "\n".join(line[prefix_length:] for line in trimmed)
    assert (
        trimmed_expected in received
    ), f"Expected substring:\n{trimmed_expected}\nReceived string:\n{received}"
