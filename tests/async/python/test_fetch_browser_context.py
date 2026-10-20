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


"""Python only: tests of behaviors that no upstream test covers."""

import asyncio
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs

import pytest

from playwright.async_api import BrowserContext, Error, FormData
from tests.server import Server
from tests.utils import must


async def test_should_reject_file_value_in_form(
    context: BrowserContext, server: Server, tmp_path: Path
) -> None:
    file = tmp_path / "f.txt"
    file.write_bytes(b"hello")
    form = FormData()
    form.set("attachment", file)
    with pytest.raises(Error, match="Please use options.multipart instead"):
        await context.request.post(server.EMPTY_PAGE, form=form)


@pytest.mark.parametrize(
    "method", ["fetch", "delete", "get", "head", "patch", "post", "put"]
)
async def test_should_support_query_params(
    context: BrowserContext, server: Server, method: str
) -> None:
    expected_params = {"p1": "v1", "парам2": "знач2"}
    [server_req, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        getattr(context.request, method)(
            server.EMPTY_PAGE + "?p1=foo", params=expected_params
        ),
    )
    assert list(map(lambda x: x.decode(), server_req.args["p1".encode()])) == [
        "foo",
        "v1",
    ]
    assert server_req.args["парам2".encode()][0].decode() == "знач2"


async def test_should_send_empty_form(context: BrowserContext, server: Server) -> None:
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.post(server.EMPTY_PAGE, form={}),
    )
    assert request.getHeader("Content-Type") == "application/x-www-form-urlencoded"
    assert request.getHeader("Content-Length") == "0"


async def test_should_send_empty_multipart(
    context: BrowserContext, server: Server
) -> None:
    # The test server rejects an empty multipart body in POST requests before handling them.
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.put(server.EMPTY_PAGE, multipart={}),
    )
    assert cast(str, request.getHeader("Content-Type")).startswith(
        "multipart/form-data; "
    )
    assert must(request.getHeader("Content-Length")) == str(
        len(must(request.post_body))
    )


async def test_should_support_form_data_set_overwrites_previous_values(
    context: BrowserContext, server: Server
) -> None:
    form = FormData()
    form.append("name", "first")
    form.append("name", "second")
    form.set("name", "final")
    form.set("age", 30)
    [request, _] = await asyncio.gather(
        server.wait_for_request("/empty.html"),
        context.request.post(server.EMPTY_PAGE, form=form),
    )
    params = parse_qs(must(request.post_body))
    assert params[b"name"] == [b"final"]
    assert params[b"age"] == [b"30"]
