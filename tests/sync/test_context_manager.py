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

from playwright.sync_api import BrowserType


def test_context_managers(browser_type: BrowserType, launch_arguments):
    with browser_type.launch(**launch_arguments) as browser:
        with browser.new_context() as context:
            with context.new_page():
                assert len(context.pages) == 1
            assert len(context.pages) == 0
            assert len(browser.contexts) == 1
        assert len(browser.contexts) == 0
    assert not browser.is_connected()
