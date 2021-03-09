# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

import sys
from io import StringIO
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 9), reason="requires python3.9 or higher"
)


@patch("sys.stderr", new_callable=StringIO)
@patch("sys.stdout", new_callable=StringIO)
def test_generate_sync_api(stdout, stderr):
    from scripts.generate_sync_api import main as generate_sync_api

    generate_sync_api()


@patch("sys.stderr", new_callable=StringIO)
@patch("sys.stdout", new_callable=StringIO)
def test_generate_async_api(stdout, stderr):
    from scripts.generate_async_api import main as generate_async_api

    generate_async_api()
