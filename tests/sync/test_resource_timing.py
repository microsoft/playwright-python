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

import pytest


def test_should_work(page, server, is_webkit, is_mac):
    if is_webkit and is_mac:
        pytest.skip()
    with page.expect_event("requestfinished") as request_info:
        page.goto(server.EMPTY_PAGE)
    request = request_info.value
    timing = request.timing
    assert timing["domainLookupStart"] >= -1
    assert timing["domainLookupEnd"] >= timing["domainLookupStart"]
    assert timing["connectStart"] >= timing["domainLookupEnd"]
    assert timing["secureConnectionStart"] == -1
    assert timing["connectEnd"] > timing["secureConnectionStart"]
    assert timing["requestStart"] >= timing["connectEnd"]
    assert timing["responseStart"] > timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000


def test_should_work_for_subresource(page, server, is_win, is_mac, is_webkit):
    if is_webkit and is_mac:
        pytest.skip()
    requests = []
    page.on("requestfinished", lambda request: requests.append(request))
    page.goto(server.PREFIX + "/one-style.html")
    assert len(requests) == 2
    timing = requests[1].timing
    if is_webkit and is_win:
        # Curl does not reuse connections.
        assert timing["domainLookupEnd"] >= timing["domainLookupStart"]
        assert timing["connectStart"] >= timing["domainLookupEnd"]
        assert timing["secureConnectionStart"] == -1
        assert timing["connectEnd"] > timing["secureConnectionStart"]
    else:
        assert timing["domainLookupStart"] == 0 or timing["domainLookupStart"] == -1
        assert timing["domainLookupEnd"] == 0 or timing["domainLookupEnd"] == -1
        assert timing["connectStart"] == 0 or timing["connectStart"] == -1
        assert timing["connectEnd"] == 0 or timing["connectEnd"] == -1
        assert timing["secureConnectionStart"] == -1

    assert timing["domainLookupStart"] >= -1
    assert timing["requestStart"] >= 0
    assert timing["responseStart"] > timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000


def test_should_work_for_ssl(browser, https_server, is_mac, is_webkit):
    if is_webkit and is_mac:
        pytest.skip()
    page = browser.new_page(ignore_https_errors=True)
    with page.expect_event("requestfinished") as request_info:
        page.goto(https_server.EMPTY_PAGE)
    request = request_info.value
    timing = request.timing
    if not (is_webkit and is_mac):
        assert timing["domainLookupStart"] >= -1
        assert timing["domainLookupEnd"] >= timing["domainLookupStart"]
        assert timing["connectStart"] >= timing["domainLookupEnd"]
        assert timing["secureConnectionStart"] > timing["connectStart"]
        assert timing["connectEnd"] > timing["secureConnectionStart"]
        assert timing["requestStart"] >= timing["connectEnd"]

    assert timing["responseStart"] > timing["requestStart"]
    assert timing["responseEnd"] >= timing["responseStart"]
    assert timing["responseEnd"] < 10000
    page.close()


@pytest.mark.skip_browser("webkit")  # In WebKit, redirects don"t carry the timing info
def test_should_work_for_redirect(page, server):
    server.set_redirect("/foo.html", "/empty.html")
    responses = []
    page.on("response", lambda response: responses.append(response))
    page.goto(server.PREFIX + "/foo.html")
    for r in responses:
        r.finished()

    assert len(responses) == 2
    assert responses[0].url == server.PREFIX + "/foo.html"
    assert responses[1].url == server.PREFIX + "/empty.html"

    timing1 = responses[0].request.timing
    assert timing1["domainLookupStart"] >= -1
    assert timing1["domainLookupEnd"] >= timing1["domainLookupStart"]
    assert timing1["connectStart"] >= timing1["domainLookupEnd"]
    assert timing1["secureConnectionStart"] == -1
    assert timing1["connectEnd"] > timing1["secureConnectionStart"]
    assert timing1["requestStart"] >= timing1["connectEnd"]
    assert timing1["responseStart"] > timing1["requestStart"]
    assert timing1["responseEnd"] >= timing1["responseStart"]
    assert timing1["responseEnd"] < 10000

    timing2 = responses[1].request.timing
    assert timing2["domainLookupStart"] == -1
    assert timing2["domainLookupEnd"] == -1
    assert timing2["connectStart"] == -1
    assert timing2["secureConnectionStart"] == -1
    assert timing2["connectEnd"] == -1
    assert timing2["requestStart"] >= 0
    assert timing2["responseStart"] > timing2["requestStart"]
    assert timing2["responseEnd"] >= timing2["responseStart"]
    assert timing2["responseEnd"] < 10000
