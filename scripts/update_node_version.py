#!/usr/bin/env python3
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

"""Pin NODE_VERSION to the latest Node.js release of the same major version.

Fetch the Node.js release index and take the most recent release of the major
version that NODE_VERSION names. Run this during a roll, alongside bumping
DRIVER_VERSION. To move to a new major version, edit NODE_VERSION by hand, for
example to 28.0.0, and run this script.
"""

import json
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_VERSION_PATH = REPO_ROOT / "NODE_VERSION"
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"


def latest_version(major: str) -> str:
    with urllib.request.urlopen(NODE_INDEX_URL) as response:  # noqa: S310
        releases = json.load(response)
    # The index is ordered newest-first, e.g. {"version": "v26.13.1", ...}.
    for release in releases:
        version = str(release["version"]).lstrip("v")
        if version.split(".")[0] == major:
            return version
    raise SystemExit(f"No Node.js {major} release found in the Node.js release index")


def main() -> None:
    old_version = NODE_VERSION_PATH.read_text().strip()
    version = latest_version(old_version.split(".")[0])
    NODE_VERSION_PATH.write_text(version + "\n")
    print(f"NODE_VERSION: {old_version} -> {version}")


if __name__ == "__main__":
    main()
