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

"""Port of tests/page/firefox-network-response.spec.ts."""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from playwright.async_api import Page, Response
from tests.server import Server, TestServerRequest

# Tests the Firefox network observer.
pytestmark = pytest.mark.only_browser("firefox")

Header = Dict[str, str]


async def expect_header_fields(response: Response, expected: List[Header]) -> None:
    headers = await response.headers_array()
    all_headers = await response.all_headers()
    names: List[str] = []
    for header in expected:
        if header["name"].lower() not in names:
            names.append(header["name"].lower())
    for name in names:
        fields = [header for header in expected if header["name"].lower() == name]
        values = [header["value"] for header in fields]
        assert [
            header for header in headers if header["name"].lower() == name
        ] == fields
        assert await response.header_values(name) == values
        combined = ("\n" if name == "set-cookie" else ", ").join(values)
        assert await response.header_value(name) == combined
        assert all_headers[name] == combined


async def fetch_response(page: Page, url: str) -> Tuple[Response, Dict[str, Any]]:
    async with page.expect_response(url) as response_info:
        fetched = await page.evaluate(
            """async url => {
          const response = await fetch(url);
          return { status: response.status, body: await response.text() };
        }""",
            url,
        )
    return await response_info.value, fetched


def write_raw_response(
    request: TestServerRequest, status: int, headers: List[Tuple[str, str]], body: bytes
) -> None:
    """Writes the response with the header names as given.

    Like Node.js's response.writeHead(status, rawHeaders). The test server (twisted)
    changes the case of the header names, so this writes the response to the socket.
    """
    lines = [
        f"HTTP/1.1 {status} {'OK' if status == 200 else 'Found'}",
        *[f"{name}: {value}" for name, value in headers],
        f"Content-Length: {len(body)}",
        "Connection: close",
    ]
    transport = request.transport
    assert transport
    transport.write(("\r\n".join(lines) + "\r\n\r\n").encode() + body)
    transport.loseConnection()


@pytest.mark.parametrize("status", [200, 302])
async def test_FF_005_should_preserve_original_response_header_fields_for_responses(
    page: Page, server: Server, status: int
) -> None:
    headers = [
        {"name": "Date", "value": "Wed, 21 Oct 2037 07:28:00 GMT"},
        {"name": "X-Literal", "value": 'first, "second, third"'},
        {"name": "X-Identical", "value": "same"},
        {"name": "X-Identical", "value": "same"},
        {"name": "X-Repeat", "value": "first, literal"},
        {"name": "x-repeat", "value": "second"},
        {"name": "Set-Cookie", "value": "a=b; Expires=Wed, 21 Oct 2037 07:28:00 GMT"},
        {
            "name": "Set-Cookie",
            "value": "c=d; Expires=Wed, 21 Oct 2037 07:28:00 GMT; Path=/",
        },
        {
            "name": "WWW-Authenticate",
            "value": 'Digest realm="one, two", qop="auth, auth-int"',
        },
        {"name": "WWW-Authenticate", "value": 'Basic realm="three, four"'},
        {"name": "Proxy-Authenticate", "value": 'Basic realm="five, six"'},
        {"name": "Proxy-Authenticate", "value": 'Basic realm="five, six"'},
    ]

    def handle(request: TestServerRequest) -> None:
        write_raw_response(
            request,
            status,
            [
                ("Content-Type", "text/html"),
                *([("Location", "/empty.html")] if status == 302 else []),
                *[(header["name"], header["value"]) for header in headers],
            ],
            b"body",
        )

    server.set_route("/headers", handle)
    final_response = await page.goto(server.PREFIX + "/headers")
    assert final_response
    if status == 302:
        redirected_from = final_response.request.redirected_from
        assert redirected_from
        redirect_response = await redirected_from.response()
        assert redirect_response
        response = redirect_response
    else:
        response = final_response
    assert response.status == status
    await expect_header_fields(response, headers)


async def test_FF_006_should_preserve_synthesized_response_header_fields(
    page: Page, server: Server
) -> None:
    cookies = [
        "a=b; Expires=Wed, 21 Oct 2037 07:28:00 GMT",
        "c=d; Expires=Wed, 21 Oct 2037 07:28:00 GMT; Path=/",
    ]
    await page.route(
        "**/headers",
        lambda route: route.fulfill(
            content_type="text/html",
            headers={
                "X-Literal": 'first, "second, third"',
                "Date": "Wed, 21 Oct 2037 07:28:00 GMT",
                "Set-Cookie": "\n".join(cookies),
                "WWW-Authenticate": 'Digest realm="one, two", qop="auth, auth-int"',
            },
            body="fulfilled",
        ),
    )
    response = await page.goto(server.PREFIX + "/headers")
    assert response
    assert await response.text() == "fulfilled"
    await expect_header_fields(
        response,
        [
            {"name": "x-literal", "value": 'first, "second, third"'},
            {"name": "date", "value": "Wed, 21 Oct 2037 07:28:00 GMT"},
            *[{"name": "set-cookie", "value": value} for value in cookies],
            {
                "name": "www-authenticate",
                "value": 'Digest realm="one, two", qop="auth, auth-int"',
            },
        ],
    )


