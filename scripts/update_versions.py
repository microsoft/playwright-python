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
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        readme = Path("README.md").resolve()
        text = readme.read_text(encoding="utf-8")
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            rx = re.compile(
                r"<!-- GEN:"
                + browser_type.name
                + r"-version -->([^<]+)<!-- GEN:stop -->"
            )
            browser = browser_type.launch()
            text = rx.sub(
                f"<!-- GEN:{browser_type.name}-version -->{browser.version}<!-- GEN:stop -->",
                text,
            )
            browser.close()
        readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
