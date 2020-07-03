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
import collections
import fnmatch
import re

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
# from typing import TypedDict

Cookie = List[Dict[str, Union[str, int, bool]]]
URLMatch = Union[str, Callable[[str], bool]]
FilePayload = Dict # TypedDict('FilePayload', name=str, mimeType=str, buffer=bytes)
FrameMatch = Dict # TypedDict('FrameMatch', url=URLMatch, name=str)
PendingWaitEvent = Dict # TypedDict('PendingWaitEvent', event=str, future=asyncio.Future)
RouteHandler = Callable[['Route', 'Request'], None]
RouteHandlerEntry = Dict # TypedDict('RouteHandlerEntry', matcher=URLMatcher, handler=RouteHandler)
SelectOption = Dict # TypedDict('SelectOption', value=Optional[str], label=Optional[str], index=Optional[str])
ConsoleMessageLocation = Dict #TypedDict('ConsoleMessageLocation', url=Optional[str], lineNumber=Optional[int], columnNumber=Optional[int])
FunctionWithSource = Callable[[Dict], Any]
ContinueRequest = Dict # TypedDict('ContinueRequest', method=string, headers=Dict[str,str], postData=bytes)
FulfillResponse = Dict # TypedDict('FulfillResponse', status=int, headers=Dict[str,str], body=str, isBase64=bool])
ErrorPayload = Dict  # TypedDict('ErrorPayload', message=str, name=str, stack=str, value=Any)

class URLMatcher:
  def __init__(self, match: URLMatch):
    if isinstance(match, str):
      regex = fnmatch.translate(match)
      self._regex_obj = re.compile(regex)
    else:
      self._reges_callback = match
    self.match = match

  def matches(self, url: str) -> bool:
    if self._reges_callback:
      return self._reges_callback(url)
    return self._regex_obj.match(url)


class TimeoutSettings:
  def __init__(self, parent: Optional['TimeoutSettings']) -> None:
    self._parent = parent

  def setDefaultTimeout(self, timeout):
    self.timeout = timeout

class Error(BaseException):
  def __init__(self, message: str) -> None:
    self.message = message

def serializeError(ex: BaseException) -> ErrorPayload:
  return dict(message=str(ex))

def parseError(error: ErrorPayload):
  return Error('%s\n%s' % (error['message'], error['stack']))
