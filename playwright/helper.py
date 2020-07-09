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

from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TYPE_CHECKING, Pattern, cast

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
 buffer: Union[bytes, str]
class FrameMatch(TypedDict):
  url: URLMatch
  name: str
class SelectOption(TypedDict):
  value: Optional[str]
  label: Optional[str]
  index: Optional[str]
class ConsoleMessageLocation(TypedDict):
  url: Optional[str]
  lineNumber: Optional[int]
  columnNumber: Optional[int]
class ErrorPayload(TypedDict, total=False):
  message: str
  name: str
  stack: str
  value: Any

class ContinueParameters(TypedDict, total=False):
  method: str
  headers: Dict[str, str]
  postData: str

class ParsedMessageParams(TypedDict):
  type: str
  guid: str
  initializer: Dict

class ParsedMessagePayload(TypedDict, total=False):
  id: int
  guid: str
  method: str
  params: ParsedMessageParams
  result: Any
  error: ErrorPayload


class URLMatcher:
  def __init__(self, match: URLMatch):
    self._callback: Optional[Callable[[str], bool]] = None
    self._regex_obj: Optional[Pattern] = None
    if isinstance(match, str):
      regex = '(?:http://|https://)' + fnmatch.translate(match)
      self._regex_obj = re.compile(regex)
    else:
      self._callback = match
    self.match = match

  def matches(self, url: str) -> bool:
    if self._callback:
      return self._callback(url)
    if self._regex_obj:
      return cast(bool, self._regex_obj.match(url))
    return False


class TimeoutSettings:
  def __init__(self, parent: Optional['TimeoutSettings']) -> None:
    self._parent = parent

  def set_default_timeout(self, timeout):
    self.timeout = timeout

class Error(Exception):
  def __init__(self, message: str, stack: str = None) -> None:
    self.message = message
    self.stack = stack

class TimeoutError(Error):
  pass

def serialize_error(ex: Exception) -> ErrorPayload:
  return dict(message=str(ex))

def parse_error(error: ErrorPayload):
  base_error_class = Error
  if error.get("name") == "TimeoutError":
    base_error_class = TimeoutError
  return base_error_class(error['message'], error['stack'])

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

class PendingWaitEvent:
  def __init__(self, event: str, future: asyncio.Future):
    self.event = event
    self.future = future

class RouteHandlerEntry:
  def __init__(self, matcher: URLMatcher, handler: RouteHandler):
    self.matcher = matcher
    self.handler = handler
