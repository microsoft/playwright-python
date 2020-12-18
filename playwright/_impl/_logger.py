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

import os
import sys

debug_enabled = os.environ.get("PWDEBUG") or (
    "DEBUG" in os.environ and "pw:api" in os.environ["DEBUG"]
)


def init_logger() -> None:
    if os.environ.get("PWDEBUG"):
        os.environ["DEBUG"] = (
            os.environ["DEBUG"] + ",pw:api" if "DEBUG" in os.environ else "pw:api"
        )


def log_api(text: str) -> None:
    if debug_enabled:
        print(f"  \033[1m\033[96mpw:api\033[0m {text}", file=sys.stderr)
