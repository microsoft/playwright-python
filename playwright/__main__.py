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

import subprocess
import sys

from playwright._impl._driver import (
    compute_driver_executable,
    get_driver_env,
    node_launch_error,
)
from playwright._impl._errors import Error


def main() -> None:
    try:
        driver_executable, driver_cli = compute_driver_executable()
        try:
            completed_process = subprocess.run(
                [driver_executable, driver_cli, *sys.argv[1:]], env=get_driver_env()
            )
        except OSError as error:
            raise node_launch_error(driver_executable, error)
        sys.exit(completed_process.returncode)
    except Error as error:
        # No Node.js to run the driver with: a message, not a traceback.
        print(error.message, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
