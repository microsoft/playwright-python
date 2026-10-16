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
import asyncio
import base64
from typing import TYPE_CHECKING, Optional

from playwright._impl._errors import Error
from playwright._impl._helper import (
    RouteFromHarNotFoundPolicy,
    URLMatch,
    create_task_and_ignore_exception,
)
from playwright._impl._local_utils import LocalUtils

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._network import Route
    from playwright._impl._page import Page


class HarRouter:
    def __init__(
        self,
        local_utils: LocalUtils,
        har_id: str,
        not_found_action: RouteFromHarNotFoundPolicy,
        url_matcher: Optional[URLMatch] = None,
    ) -> None:
        self._local_utils: LocalUtils = local_utils
        self._har_id: str = har_id
        self._not_found_action: RouteFromHarNotFoundPolicy = not_found_action
        self._options_url_match: Optional[URLMatch] = url_matcher

    @staticmethod
    async def create(
        local_utils: LocalUtils,
        file: str,
        not_found_action: RouteFromHarNotFoundPolicy,
        url_matcher: Optional[URLMatch] = None,
    ) -> "HarRouter":
        result = await local_utils._channel.harOpen(file=file)
        if result["error"]:
            raise Error(result["error"])
        har_id = result["harId"]
        if har_id is None:
            raise Error("harOpen returned no HAR id")
        return HarRouter(
            local_utils=local_utils,
            har_id=har_id,
            not_found_action=not_found_action,
            url_matcher=url_matcher,
        )

    async def _handle(self, route: "Route") -> None:
        request = route.request
        response = await self._local_utils.har_lookup(
            har_id=self._har_id,
            url=request.url,
            method=request.method,
            headers=await request.headers_array(),
            post_data=request.post_data_buffer,
            is_navigation_request=request.is_navigation_request(),
        )
        action = response["action"]
        if action == "redirect":
            redirect_url = response["redirectURL"]
            assert redirect_url
            await route._redirected_navigation_request(redirect_url)
            return

        if action == "fulfill":
            # If the response status is -1, the request was canceled or stalled, so we just stall it here.
            # See https://github.com/microsoft/playwright/issues/29311.
            # TODO: it'd be better to abort such requests, but then we likely need to respect the timing,
            # because the request might have been stalled for a long time until the very end of the
            # test when HAR was recorded but we'd abort it immediately.
            if response["status"] == -1:
                return
            body = response["body"]
            assert body is not None
            await route.fulfill(
                status=response["status"],
                headers={v["name"]: v["value"] for v in response["headers"] or []},
                body=base64.b64decode(body),
                json=None,
                path=None,
                content_type=None,
                response=None,
            )
            return

        if action == "error":
            pass
        # Report the error, but fall through to the default handler.

        if self._not_found_action == "abort":
            await route.abort(error_code=None)
            return

        await route.fallback(url=None, method=None, headers=None, post_data=None)

    async def add_context_route(self, context: "BrowserContext") -> None:
        await context.route(
            url=self._options_url_match or "**/*",
            handler=lambda route, _: asyncio.create_task(self._handle(route)),
            times=None,
        )

    async def add_page_route(self, page: "Page") -> None:
        await page.route(
            url=self._options_url_match or "**/*",
            handler=lambda route, _: asyncio.create_task(self._handle(route)),
            times=None,
        )

    def dispose(self) -> None:
        create_task_and_ignore_exception(
            self._local_utils._loop,
            self._local_utils._channel.harClose(harId=self._har_id),
        )
