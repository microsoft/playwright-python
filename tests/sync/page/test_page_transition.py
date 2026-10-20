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

"""Port of tests/page/page-transition.spec.ts."""


import pytest

from playwright.sync_api import Error, Page


def test_PA_038_should_not_crash_when_filter_transition_completes(
    page: Page, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip(
            "fixme: Web process crashes on the compositor thread when a filter transitions to none"
        )

    page.set_content(
        f"""
    <style>
      div {{ transition: filter 0.1s; }}
      .dim {{ filter: brightness(0.95); }}
    </style>
    {'<div>hello</div>' * 10}
  """
    )
    crashed = False

    def on_crash(_: Page) -> None:
        nonlocal crashed
        crashed = True

    page.on("crash", on_crash)
    i = 0
    while i < 10 and not crashed:
        try:
            page.evaluate(
                """async () => {
        const divs = [...document.querySelectorAll('div')];
        const settled = () => Promise.all(divs.map(div => new Promise(f => div.addEventListener('transitionend', f, { once: true }))));
        let promise = settled();
        divs.forEach(div => div.classList.add('dim'));
        await promise;
        promise = settled();
        divs.forEach(div => div.classList.remove('dim'));
        await promise;
      }"""
            )
        except Error:
            pass
        i += 1
    assert crashed is False