async def test_FF_007_should_report_current_effective_fields_after_cache_revalidation(
    page: Page, server: Server
) -> None:
    validators: List[Optional[str]] = []

    def add_headers(request: TestServerRequest, headers: Dict[str, Any]) -> None:
        for name, value in headers.items():
            for item in value if isinstance(value, list) else [value]:
                request.responseHeaders.addRawHeader(name, item)

    def handle(request: TestServerRequest) -> None:
        validators.append(request.getHeader("if-none-match"))
        if len(validators) == 1:
            request.setResponseCode(200)
            add_headers(
                request,
                {
                    "Content-Type": "text/plain",
                    "ETag": '"v1"',
                    "Cache-Control": "max-age=0, must-revalidate",
                    "X-Keep": ["first, literal", "second"],
                    "X-Change": ["old, literal", "old-second"],
                    "Set-Cookie": [
                        "old=value; Expires=Wed, 21 Oct 2037 07:28:00 GMT",
                        "old2=value; Path=/",
                    ],
                    "WWW-Authenticate": [
                        'Basic realm="old, realm"',
                        'Basic realm="old-second"',
                    ],
                    "Proxy-Authenticate": [
                        'Basic realm="old, proxy"',
                        'Basic realm="old-proxy-second"',
                    ],
                },
            )
            request.write(b"cached-body")
            request.finish()
            return
        request.setResponseCode(304)
        add_headers(
            request,
            {
                "Cache-Control": "max-age=3600",
                "X-Change": ["new, literal", "new-second"],
                "Set-Cookie": [
                    "new=value; Expires=Wed, 21 Oct 2037 07:28:00 GMT",
                    "new2=value; Path=/",
                ],
                "WWW-Authenticate": [
                    'Basic realm="new, realm"',
                    'Basic realm="new-second"',
                ],
                "Proxy-Authenticate": [
                    'Basic realm="new, proxy"',
                    'Basic realm="new-proxy-second"',
                ],
            },
        )
        request.finish()

    server.set_route("/cached-headers", handle)

    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/cached-headers"
    initial = await fetch_response(page, url)
    revalidated = await fetch_response(page, url)
    cached = await fetch_response(page, url)

    assert validators == [None, '"v1"']
    for _, fetched in [initial, revalidated, cached]:
        assert fetched == {"status": 200, "body": "cached-body"}
    assert [initial[0].status, revalidated[0].status, cached[0].status] == [
        200,
        304,
        200,
    ]
    assert await initial[0].header_value("x-change") == "old, literal, old-second"
    assert await revalidated[0].header_values("x-keep") == []
    assert await revalidated[0].header_values("x-change") == [
        "new, literal",
        "new-second",
    ]
    assert await revalidated[0].header_values("set-cookie") == [
        "new=value; Expires=Wed, 21 Oct 2037 07:28:00 GMT",
        "new2=value; Path=/",
    ]
    assert await revalidated[0].header_values("www-authenticate") == [
        'Basic realm="new, realm"',
        'Basic realm="new-second"',
    ]
    assert await revalidated[0].header_values("proxy-authenticate") == [
        'Basic realm="new, proxy"',
        'Basic realm="new-proxy-second"',
    ]
    assert await cached[0].header_values("x-keep") == ["first, literal, second"]
    assert await cached[0].header_values("x-change") == ["new, literal, new-second"]
    for name in ["set-cookie", "www-authenticate", "proxy-authenticate"]:
        assert await cached[0].header_values(name) == []


async def test_FF_008_should_report_a_standalone_304_response_without_waiting_for_a_cache_merge(
    page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(304)
        request.setHeader("X-Literal", "standalone, value")
        request.setHeader("Cache-Control", "no-store")
        request.finish()

    server.set_route("/standalone-304", handle)
    await page.goto(server.EMPTY_PAGE)
    response, fetched = await fetch_response(page, server.PREFIX + "/standalone-304")
    assert response.status == 304
    assert fetched == {"status": 304, "body": ""}
    assert await response.header_values("x-literal") == ["standalone, value"]
    # Upstream checks that finished() resolves to null; it returns None.
    await response.finished()
