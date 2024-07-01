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

import base64
import json
import pathlib
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import playwright._impl._network as network
from playwright._impl._api_structures import (
    FilePayload,
    FormField,
    Headers,
    HttpCredentials,
    ProxySettings,
    ServerFilePayload,
    StorageState,
)
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._helper import (
    Error,
    NameValue,
    TargetClosedError,
    async_readfile,
    async_writefile,
    is_file_payload,
    locals_to_params,
    object_to_array,
    to_impl,
)
from playwright._impl._network import serialize_headers
from playwright._impl._tracing import Tracing

if typing.TYPE_CHECKING:
    from playwright._impl._playwright import Playwright


FormType = Dict[str, Union[bool, float, str]]
DataType = Union[Any, bytes, str]
MultipartType = Dict[str, Union[bytes, bool, float, str, FilePayload]]
ParamsType = Dict[str, Union[bool, float, str]]


class APIRequest:
    def __init__(self, playwright: "Playwright") -> None:
        self.playwright = playwright
        self._loop = playwright._loop
        self._dispatcher_fiber = playwright._connection._dispatcher_fiber

    async def new_context(
        self,
        baseURL: str = None,
        extraHTTPHeaders: Dict[str, str] = None,
        httpCredentials: HttpCredentials = None,
        ignoreHTTPSErrors: bool = None,
        proxy: ProxySettings = None,
        userAgent: str = None,
        timeout: float = None,
        storageState: Union[StorageState, str, Path] = None,
    ) -> "APIRequestContext":
        params = locals_to_params(locals())
        if "storageState" in params:
            storage_state = params["storageState"]
            if not isinstance(storage_state, dict) and storage_state:
                params["storageState"] = json.loads(
                    (await async_readfile(storage_state)).decode()
                )
        if "extraHTTPHeaders" in params:
            params["extraHTTPHeaders"] = serialize_headers(params["extraHTTPHeaders"])
        context = cast(
            APIRequestContext,
            from_channel(await self.playwright._channel.send("newRequest", params)),
        )
        return context


