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

"""Port of packages/playwright-core/src/client/fileUtils.ts."""

import os
from pathlib import Path
from typing import Union

# Keep in sync with the server.
file_upload_size_limit = 50 * 1024 * 1024


def mkdir_if_needed(file_path: Union[Path, str]) -> None:
    # This will harmlessly throw on windows if the dirname is the root directory.
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    except OSError:
        pass
