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

from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    file = Path("playwright/_impl/_devices_generated.py").open("w")
    file.write(
        """
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
if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import TypedDict, TYPE_CHECKING
else:  # pragma: no cover
    from typing_extensions import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright._impl._api_structures import ViewportSize


class DeviceDescriptor(TypedDict):
    viewport: "ViewportSize"
    user_agent: str
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool
"""
    )
    with sync_playwright() as playwright:
        file.write('Devices = TypedDict("Devices", {')
        for device in playwright.devices.keys():
            file.write(f'"{device}": DeviceDescriptor,')
        file.write("})")
        file.close()


if __name__ == "__main__":
    main()