class APIRequestContext(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._tracing: Tracing = from_channel(initializer["tracing"])
        self._close_reason: Optional[str] = None

    async def dispose(self, reason: str = None) -> None:
        self._close_reason = reason
        try:
            await self._channel.send("dispose", {"reason": reason})
        except Error as e:
            if is_target_closed_error(e):
                return
            raise e
        self._tracing._reset_stack_counter()

    async def delete(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: MultipartType = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="DELETE",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
        )

    async def head(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: MultipartType = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="HEAD",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
        )

    async def get(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: MultipartType = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="GET",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
        )

    async def patch(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="PATCH",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
        )

    async def put(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="PUT",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
        )

    async def post(
        self,
        url: str,
        params: ParamsType = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        return await self.fetch(
            url,
            method="POST",
            params=params,
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            failOnStatusCode=failOnStatusCode,
            ignoreHTTPSErrors=ignoreHTTPSErrors,
            maxRedirects=maxRedirects,
        )

    async def fetch(
        self,
        urlOrRequest: Union[str, network.Request],
        params: ParamsType = None,
        method: str = None,
        headers: Headers = None,
        data: DataType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        url = urlOrRequest if isinstance(urlOrRequest, str) else None
        request = (
            cast(network.Request, to_impl(urlOrRequest))
            if isinstance(to_impl(urlOrRequest), network.Request)
            else None
        )
        assert request or isinstance(
            urlOrRequest, str
        ), "First argument must be either URL string or Request"
        return await self._inner_fetch(
            request,
            url,
            method,
            headers,
            data,
            params,
            form,
            multipart,
            timeout,
            failOnStatusCode,
            ignoreHTTPSErrors,
            maxRedirects,
        )

    async def _inner_fetch(
        self,
        request: Optional[network.Request],
        url: Optional[str],
        method: str = None,
        headers: Headers = None,
        data: DataType = None,
        params: ParamsType = None,
        form: FormType = None,
        multipart: Dict[str, Union[bytes, bool, float, str, FilePayload]] = None,
        timeout: float = None,
        failOnStatusCode: bool = None,
        ignoreHTTPSErrors: bool = None,
        maxRedirects: int = None,
    ) -> "APIResponse":
        if self._close_reason:
            raise TargetClosedError(self._close_reason)
        assert (
            (1 if data else 0) + (1 if form else 0) + (1 if multipart else 0)
        ) <= 1, "Only one of 'data', 'form' or 'multipart' can be specified"
        assert (
            maxRedirects is None or maxRedirects >= 0
        ), "'max_redirects' must be greater than or equal to '0'"
        url = url or (request.url if request else url)
        method = method or (request.method if request else "GET")
        # Cannot call allHeaders() here as the request may be paused inside route handler.
        headers_obj = headers or (request.headers if request else None)
        serialized_headers = serialize_headers(headers_obj) if headers_obj else None
        json_data: Any = None
        form_data: Optional[List[NameValue]] = None
        multipart_data: Optional[List[FormField]] = None
        post_data_buffer: Optional[bytes] = None
        if data is not None:
            if isinstance(data, str):
                if is_json_content_type(serialized_headers):
                    json_data = data if is_json_parsable(data) else json.dumps(data)
                else:
                    post_data_buffer = data.encode()
            elif isinstance(data, bytes):
                post_data_buffer = data
            elif isinstance(data, (dict, list, int, bool)):
                json_data = json.dumps(data)
            else:
                raise Error(f"Unsupported 'data' type: {type(data)}")
        elif form:
            form_data = object_to_array(form)
        elif multipart:
            multipart_data = []
            # Convert file-like values to ServerFilePayload structs.
            for name, value in multipart.items():
                if is_file_payload(value):
                    payload = cast(FilePayload, value)
                    assert isinstance(
                        payload["buffer"], bytes
                    ), f"Unexpected buffer type of 'data.{name}'"
                    multipart_data.append(
                        FormField(name=name, file=file_payload_to_json(payload))
                    )
                elif isinstance(value, str):
                    multipart_data.append(FormField(name=name, value=value))
        if (
            post_data_buffer is None
            and json_data is None
            and form_data is None
            and multipart_data is None
        ):
            post_data_buffer = request.post_data_buffer if request else None
        post_data = (
            base64.b64encode(post_data_buffer).decode() if post_data_buffer else None
        )

        response = await self._channel.send(
            "fetch",
            {
                "url": url,
                "params": object_to_array(params),
                "method": method,
                "headers": serialized_headers,
                "postData": post_data,
                "jsonData": json_data,
                "formData": form_data,
                "multipartData": multipart_data,
                "timeout": timeout,
                "failOnStatusCode": failOnStatusCode,
                "ignoreHTTPSErrors": ignoreHTTPSErrors,
                "maxRedirects": maxRedirects,
            },
        )
        return APIResponse(self, response)

    async def storage_state(
        self, path: Union[pathlib.Path, str] = None
    ) -> StorageState:
        result = await self._channel.send_return_as_dict("storageState")
        if path:
            await async_writefile(path, json.dumps(result))
        return result


def file_payload_to_json(payload: FilePayload) -> ServerFilePayload:
    return ServerFilePayload(
        name=payload["name"],
        mimeType=payload["mimeType"],
        buffer=base64.b64encode(payload["buffer"]).decode(),
    )


class APIResponse:
    def __init__(self, context: APIRequestContext, initializer: Dict) -> None:
        self._loop = context._loop
        self._dispatcher_fiber = context._connection._dispatcher_fiber
        self._request = context
        self._initializer = initializer
        self._headers = network.RawHeaders(initializer["headers"])

    def __repr__(self) -> str:
        return f"<APIResponse url={self.url!r} status={self.status!r} status_text={self.status_text!r}>"

    @property
    def ok(self) -> bool:
        return self.status >= 200 and self.status <= 299

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def status(self) -> int:
        return self._initializer["status"]

    @property
    def status_text(self) -> str:
        return self._initializer["statusText"]

    @property
    def headers(self) -> Headers:
        return self._headers.headers()

    @property
    def headers_array(self) -> network.HeadersArray:
        return self._headers.headers_array()

    async def body(self) -> bytes:
        try:
            result = await self._request._channel.send_return_as_dict(
                "fetchResponseBody",
                {
                    "fetchUid": self._fetch_uid,
                },
            )
            if result is None:
                raise Error("Response has been disposed")
            return base64.b64decode(result["binary"])
        except Error as exc:
            if is_target_closed_error(exc):
                raise Error("Response has been disposed")
            raise exc

    async def text(self) -> str:
        content = await self.body()
        return content.decode()

    async def json(self) -> Any:
        content = await self.text()
        return json.loads(content)

    async def dispose(self) -> None:
        await self._request._channel.send(
            "disposeAPIResponse",
            {
                "fetchUid": self._fetch_uid,
            },
        )

    @property
    def _fetch_uid(self) -> str:
        return self._initializer["fetchUid"]

    async def _fetch_log(self) -> List[str]:
        return await self._request._channel.send(
            "fetchLog",
            {
                "fetchUid": self._fetch_uid,
            },
        )


def is_json_content_type(headers: network.HeadersArray = None) -> bool:
    if not headers:
        return False
    for header in headers:
        if header["name"] == "Content-Type":
            return header["value"].startswith("application/json")
    return False


def is_json_parsable(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False
