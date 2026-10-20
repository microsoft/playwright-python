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

"""Port of packages/playwright-core/src/client/fetch.ts.

Python:
- The options objects are the keyword arguments that the generated API passes. The
  options of new_context() are put in a dict, so that the instrumentation can change
  them, as it changes the options object upstream.
- ok, url, status, status_text, headers, headers_array and timing of APIResponse
  are properties, as the generated API reads them.
- params is a dict or a str: there is no URLSearchParams. FormData is the class of
  playwright/_impl/_form_data.py; its values are strings, numbers, bools, Paths and
  FilePayloads, not Files. A pathlib.Path is the counterpart of an fs.ReadStream.
- A binary is base64 on the channel.
- `x || y` and `!x` on an object are None checks: an empty dict is truthy in JS.
- assert(value, message) throws an Error with the message; here it is a raise.
- JSON.stringify() is _json_stringify(), which raises for NaN and Infinity, where
  JSON.stringify() writes null.
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    TypeVar,
    Union,
    cast,
)

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
from playwright._impl._errors import Error
from playwright._impl._form_data import FormData
from playwright._impl_v2.channel_owner import (
    ApiCallOptions,
    ChannelOwner,
    api_call,
    from_channel,
    internal,
)
from playwright._impl_v2.errors import TargetClosedError, is_target_closed_error
from playwright._impl_v2.file_utils import mkdir_if_needed
from playwright._impl_v2.internal_structures import Headers, HeadersArray, NameValue
from playwright._impl_v2.isomorphic.headers import headers_object_to_array
from playwright._impl_v2.isomorphic.string_utils import js_string
from playwright._impl_v2.timeout_settings import NO_TIMEOUT, TimeoutSettings
from playwright._impl_v2.tracing import Tracing

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl_v2 import protocol_types as channels
    from playwright._impl_v2.channel_owner import ApiZone
    from playwright._impl_v2.network import Request
    from playwright._impl_v2.playwright import Playwright
    from playwright._impl_v2.protocol_channels import APIRequestContextChannel

R = TypeVar("R")

# Python: the types of the options, as the generated API passes them.
ParamsType = Union[Dict[str, Union[str, float, bool]], str]
DataType = Union[str, bytes, Any]
FormType = Union[Dict[str, Union[str, float, bool]], FormData]
MultipartType = Union[
    Dict[str, Union[str, float, bool, bytes, Path, FilePayload]], FormData
]


class APIRequest:
    def __init__(self, playwright: "Playwright") -> None:
        self._playwright = playwright
        self._contexts: Set["APIRequestContext"] = set()
        # Python: the generated API reads the event loop of each object.
        self._loop = playwright._loop

    async def new_context(
        self,
        base_url: Optional[str],
        user_agent: Optional[str],
        ignore_https_errors: Optional[bool],
        extra_http_headers: Optional[Dict[str, str]],
        fail_on_status_code: Optional[bool],
        client_certificates: Optional[Sequence[ClientCertificate]],
        max_redirects: Optional[int],
        http_credentials: Optional[Union[HttpCredentials, Sequence[HttpCredentials]]],
        proxy: Optional[ProxySettings],
        storage_state: Optional[Union[StorageState, str, Path]],
        timeout: Optional[float],
    ) -> "APIRequestContext":
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.browser_context import (
            to_client_certificates_protocol,
            to_http_credentials_protocol,
        )

        # Python: `options = { ...options }`, with the Python names of the options.
        options: Dict[str, Any] = {
            "base_url": base_url,
            "user_agent": user_agent,
            "ignore_https_errors": ignore_https_errors,
            "extra_http_headers": extra_http_headers,
            "fail_on_status_code": fail_on_status_code,
            "client_certificates": client_certificates,
            "max_redirects": max_redirects,
            "http_credentials": http_credentials,
            "proxy": proxy,
            "storage_state": storage_state,
            "timeout": timeout,
        }
        await self._playwright._instrumentation.run_before_create_request_context(
            options
        )
        # Python: the path can be a pathlib.Path.
        storage_state = (
            json.loads(await _read_file(options["storage_state"]))
            if isinstance(options.get("storage_state"), (str, Path))
            else options.get("storage_state")
        )
        default_launch_options = self._playwright._default_launch_options
        context = APIRequestContext.from_(
            (
                await self._playwright._channel.newRequest(
                    baseURL=options.get("base_url"),
                    userAgent=options.get("user_agent"),
                    ignoreHTTPSErrors=options.get("ignore_https_errors"),
                    extraHTTPHeaders=(
                        headers_object_to_array(options["extra_http_headers"])
                        if options.get("extra_http_headers") is not None
                        else None
                    ),
                    failOnStatusCode=options.get("fail_on_status_code"),
                    clientCertificates=await to_client_certificates_protocol(
                        options.get("client_certificates")
                    ),
                    maxRedirects=options.get("max_redirects"),
                    httpCredentials=to_http_credentials_protocol(
                        options.get("http_credentials")
                    ),
                    proxy=cast(
                        "Optional[channels.PlaywrightNewRequestParamsProxy]",
                        options.get("proxy"),
                    ),
                    storageState=cast(
                        "Optional[channels.PlaywrightNewRequestParamsStorageState]",
                        storage_state,
                    ),
                    # We do not expose tracesDir in the API, so do not allow options to accidentally override it.
                    tracesDir=(
                        default_launch_options.get("traces_dir")
                        if default_launch_options
                        else None
                    ),
                    timeout=NO_TIMEOUT,
                )
            )["request"]
        )
        self._contexts.add(context)
        context._request = self
        context_timeout = options.get("timeout")
        context._timeout_settings.set_default_timeout(
            context_timeout
            if context_timeout is not None
            else self._playwright._default_context_timeout
        )
        context.tracing._traces_dir = (
            default_launch_options.get("traces_dir") if default_launch_options else None
        )
        await context._instrumentation.run_after_create_request_context(context)
        return context


class APIRequestContext(ChannelOwner):
    _channel: "APIRequestContextChannel"

    @staticmethod
    def from_(channel: "APIRequestContextChannel") -> "APIRequestContext":
        return from_channel(channel)

    def __init__(
        self,
        parent: ChannelOwner,
        type: str,
        guid: str,
        initializer: "channels.APIRequestContextInitializer",
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._request: Optional[APIRequest] = None
        self.tracing: Tracing = Tracing.from_(initializer["tracing"])
        self._close_reason: Optional[str] = None
        self._timeout_settings = TimeoutSettings()

    # Not ported: [Symbol.asyncDispose](); the Python APIRequestContext is not an
    # async context manager.

    async def dispose(self, reason: Optional[str]) -> None:
        self._close_reason = reason
        await self._instrumentation.run_before_close_request_context(self)
        await self.tracing._export_all_hars()
        try:
            await self._channel.dispose(reason=reason, timeout=NO_TIMEOUT)
        except Exception as e:
            if is_target_closed_error(e):
                return
            raise e
        self.tracing._reset_stack_counter()
        if self._request:
            self._request._contexts.discard(self)

    async def cookies(self, urls: Optional[Union[str, Sequence[str]]]) -> List[Cookie]:
        if not urls:
            urls = []
        if isinstance(urls, str):
            urls = [urls]
        return cast(
            List[Cookie],
            (await self._channel.cookies(urls=urls, timeout=NO_TIMEOUT))["cookies"],
        )

    async def add_cookies(self, cookies: Sequence[SetCookieParam]) -> None:
        await self._channel.addCookies(
            cookies=cast("Sequence[channels.SetNetworkCookie]", cookies),
            timeout=NO_TIMEOUT,
        )

    async def clear_cookies(
        self,
        name: Optional[Union[str, Pattern[str]]],
        domain: Optional[Union[str, Pattern[str]]],
        path: Optional[Union[str, Pattern[str]]],
    ) -> None:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.network import to_clear_cookies_params

        await self._channel.clearCookies(
            **to_clear_cookies_params(name=name, domain=domain, path=path),
            timeout=NO_TIMEOUT,
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

    @api_call()
    async def fetch(
        self,
        url_or_request: Union[str, "Request"],
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
        request = None if isinstance(url_or_request, str) else url_or_request
        return await self._inner_fetch(
            url=url,
            request=request,
            params=params,
            method=method,
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

    async def _inner_fetch(
        self,
        url: Optional[str],
        request: Optional["Request"],
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
        if self._close_reason:
            raise TargetClosedError(self._close_reason)
        # Python: each assert(value, message) raises an Error with the message.
        if not (request or isinstance(url, str)):
            raise Error("First argument must be either URL string or Request")
        if (
            (0 if data is None else 1)
            + (0 if form is None else 1)
            + (0 if multipart is None else 1)
        ) > 1:
            raise Error("Only one of 'data', 'form' or 'multipart' can be specified")
        if not (max_redirects is None or max_redirects >= 0):
            # Python: the message names the Python option, max_redirects.
            raise Error("'max_redirects' must be greater than or equal to '0'")
        if not (max_retries is None or max_retries >= 0):
            # Python: the message names the Python option, max_retries.
            raise Error("'max_retries' must be greater than or equal to '0'")
        url = url if url is not None else cast("Request", request).url
        method = method or (request.method if request else None)
        encoded_params = None
        if isinstance(params, str):
            encoded_params = params
        # Not ported: the URLSearchParams form of params; Python has no URLSearchParams.
        # Cannot call allHeaders() here as the request may be paused inside route handler.
        headers_obj = (
            headers if headers is not None else (request.headers if request else None)
        )
        headers_array = (
            headers_object_to_array(headers_obj) if headers_obj is not None else None
        )
        json_data: Any = None
        form_data: Optional[List[NameValue]] = None
        multipart_data: Optional[List["channels.FormField"]] = None
        post_data_buffer: Optional[bytes] = None
        # Python: one type for the loop variables of the branches below, as each JS
        # loop has its own block scope.
        name: str
        value: Any
        if data is not None:
            if isinstance(data, str):
                if is_json_content_type(headers_array):
                    json_data = (
                        data if is_json_parsable(data) else _json_stringify(data)
                    )
                else:
                    post_data_buffer = data.encode("utf-8")
            elif isinstance(data, bytes):
                post_data_buffer = data
            # Python: typeof 'object', 'number' or 'boolean'.
            elif isinstance(data, (dict, list, int, float, bool)):
                try:
                    json_data = _json_stringify(data)
                except ValueError as e:
                    # Python: NaN and Infinity raise; JSON.stringify() writes null.
                    raise Error(str(e)) from None
            else:
                raise Error("Unexpected 'data' type")
        elif form is not None:
            if isinstance(form, FormData):
                form_data = []
                for name, value in form._fields:
                    # Python: a number or a bool in a FormData is a string, as
                    # FormData.append() converts it upstream.
                    if not isinstance(value, (str, int, float, bool)):
                        raise Error(
                            f'Expected string for options.form["{name}"], found File. Please use options.multipart instead.'
                        )
                    form_data.append({"name": name, "value": js_string(value)})
            else:
                form_data = object_to_array(form)
        elif multipart is not None:
            multipart_data = []
            if isinstance(multipart, FormData):
                form_ = multipart
                for name, value in form_._fields:
                    if isinstance(value, str):
                        multipart_data.append({"name": name, "value": value})
                    else:
                        # Python: the other values of a FormData are numbers, bools,
                        # Paths and FilePayloads, not Files: to_form_field() takes them.
                        multipart_data.append(await to_form_field(name, value))
            else:
                # Convert file-like values to ServerFilePayload structs.
                for name, value in multipart.items():
                    multipart_data.append(await to_form_field(name, value))
        if (
            post_data_buffer is None
            and json_data is None
            and form_data is None
            and multipart_data is None
        ):
            post_data_buffer = request.post_data_buffer if request else None
        # Not ported: the __testHookLookup fixture, a hook of the JS tests.
        result = await self._channel.fetch(
            url=url,
            params=object_to_array(params) if isinstance(params, dict) else None,
            encodedParams=encoded_params,
            method=method,
            headers=headers_array,
            # Python: the binary is base64 on the channel.
            postData=(
                base64.b64encode(post_data_buffer).decode()
                if post_data_buffer is not None
                else None
            ),
            jsonData=json_data,
            formData=form_data,
            multipartData=multipart_data,
            failOnStatusCode=fail_on_status_code,
            ignoreHTTPSErrors=ignore_https_errors,
            maxRedirects=max_redirects,
            maxRetries=max_retries,
            timeout=self._timeout_settings.timeout(timeout),
        )
        return APIResponse(self, result["response"])

    async def storage_state(
        self,
        path: Optional[Union[str, Path]],
        indexed_db: Optional[bool],
        opfs: Optional[bool],
    ) -> StorageState:
        state = await self._channel.storageState(
            indexedDB=indexed_db, opfs=opfs, timeout=NO_TIMEOUT
        )
        if path:
            await mkdir_if_needed(path)
            await _write_file(path, _json_stringify(state, 2))
        return cast(StorageState, state)


async def to_form_field(name: str, value: Any) -> "channels.FormField":
    if is_file_payload(value):
        payload = cast(FilePayload, value)
        if not isinstance(payload["buffer"], bytes):
            raise Error(f"Unexpected buffer type of 'data.{name}'")
        return {"name": name, "file": file_payload_to_json(payload)}
    elif isinstance(value, (str, int, float, bool)):
        return {"name": name, "value": js_string(value)}
    # Python: a pathlib.Path is the counterpart of an fs.ReadStream. Upstream takes
    # any other value for a stream; here it is an error.
    elif isinstance(value, Path):
        return {"name": name, "file": await read_stream_to_json(value)}
    raise Error(f"Unexpected value type of 'multipart.{name}'")


def is_json_parsable(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        # Python: NaN and Infinity are not JSON, as JSON.parse() says.
        json.loads(value, parse_constant=_reject_json_constant)
        return True
    except json.JSONDecodeError:
        # Python: json.JSONDecodeError is the SyntaxError of JSON.parse().
        return False


class APIResponse:
    def __init__(
        self, context: APIRequestContext, initializer: "channels.APIResponse"
    ) -> None:
        # Python: imported here, to avoid an import cycle.
        from playwright._impl_v2.network import RawHeaders

        self._request = context
        self._initializer = initializer
        self._headers = RawHeaders(self._initializer["headers"])
        self._api_name = "APIResponse"
        # Python: the generated API reads the event loop of each object.
        self._loop = context._loop

        # Not ported: the inspect.custom hook of Node's util.inspect().

    def _wrap_api_call(
        self,
        func: Callable[["ApiZone"], Awaitable[R]],
        options: Optional[ApiCallOptions] = None,
    ) -> Awaitable[R]:
        # Python: not an async def, as ChannelOwner._wrap_api_call().
        return self._request._wrap_api_call(func, options)

    @property
    def ok(self) -> bool:
        return self._initializer["status"] >= 200 and self._initializer["status"] <= 299

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
    def headers_array(self) -> HeadersArray:
        return self._headers.headers_array()

    async def security_details(self) -> Optional[SecurityDetails]:
        return cast(Optional[SecurityDetails], self._initializer.get("securityDetails"))

    async def server_addr(self) -> Optional[RemoteAddr]:
        return self._initializer.get("serverAddr")

    @property
    def timing(self) -> ResourceTiming:
        response_end_timing = self._initializer.get("responseEndTiming")
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
                **(self._initializer.get("timing") or {}),
                "responseEnd": (
                    response_end_timing if response_end_timing is not None else -1
                ),
            },
        )

    @internal
    async def body(self) -> bytes:
        try:
            result = await self._request._channel.fetchResponseBody(
                fetchUid=self._fetch_uid(), timeout=NO_TIMEOUT
            )
            if result["binary"] is None:
                raise Error("Response has been disposed")
            # Python: the binary is base64 on the channel.
            return base64.b64decode(result["binary"])
        except Exception as e:
            if is_target_closed_error(e):
                raise Error("Response has been disposed")
            raise e

    async def text(self) -> str:
        content = await self.body()
        # Python: as toString('utf8'), invalid bytes become U+FFFD.
        return content.decode("utf-8", errors="replace")

    async def json(self) -> Any:
        content = await self.text()
        return json.loads(content)

    # Not ported: [Symbol.asyncDispose](); the Python APIResponse is not an async
    # context manager.

    async def dispose(self) -> None:
        await self._request._channel.disposeAPIResponse(
            fetchUid=self._fetch_uid(), timeout=NO_TIMEOUT
        )

    # Not ported: _inspect(), the text for Node's util.inspect(); __repr__() below
    # is the Python counterpart.

    def _fetch_uid(self) -> str:
        return self._initializer["fetchUid"]

    async def _fetch_log(self) -> List[str]:
        log = (
            await self._request._channel.fetchLog(
                fetchUid=self._fetch_uid(), timeout=NO_TIMEOUT
            )
        )["log"]
        return log

    # Python only: the members of the Python API that upstream does not have.

    def __repr__(self) -> str:
        return f"<APIResponse url={self.url!r} status={self.status!r} status_text={self.status_text!r}>"


def file_payload_to_json(payload: FilePayload) -> "channels.FormFieldFile":
    return {
        "name": payload["name"],
        "mimeType": payload["mimeType"],
        # Python: the binary is base64 on the channel.
        "buffer": base64.b64encode(payload["buffer"]).decode(),
    }


async def read_stream_to_json(stream: Path) -> "channels.FormFieldFile":
    # Python: the 'data' and 'end' events of the stream are a read of the file.
    buffer = await _read_bytes(stream)
    stream_path = str(stream)
    return {
        "name": os.path.basename(stream_path),
        # Python: the binary is base64 on the channel.
        "buffer": base64.b64encode(buffer).decode(),
    }


def is_json_content_type(headers: Optional[HeadersArray]) -> bool:
    if not headers:
        return False
    for header in headers:
        if header["name"].lower() == "content-type":
            return header["value"].split(";")[0].strip().lower() == "application/json"
    return False


def object_to_array(map: Optional[Dict[str, Any]]) -> Optional[List[NameValue]]:
    if map is None:
        return None
    result: List[NameValue] = []
    for name, value in map.items():
        if value is not None:
            result.append({"name": name, "value": js_string(value)})
    return result


def is_file_payload(value: Any) -> bool:
    # Python: the truthiness of each field, as upstream; a buffer is an object, so
    # it is truthy even when it is empty.
    return (
        isinstance(value, dict)
        and bool(value.get("name"))
        and bool(value.get("mimeType"))
        and value.get("buffer") is not None
    )


# Python only: the counterparts of JSON.stringify() and of fs.promises.readFile() and
# writeFile().


def _json_stringify(value: Any, indent: Optional[int] = None) -> str:
    # JSON.stringify(value, undefined, indent): no spaces without an indent, and no
    # escapes of non-ASCII characters. NaN and Infinity raise a ValueError.
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )


def _reject_json_constant(value: str) -> Any:
    raise json.JSONDecodeError(f"{value} is not valid JSON", value, 0)


async def _read_bytes(path: Union[str, Path]) -> bytes:
    return await asyncio.get_running_loop().run_in_executor(
        None, lambda: Path(path).read_bytes()
    )


async def _read_file(path: Union[str, Path]) -> str:
    # fs.promises.readFile(path, 'utf8').
    return (await _read_bytes(path)).decode("utf-8")


async def _write_file(path: Union[str, Path], data: str) -> None:
    # fs.promises.writeFile(path, data, 'utf8').
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: Path(path).write_bytes(data.encode("utf-8"))
    )
