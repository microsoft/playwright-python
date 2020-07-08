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

from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import sys

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict


if TYPE_CHECKING:
  from playwright.network import Route, Request

Cookie = List[Dict[str, Union[str, int, bool]]]
URLMatch = Union[str, Callable[[str], bool]]
RouteHandler = Callable[['Route', 'Request'], None]
FunctionWithSource = Callable[[Dict], Any]
class FilePayload(TypedDict):
 name: str
 mimeType: str
 buffer: bytes
class FrameMatch(TypedDict):
  url: URLMatch
  name: str
class PendingWaitEvent(TypedDict):
  event: str
  future: asyncio.Future

class RouteHandlerEntry(TypedDict):
  matcher: "URLMatcher"
  handler: RouteHandler
class SelectOption(TypedDict):
  value: Optional[str]
  label: Optional[str]
  index: Optional[str]
class ConsoleMessageLocation(TypedDict):
  url: Optional[str]
  lineNumber: Optional[int]
  columnNumber: Optional[int]
class ErrorPayload(TypedDict):
  message: str
  name: str
  stack: str
  value: Any

class URLMatcher:
  def __init__(self, match: URLMatch):
    self._callback = None
    self._regex_obj = None
    if isinstance(match, str):
      regex = '(?:http://|https://)' + fnmatch.translate(match)
      self._regex_obj = re.compile(regex)
    else:
      self._callback = match
    self.match = match

  def matches(self, url: str) -> bool:
    if self._callback:
      return self._callback(url)
    return self._regex_obj.match(url)


class TimeoutSettings:
  def __init__(self, parent: Optional['TimeoutSettings']) -> None:
    self._parent = parent

  def set_default_timeout(self, timeout):
    self.timeout = timeout

class Error(BaseException):
  def __init__(self, message: str) -> None:
    self.message = message

def serialize_error(ex: BaseException) -> ErrorPayload:
  return dict(message=str(ex))

def parse_error(error: ErrorPayload):
  return Error('%s\n%s' % (error['message'], error['stack']))

def is_function_body(expression: str) -> bool:
  expression = expression.strip()
  return expression.startswith('function') or expression.startswith('async ') or '=>' in expression

def locals_to_params(args: Dict) -> Dict:
  copy = dict()
  for key in args:
    if key == 'self':
      continue
    if args[key] != None:
      copy[key] = args[key]
  return copy
