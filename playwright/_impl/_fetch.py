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
import mimetypes
import pathlib
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Sequence, Union, cast

import playwright._impl._network as network
from playwright._impl._api_structures import (
    ClientCertificate,
    Cookie,
    FilePayload,
    HttpCredentials,
    ProxySettings,
    RemoteAddr,
    ResourceTiming,
    SecurityDetails,
    SetCookieParam,
    StorageState,
)
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import Error, TargetClosedError, is_target_closed_error
from playwright._impl._form_data import FormData
from playwright._impl._headers import serialize_headers
from playwright._impl._helper import (
    async_readfile,
    async_writefile,
    is_file_payload,
    to_impl,
)
from playwright._impl._internal_structures import Headers, NameValue
from playwright._impl._network import (
    to_client_certificates_protocol,
    to_http_credentials_protocol,
)
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._timeout_settings import TimeoutSettings
from playwright._impl._tracing import Tracing

if typing.TYPE_CHECKING:  # pragma: no cover
    from playwright._impl import _protocol_types as channels
    from playwright._impl._playwright import Playwright
    from playwright._impl._protocol_channels import APIRequestContextChannel


FormType = Union[Dict[str, Union[bool, float, str]], FormData]
DataType = Union[Any, bytes, str]
MultipartType = Union[Dict[str, Union[bytes, bool, float, str, FilePayload]], FormData]
ParamsType = Union[Dict[str, Union[bool, float, str]], str]


class APIRequest:
    def __init__(self, playwright: "Playwright") -> None:
        self.playwright = playwright
        self._loop = playwright._loop
        self._dispatcher_fiber = playwright._connection._dispatcher_fiber

    async def new_context(
        self,
        base_url: Optional[str],
        extra_http_headers: Optional[Dict[str, str]],
        http_credentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
        ignore_https_errors: Optional[bool],
        proxy: Optional[ProxySettings],
        user_agent: Optional[str],
        timeout: Optional[float],
        storage_state: Optional[Union[StorageState, str, Path]],
        client_certificates: Optional[List[ClientCertificate]],
        fail_on_status_code: Optional[bool],
        max_redirects: Optional[int],
    ) -> "APIRequestContext":
        if storage_state and not isinstance(storage_state, dict):
            storage_state = json.loads((await async_readfile(storage_state)).decode())
        result = await self.playwright._channel.newRequest(
            baseURL=base_url,
            userAgent=user_agent,
            ignoreHTTPSErrors=ignore_https_errors,
            extraHTTPHeaders=(
                serialize_headers(extra_http_headers)
                if extra_http_headers is not None
                else None
            ),
            failOnStatusCode=fail_on_status_code,
            clientCertificates=cast(
                "Optional[List[channels.PlaywrightNewRequestParamsClientCertificates]]",
                await to_client_certificates_protocol(client_certificates),
            ),
            maxRedirects=max_redirects,
            httpCredentials=cast(
                "Optional[List[channels.HttpCredentials]]",
                to_http_credentials_protocol(http_credentials),
            ),
            proxy=cast("Optional[channels.PlaywrightNewRequestParamsProxy]", proxy),
            storageState=cast(
                "Optional[channels.PlaywrightNewRequestParamsStorageState]",
                storage_state,
            ),
            tracesDir=None,
        )
        context = cast(APIRequestContext, from_channel(result["request"]))
        context._timeout_settings.set_default_timeout(timeout)
        return context


