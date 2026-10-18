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

import pathlib
from typing import List, Tuple, Union

from playwright._impl._api_structures import FilePayload

FormDataValue = Union[bool, float, str, pathlib.Path, FilePayload]


class FormData:
    def __init__(self) -> None:
        self._fields: List[Tuple[str, FormDataValue]] = []

    def set(self, name: str, value: FormDataValue) -> "FormData":
        # Like FormData.set() of the WHATWG spec: the first entry with the name takes
        # the value in place, and the others are removed.
        fields: List[Tuple[str, FormDataValue]] = []
        replaced = False
        for field_name, field_value in self._fields:
            if field_name != name:
                fields.append((field_name, field_value))
            elif not replaced:
                fields.append((name, value))
                replaced = True
        if not replaced:
            fields.append((name, value))
        self._fields = fields
        return self

    def append(self, name: str, value: FormDataValue) -> "FormData":
        self._fields.append((name, value))
        return self
