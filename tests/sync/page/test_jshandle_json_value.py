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

"""Port of tests/page/jshandle-json-value.spec.ts."""

from datetime import datetime, timezone

from playwright.sync_api import Page


def test_JH_007_should_work_smoke(page: Page) -> None:
    a_handle = page.evaluate_handle("() => ({ foo: 'bar' })")
    json = a_handle.json_value()
    assert json == {"foo": "bar"}


def test_JH_008_should_work_with_dates(page: Page) -> None:
    date_handle = page.evaluate_handle("() => new Date('2017-09-26T00:00:00.000Z')")
    date = date_handle.json_value()
    assert date == datetime(2017, 9, 26, tzinfo=timezone.utc)


def test_JH_009_should_handle_circular_objects(page: Page) -> None:
    handle = page.evaluate_handle("const a = {}; a.b = a; a")
    # Python's == recurses forever on two distinct circular dicts, so check the
    # shape of { b: <itself> } directly.
    a = handle.json_value()
    assert list(a.keys()) == ["b"]
    assert a["b"] is a
