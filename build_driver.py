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

import gzip
import os
import shutil
import subprocess

driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'driver')
package_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playwright_web')
drivers_path = os.path.join(package_path, 'drivers')


if not os.path.exists(drivers_path):
  os.makedirs(drivers_path)
if os.path.exists(os.path.join(driver_path, 'package-lock.json')):
  os.remove(os.path.join(driver_path, 'package-lock.json'))
if os.path.exists(os.path.join(driver_path, 'node_modules')):
  shutil.rmtree(os.path.join(driver_path, 'node_modules'))
if os.path.exists(os.path.join(driver_path, 'out')):
  shutil.rmtree(os.path.join(driver_path, 'out'))

subprocess.run('npm i', cwd=driver_path, shell=True)
subprocess.run('npm run bake', cwd=driver_path, shell=True)

for driver in ['driver-linux', 'driver-macos', 'driver-win.exe']:
  if os.path.exists(os.path.join(package_path, driver)):
    os.remove(os.path.join(package_path, driver))

  in_path = os.path.join(driver_path, 'out', driver)
  out_path = os.path.join(drivers_path, driver + '.gz')
  with open(in_path, 'rb') as f_in, gzip.open(out_path, 'wb') as f_out:
    shutil.copyfileobj(f_in, f_out)
