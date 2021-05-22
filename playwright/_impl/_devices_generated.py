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
    from typing import TYPE_CHECKING, TypedDict
else:  # pragma: no cover
    from typing_extensions import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from playwright._impl._api_structures import ViewportSize


class DeviceDescriptor(TypedDict):
    viewport: "ViewportSize"
    user_agent: str
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool


Devices = TypedDict(
    "Devices",
    {
        "Blackberry PlayBook": DeviceDescriptor,
        "Blackberry PlayBook landscape": DeviceDescriptor,
        "BlackBerry Z30": DeviceDescriptor,
        "BlackBerry Z30 landscape": DeviceDescriptor,
        "Galaxy Note 3": DeviceDescriptor,
        "Galaxy Note 3 landscape": DeviceDescriptor,
        "Galaxy Note II": DeviceDescriptor,
        "Galaxy Note II landscape": DeviceDescriptor,
        "Galaxy S III": DeviceDescriptor,
        "Galaxy S III landscape": DeviceDescriptor,
        "Galaxy S5": DeviceDescriptor,
        "Galaxy S5 landscape": DeviceDescriptor,
        "Galaxy S8": DeviceDescriptor,
        "Galaxy S8 landscape": DeviceDescriptor,
        "Galaxy S9+": DeviceDescriptor,
        "Galaxy S9+ landscape": DeviceDescriptor,
        "Galaxy Tab S4": DeviceDescriptor,
        "Galaxy Tab S4 landscape": DeviceDescriptor,
        "iPad (gen 6)": DeviceDescriptor,
        "iPad (gen 6) landscape": DeviceDescriptor,
        "iPad (gen 7)": DeviceDescriptor,
        "iPad (gen 7) landscape": DeviceDescriptor,
        "iPad Mini": DeviceDescriptor,
        "iPad Mini landscape": DeviceDescriptor,
        "iPad Pro 11": DeviceDescriptor,
        "iPad Pro 11 landscape": DeviceDescriptor,
        "iPhone 6": DeviceDescriptor,
        "iPhone 6 landscape": DeviceDescriptor,
        "iPhone 6 Plus": DeviceDescriptor,
        "iPhone 6 Plus landscape": DeviceDescriptor,
        "iPhone 7": DeviceDescriptor,
        "iPhone 7 landscape": DeviceDescriptor,
        "iPhone 7 Plus": DeviceDescriptor,
        "iPhone 7 Plus landscape": DeviceDescriptor,
        "iPhone 8": DeviceDescriptor,
        "iPhone 8 landscape": DeviceDescriptor,
        "iPhone 8 Plus": DeviceDescriptor,
        "iPhone 8 Plus landscape": DeviceDescriptor,
        "iPhone SE": DeviceDescriptor,
        "iPhone SE landscape": DeviceDescriptor,
        "iPhone X": DeviceDescriptor,
        "iPhone X landscape": DeviceDescriptor,
        "iPhone XR": DeviceDescriptor,
        "iPhone XR landscape": DeviceDescriptor,
        "iPhone 11": DeviceDescriptor,
        "iPhone 11 landscape": DeviceDescriptor,
        "iPhone 11 Pro": DeviceDescriptor,
        "iPhone 11 Pro landscape": DeviceDescriptor,
        "iPhone 11 Pro Max": DeviceDescriptor,
        "iPhone 11 Pro Max landscape": DeviceDescriptor,
        "iPhone 12": DeviceDescriptor,
        "iPhone 12 landscape": DeviceDescriptor,
        "iPhone 12 Pro": DeviceDescriptor,
        "iPhone 12 Pro landscape": DeviceDescriptor,
        "iPhone 12 Pro Max": DeviceDescriptor,
        "iPhone 12 Pro Max landscape": DeviceDescriptor,
        "JioPhone 2": DeviceDescriptor,
        "JioPhone 2 landscape": DeviceDescriptor,
        "Kindle Fire HDX": DeviceDescriptor,
        "Kindle Fire HDX landscape": DeviceDescriptor,
        "LG Optimus L70": DeviceDescriptor,
        "LG Optimus L70 landscape": DeviceDescriptor,
        "Microsoft Lumia 550": DeviceDescriptor,
        "Microsoft Lumia 550 landscape": DeviceDescriptor,
        "Microsoft Lumia 950": DeviceDescriptor,
        "Microsoft Lumia 950 landscape": DeviceDescriptor,
        "Nexus 10": DeviceDescriptor,
        "Nexus 10 landscape": DeviceDescriptor,
        "Nexus 4": DeviceDescriptor,
        "Nexus 4 landscape": DeviceDescriptor,
        "Nexus 5": DeviceDescriptor,
        "Nexus 5 landscape": DeviceDescriptor,
        "Nexus 5X": DeviceDescriptor,
        "Nexus 5X landscape": DeviceDescriptor,
        "Nexus 6": DeviceDescriptor,
        "Nexus 6 landscape": DeviceDescriptor,
        "Nexus 6P": DeviceDescriptor,
        "Nexus 6P landscape": DeviceDescriptor,
        "Nexus 7": DeviceDescriptor,
        "Nexus 7 landscape": DeviceDescriptor,
        "Nokia Lumia 520": DeviceDescriptor,
        "Nokia Lumia 520 landscape": DeviceDescriptor,
        "Nokia N9": DeviceDescriptor,
        "Nokia N9 landscape": DeviceDescriptor,
        "Pixel 2": DeviceDescriptor,
        "Pixel 2 landscape": DeviceDescriptor,
        "Pixel 2 XL": DeviceDescriptor,
        "Pixel 2 XL landscape": DeviceDescriptor,
        "Pixel 3": DeviceDescriptor,
        "Pixel 3 landscape": DeviceDescriptor,
        "Pixel 4": DeviceDescriptor,
        "Pixel 4 landscape": DeviceDescriptor,
        "Pixel 4a (5G)": DeviceDescriptor,
        "Pixel 4a (5G) landscape": DeviceDescriptor,
        "Pixel 5": DeviceDescriptor,
        "Pixel 5 landscape": DeviceDescriptor,
        "Moto G4": DeviceDescriptor,
        "Moto G4 landscape": DeviceDescriptor,
    },
)