class APIRequestContext(ChannelOwner):
    _channel: "APIRequestContextChannel"

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._tracing: Tracing = from_channel(initializer["tracing"])
        self._close_reason: Optional[str] = None
        self._timeout_settings = TimeoutSettings(None)

    async def dispose(self, reason: Optional[str]) -> None:
        self._close_reason = reason
        await self._tracing._export_all_hars()
        try:
            await self._channel.dispose(reason=reason)
        except Error as e:
            if is_target_closed_error(e):
                return
            raise e
        self._tracing._reset_stack_counter()

    @property
    def tracing(self) -> Tracing:
        return self._tracing

    async def cookies(self, urls: Optional[Union[str, Sequence[str]]]) -> List[Cookie]:
        if urls is None:
            urls = []
        if isinstance(urls, str):
            urls = [urls]
        return cast(List[Cookie], (await self._channel.cookies(urls=urls))["cookies"])

    async def add_cookies(self, cookies: Sequence[SetCookieParam]) -> None:
        await self._channel.addCookies(
            cookies=cast("Sequence[channels.SetNetworkCookie]", cookies)
        )

    async def clear_cookies(
        self,
        name: Optional[Union[str, Pattern[str]]],
        domain: Optional[Union[str, Pattern[str]]],
        path: Optional[Union[str, Pattern[str]]],
    ) -> None:
        await self._channel.clearCookies(
            name=name if isinstance(name, str) else None,
            nameRegexSource=name.pattern if isinstance(name, Pattern) else None,
            nameRegexFlags=(
                escape_regex_flags(name) if isinstance(name, Pattern) else None
            ),
            domain=domain if isinstance(domain, str) else None,
            domainRegexSource=domain.pattern if isinstance(domain, Pattern) else None,
            domainRegexFlags=(
                escape_regex_flags(domain) if isinstance(domain, Pattern) else None
            ),
            path=path if isinstance(path, str) else None,
            pathRegexSource=path.pattern if isinstance(path, Pattern) else None,
            pathRegexFlags=(
                escape_regex_flags(path) if isinstance(path, Pattern) else None
            ),
        )

    async def delete(
        self,
        url: str,
        params: Optional[ParamsType],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        return await self.fetch(
            url_or_request=url,
            params=params,
            method="DELETE",
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def head(
        self,
        url: str,
        params: Optional[ParamsType],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        return await self.fetch(
            url_or_request=url,
            params=params,
            method="HEAD",
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def get(
        self,
        url: str,
        params: Optional[ParamsType],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        return await self.fetch(
            url_or_request=url,
            params=params,
            method="GET",
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def patch(
        self,
        url: str,
        params: Optional[ParamsType],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        return await self.fetch(
            url_or_request=url,
            params=params,
            method="PATCH",
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def put(
        self,
        url: str,
        params: Optional[ParamsType],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        return await self.fetch(
            url_or_request=url,
            params=params,
            method="PUT",
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def post(
        self,
        url: str,
        params: Optional[ParamsType],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        return await self.fetch(
            url_or_request=url,
            params=params,
            method="POST",
            headers=headers,
            data=data,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def fetch(
        self,
        url_or_request: Union[str, network.Request],
        params: Optional[ParamsType],
        method: Optional[str],
        headers: Optional[Headers],
        data: Optional[DataType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        url = url_or_request if isinstance(url_or_request, str) else None
        request = (
            cast(network.Request, to_impl(url_or_request))
            if isinstance(to_impl(url_or_request), network.Request)
            else None
        )
        if not request and not isinstance(url_or_request, str):
            raise Error("First argument must be either URL string or Request")
        return await self._inner_fetch(
            request=request,
            url=url,
            method=method,
            headers=headers,
            data=data,
            params=params,
            form=form,
            multipart=multipart,
            timeout=timeout,
            fail_on_status_code=fail_on_status_code,
            ignore_https_errors=ignore_https_errors,
            max_redirects=max_redirects,
            max_retries=max_retries,
        )

    async def _inner_fetch(
        self,
        request: Optional[network.Request],
        url: Optional[str],
        method: Optional[str],
        headers: Optional[Headers],
        data: Optional[DataType],
        params: Optional[ParamsType],
        form: Optional[FormType],
        multipart: Optional[MultipartType],
        timeout: Optional[float],
        fail_on_status_code: Optional[bool],
        ignore_https_errors: Optional[bool],
        max_redirects: Optional[int],
        max_retries: Optional[int],
    ) -> "APIResponse":
        if self._close_reason:
            raise TargetClosedError(self._close_reason)
        if (
            (1 if data is not None else 0)
            + (1 if form is not None else 0)
            + (1 if multipart is not None else 0)
        ) > 1:
            raise Error("Only one of 'data', 'form' or 'multipart' can be specified")
        if max_redirects is not None and max_redirects < 0:
            raise Error("'max_redirects' must be greater than or equal to '0'")
        if max_retries is not None and max_retries < 0:
            raise Error("'max_retries' must be greater than or equal to '0'")
        url = url or (request.url if request else url)
        assert url is not None
        method = method or (request.method if request else "GET")
        # Cannot call allHeaders() here as the request may be paused inside route handler.
        headers_obj = headers or (request.headers if request else None)
        serialized_headers = serialize_headers(headers_obj) if headers_obj else None
        json_data: Any = None
        form_data: Optional[List[NameValue]] = None
        multipart_data: Optional[List[channels.FormField]] = None
        post_data_buffer: Optional[bytes] = None
        if data is not None:
            if isinstance(data, str):
                if is_json_content_type(serialized_headers):
                    json_data = data if is_json_parsable(data) else json.dumps(data)
                else:
                    post_data_buffer = data.encode()
            elif isinstance(data, bytes):
                post_data_buffer = data
            elif isinstance(data, (dict, list, int, float, bool)):
                try:
                    # NaN and Infinity are not valid JSON.
                    json_data = json.dumps(data, allow_nan=False)
                except ValueError as e:
                    raise Error(str(e)) from None
            else:
                raise Error(f"Unsupported 'data' type: {type(data)}")
        elif form is not None:
            if isinstance(form, FormData):
                form_data = []
                for fd_name, fd_value in form._fields:
                    if isinstance(fd_value, (pathlib.Path, dict)):
                        raise Error(
                            f"Form field {fd_name!r} must be a string, number or boolean. Use 'multipart' for file uploads."
                        )
                    form_data.append(NameValue(name=fd_name, value=str(fd_value)))
            else:
                form_data = object_to_array(form) or []
        elif multipart is not None:
            multipart_data = []
            if isinstance(multipart, FormData):
                for fd_name, fd_value in multipart._fields:
                    multipart_data.append(
                        await _form_data_field_to_form_field(fd_name, fd_value)
                    )
            else:
                for name, value in multipart.items():
                    multipart_data.append(
                        await _form_data_field_to_form_field(name, value)
                    )
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

        result = await self._channel.fetch(
            url=url,
            encodedParams=params if isinstance(params, str) else None,
            params=object_to_array(params) if isinstance(params, dict) else None,
            method=method,
            headers=serialized_headers,
            postData=post_data,
            jsonData=json_data,
            formData=form_data,
            multipartData=multipart_data,
            failOnStatusCode=fail_on_status_code,
            ignoreHTTPSErrors=ignore_https_errors,
            maxRedirects=max_redirects,
            maxRetries=max_retries,
            timeout=self._timeout_settings.timeout(timeout),
        )
        return APIResponse(self, cast(Dict, result["response"]))

    async def storage_state(
        self,
        path: Optional[Union[pathlib.Path, str]],
        indexed_db: Optional[bool],
        opfs: Optional[bool],
    ) -> StorageState:
        result = cast(
            StorageState,
            await self._channel.storageState(indexedDB=indexed_db, opfs=opfs),
        )
        if path:
            await async_writefile(path, json.dumps(result))
        return result


def object_to_array(obj: Optional[Dict]) -> Optional[List[NameValue]]:
    if not obj:
        return None
    result = []
    for key, value in obj.items():
        result.append(NameValue(name=key, value=str(value)))
    return result


def file_payload_to_json(payload: FilePayload) -> "channels.FormFieldFile":
    return {
        "name": payload["name"],
        "mimeType": payload["mimeType"],
        "buffer": base64.b64encode(payload["buffer"]).decode(),
    }


async def _form_data_field_to_form_field(name: str, value: Any) -> "channels.FormField":
    if isinstance(value, pathlib.Path):
        mime_type, _ = mimetypes.guess_type(str(value))
        return {
            "name": name,
            "file": {
                "name": value.name,
                "mimeType": mime_type or "application/octet-stream",
                "buffer": base64.b64encode(await async_readfile(str(value))).decode(),
            },
        }
    if is_file_payload(value):
        payload = cast(FilePayload, value)
        if not isinstance(payload["buffer"], bytes):
            raise Error(f"Unexpected buffer type of form field {name!r}")
        return {"name": name, "file": file_payload_to_json(payload)}
    if isinstance(value, (str, int, float, bool)):
        return {"name": name, "value": str(value)}
    raise Error(f"Unsupported form field {name!r} value type: {type(value).__name__}")


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

    @property
    def timing(self) -> ResourceTiming:
        return cast(
            ResourceTiming,
            {
                "startTime": -1,
                "domainLookupStart": -1,
                "domainLookupEnd": -1,
                "connectStart": -1,
                "secureConnectionStart": -1,
                "connectEnd": -1,
                "requestStart": -1,
                "responseStart": -1,
                **self._initializer.get("timing", {}),
                "responseEnd": self._initializer.get("responseEndTiming", -1),
            },
        )

    async def body(self) -> bytes:
        try:
            result = await self._request._connection.wrap_api_call(
                lambda: self._request._channel.fetchResponseBody(
                    fetchUid=self._fetch_uid
                ),
                is_internal=True,
            )
            if result["binary"] is None:
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

    async def security_details(self) -> Optional[SecurityDetails]:
        return self._initializer.get("securityDetails") or None

    async def server_addr(self) -> Optional[RemoteAddr]:
        return self._initializer.get("serverAddr") or None

    async def dispose(self) -> None:
        await self._request._channel.disposeAPIResponse(fetchUid=self._fetch_uid)

    @property
    def _fetch_uid(self) -> str:
        return self._initializer["fetchUid"]

    async def _fetch_log(self) -> List[str]:
        return (await self._request._channel.fetchLog(fetchUid=self._fetch_uid))["log"]


def is_json_content_type(headers: network.HeadersArray = None) -> bool:
    if not headers:
        return False
    for header in headers:
        if header["name"].lower() == "content-type":
            return header["value"].startswith("application/json")
    return False


def is_json_parsable(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        # NaN and Infinity are not valid JSON, unlike what json.loads() accepts by default.
        json.loads(value, parse_constant=_reject_json_constant)
        return True
    except ValueError:
        return False


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"{value} is not valid JSON")
