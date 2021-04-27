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

# These are types that we use in the API. They are public and are a part of the
# stable API.


from typing import Optional


class Error(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        self.name: Optional[str] = None
        self.stack: Optional[str] = None
        super().__init__(message)


class TimeoutError(Error):
    pass
