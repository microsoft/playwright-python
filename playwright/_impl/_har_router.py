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

"""Port of packages/playwright-core/src/client/harRouter.ts."""

import base64
from typing import TYPE_CHECKING, Dict, Literal, Optional, cast

from playwright._impl._errors import Error
from playwright._impl._helper import create_task_and_ignore_exception
from playwright._impl._local_utils import LocalUtils
from playwright._impl._url_match import URLMatch

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._network import Route
    from playwright._impl._page import Page

HarNotFoundAction = Literal["abort", "fallback"]


class HarRouter:
    def __init__(
        self,
        local_utils: LocalUtils,
        har_id: str,
        not_found_action: HarNotFoundAction,
        url_match: Optional[URLMatch],
    ) -> None:
        self._local_utils: LocalUtils = local_utils
        self._har_id: str = har_id
        self._not_found_action: HarNotFoundAction = not_found_action
        self._url_match: Optional[URLMatch] = url_match

    @staticmethod
    async def create(
        local_utils: LocalUtils,
        file: str,
        not_found_action: HarNotFoundAction,
        url_match: Optional[URLMatch],
    ) -> "HarRouter":
        result = await local_utils.har_open(file)
        if result["error"]:
            raise Error(result["error"])
        return HarRouter(
            local_utils=local_utils,
            har_id=cast(str, result["harId"]),
            not_found_action=not_found_action,
            url_match=url_match,
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
        if response["action"] == "redirect":
            await route._redirect_navigation_request(cast(str, response["redirectURL"]))
            return

        if response["action"] == "fulfill":
            # If the response status is -1, the request was canceled or stalled, so we just stall it here.
            # See https://github.com/microsoft/playwright/issues/29311.
            # TODO: it'd be better to abort such requests, but then we likely need to respect the timing,
            # because the request might have been stalled for a long time until the very end of the
            # test when HAR was recorded but we'd abort it immediately.
            if response["status"] == -1:
                return
            # route.fulfill does not support multiple set-cookie headers. We need to merge them into one.
            transformed_headers: Dict[str, str] = {}
            for header in response["headers"] or []:
                name, value = header["name"], header["value"]
                if name.lower() != "set-cookie":
                    # non-set-cookie header gets set as-is
                    transformed_headers[name] = value
                elif "set-cookie" not in transformed_headers:
                    # first set-cookie header gets included as-is
                    transformed_headers["set-cookie"] = value
                else:
                    # subsequent set-cookie headers get appended to existing header
                    transformed_headers["set-cookie"] += f"\n{value}"
            await route.fulfill(
                status=response["status"],
                headers=transformed_headers,
                body=base64.b64decode(cast(str, response["body"])),
                json=None,
                path=None,
                content_type=None,
                response=None,
            )
            return

        # Upstream logs the "error" action with the debug logger, which Python does not have.
        # Report the error, but fall through to the default handler.

        if self._not_found_action == "abort":
            await route.abort(error_code=None)
            return

        await route.fallback(url=None, method=None, headers=None, post_data=None)

    async def add_context_route(self, context: "BrowserContext") -> None:
        await context.route(
            url=self._url_match or "**/*",
            handler=lambda route, _: self._handle(route),
            times=None,
        )

    async def add_page_route(self, page: "Page") -> None:
        await page.route(
            url=self._url_match or "**/*",
            handler=lambda route, _: self._handle(route),
            times=None,
        )

    def dispose(self) -> None:
        create_task_and_ignore_exception(
            self._local_utils._loop,
            self._local_utils.har_close(self._har_id),
        )
