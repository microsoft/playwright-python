#!/usr/bin/env python
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

import sys
from pathlib import Path
from typing import List

LICENSE_HEADER = """
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
""".strip()


def file_has_license(file_path: str) -> None:
    path = Path(file_path)
    if not path.name.endswith(".py"):
        return
    if not path.exists():
        raise Exception(f"File {file_path} does not exist")
    content = path.read_text(encoding="utf-8")
    if content.strip() == "":
        return
    if content.startswith("#!"):
        # flake8: noqa: E203
        content = content[content.find("\n") + 1 :]
    if not content.startswith(LICENSE_HEADER):
        raise Exception(f"File {file_path} does not have license header")


def main() -> None:
    errors: List[str] = []

    for file_path in sys.argv[1:]:
        try:
            file_has_license(file_path)
        except Exception as e:
            errors.append(str(e))

    if errors:
        print("Missing license header in files:")
        for error in errors:
            print("  -", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
