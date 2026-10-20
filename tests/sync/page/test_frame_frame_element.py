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

"""Port of tests/page/frame-frame-element.spec.ts."""

import pytest

from playwright.sync_api import Error, Page
from tests.server import Server
from tests.utils import must

from ..utils import Utils


def test_FR_014_should_work_smoke(page: Page, server: Server, utils: Utils) -> None:
    page.goto(server.EMPTY_PAGE)
    frame1 = utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    frame3 = utils.attach_frame(page, "frame3", server.EMPTY_PAGE)
    frame1handle1 = must(page.query_selector("#frame1"))
    frame1handle2 = frame1.frame_element()
    frame3handle1 = must(page.query_selector("#frame3"))
    frame3handle2 = frame3.frame_element()
    assert frame1handle1.evaluate("(a, b) => a === b", frame1handle2) is True
    assert frame3handle1.evaluate("(a, b) => a === b", frame3handle2) is True
    assert frame1handle1.evaluate("(a, b) => a === b", frame3handle1) is False


def test_FR_015_should_work_with_content_frame(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    frame = utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    handle = frame.frame_element()
    content_frame = handle.content_frame()
    assert content_frame == frame


def test_FR_016_should_work_with_frameset(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/frames/frameset.html")
    frame_element1 = must(page.query_selector("frame"))
    frame = must(frame_element1.content_frame())
    frame_element2 = frame.frame_element()
    assert frame_element1.evaluate("(a, b) => a === b", frame_element2) is True


def test_FR_017_should_throw_when_detached(
    page: Page, server: Server, utils: Utils
) -> None:
    page.goto(server.EMPTY_PAGE)
    frame1 = utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    page.eval_on_selector("#frame1", "e => e.remove()")
    with pytest.raises(Error) as exc_info:
        frame1.frame_element()
    assert "Frame has been detached." in exc_info.value.message


def test_FR_018_should_work_inside_closed_shadow_root(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <div id=framecontainer>
    </div>
    <script>
      const iframe = document.createElement('iframe');
      iframe.setAttribute('name', 'myframe');
      iframe.setAttribute('srcdoc', 'find me');
      const div = document.getElementById('framecontainer');
      const host = div.attachShadow({ mode: 'closed' });
      host.appendChild(iframe);
    </script>
  """
    )

    frame = page.frames[1]
    element = frame.frame_element()
    assert element.get_attribute("name") == "myframe"


def test_FR_019_should_work_inside_declarative_shadow_root(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.set_content(
        """
    <div>
      <template shadowrootmode="open">
        <iframe name="myframe" srcdoc="<h1>Hi!</h1>"></iframe>
        <slot></slot>
      </template>
      <span>footer</span>
    </div>
  """
    )
    frame = page.frames[1]
    element = frame.frame_element()
    assert element.get_attribute("name") == "myframe"
