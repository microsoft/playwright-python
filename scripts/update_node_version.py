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

"""Pin NODE_VERSION to the latest Node.js LTS.

A Python port of upstream's utils/build/update-playwright-node.mjs: fetch the
Node.js release index and take the most recent LTS release, which is the Node.js
version Playwright bundles. Run this during a roll, alongside bumping
DRIVER_VERSION. (Unlike upstream we don't touch Dockerfiles — the
playwright-python images don't pin a Node.js version; the bundled driver carries
its own Node.js.)
"""

import json
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"


def latest_lts_version() -> str:
    with urllib.request.urlopen(NODE_INDEX_URL) as response:  # noqa: S310
        releases = json.load(response)
    # The index is ordered newest-first; each release's "lts" field is false for
    # non-LTS lines and the LTS codename otherwise. The first truthy one is the
    # latest LTS release, e.g. {"version": "v24.16.0", "lts": "Krypton"}.
    for release in releases:
        if release.get("lts"):
            return str(release["version"]).lstrip("v")
    raise SystemExit("No LTS release found in the Node.js release index")


def main() -> None:
    version = latest_lts_version()
    (REPO_ROOT / "NODE_VERSION").write_text(version + "\n")
    print(f"NODE_VERSION set to {version}")


if __name__ == "__main__":
    main()
