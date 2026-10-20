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

"""Port of packages/playwright-core/src/client/harRouter.ts.

Python: the options object { urlMatch } is the url_match parameter. The post data
and the body are base64 strings on the wire. [Symbol.asyncDispose]() is not ported.
"""

import base64
from typing import TYPE_CHECKING, Dict, Literal, Optional, cast

from playwright._impl._errors import Error
from playwright._impl_v2.isomorphic.url_match import URLMatch
from playwright._impl_v2.utils.debug_logger import debug_logger
from playwright._impl_v2.utils.tasks import fire_and_forget

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2.browser_context import BrowserContext
    from playwright._impl_v2.local_utils import LocalUtils
    from playwright._impl_v2.network import Route
    from playwright._impl_v2.page import Page

HarNotFoundAction = Literal["abort", "fallback"]


class HarRouter:
    @staticmethod
    async def create(
        local_utils: "LocalUtils",
        file: str,
        not_found_action: HarNotFoundAction,
        url_match: Optional[URLMatch],
    ) -> "HarRouter":
        result = await local_utils.har_open({"file": file})
        har_id, error = result["harId"], result["error"]
        if error:
            raise Error(error)
        return HarRouter(local_utils, cast(str, har_id), not_found_action, url_match)

    def __init__(
        self,
        local_utils: "LocalUtils",
        har_id: str,
        not_found_action: HarNotFoundAction,
        url_match: Optional[URLMatch],
    ) -> None:
        self._local_utils: "LocalUtils" = local_utils
        self._har_id: str = har_id
        # Python: the urlMatch of the options; baseURL is never set.
        self._url_match: Optional[URLMatch] = url_match
        self._not_found_action: HarNotFoundAction = not_found_action

    async def _handle(self, route: "Route") -> None:
        request = route.request

        post_data_buffer = request.post_data_buffer
        response = await self._local_utils.har_lookup(
            {
                "harId": self._har_id,
                "url": request.url,
                "method": request.method,
                "headers": (await request.headers_array()),
                # Python: binary is base64 on the wire; an empty buffer is a value.
                "postData": (
                    base64.b64encode(post_data_buffer).decode()
                    if post_data_buffer is not None
                    else None
                ),
                "isNavigationRequest": request.is_navigation_request(),
            }
        )

        if response["action"] == "redirect":
            debug_logger.log(
                "api",
                f"HAR: {route.request.url} redirected to {response['redirectURL']}",
            )
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
            # Python: the reduce() is a loop.
            transformed_headers: Dict[str, str] = {}
            for header in response["headers"] or []:
                name, value = header["name"], header["value"]
                if name.lower() != "set-cookie":
                    # non-set-cookie header gets set as-is
                    transformed_headers[name] = value
                else:
                    # first set-cookie header gets included as-is
                    if not transformed_headers.get("set-cookie"):
                        transformed_headers["set-cookie"] = value
                    else:
                        # subsequent set-cookie headers get appended to existing header
                        transformed_headers["set-cookie"] += f"\n{value}"

            await route.fulfill(
                response=None,
                status=response["status"],
                headers=transformed_headers,
                content_type=None,
                # Python: binary is base64 on the wire.
                body=base64.b64decode(cast(str, response["body"])),
                json=None,
                path=None,
            )
            return

        if response["action"] == "error":
            debug_logger.log("api", "HAR: " + cast(str, response["message"]))
        # Report the error, but fall through to the default handler.

        if self._not_found_action == "abort":
            await route.abort(error_code=None)
            return

        await route.fallback(url=None, method=None, headers=None, post_data=None)

    async def add_context_route(self, context: "BrowserContext") -> None:
        # Python: a handler takes every argument that it is called with.
        await context.route(
            url=self._url_match or "**/*",
            handler=lambda route, _: self._handle(route),
            times=None,
        )

    async def add_page_route(self, page: "Page") -> None:
        # Python: a handler takes every argument that it is called with.
        await page.route(
            url=self._url_match or "**/*",
            handler=lambda route, _: self._handle(route),
            times=None,
        )

    # Not ported: [Symbol.asyncDispose]() is JavaScript only.

    def dispose(self) -> None:
        # Python: har_close() is an async def, so the message goes out when its task
        # runs, not at once.
        fire_and_forget(self._local_utils.har_close({"harId": self._har_id}))
