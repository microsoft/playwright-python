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

# Types that the implementation uses internally. The public TypedDicts are
# generated into _api_structures.py.

from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict

from playwright._impl._api_structures import NameValue

HeadersArray = List[NameValue]
Headers = Dict[str, str]


class ServerFilePayload(TypedDict):
    name: str
    mimeType: str
    buffer: str


class FormField(TypedDict, total=False):
    name: str
    value: Optional[str]
    file: Optional[ServerFilePayload]


class ExpectedTextValue(TypedDict, total=False):
    string: str
    regexSource: str
    regexFlags: str
    matchSubstring: bool
    normalizeWhiteSpace: bool
    ignoreCase: Optional[bool]


class FrameExpectOptions(TypedDict, total=False):
    expressionArg: Any
    expectedText: Optional[Sequence[ExpectedTextValue]]
    expectedNumber: Optional[float]
    expectedValue: Optional[Any]
    useInnerText: Optional[bool]
    isNot: bool
    timeout: Optional[float]
    pseudo: Optional[str]


class FrameExpectResult(TypedDict, total=False):
    matches: bool
    received: Any
    log: Optional[List[str]]
    errorMessage: Optional[str]
    timedOut: Optional[bool]


AriaRole = Literal[
    "alert",
    "alertdialog",
    "application",
    "article",
    "banner",
    "blockquote",
    "button",
    "caption",
    "cell",
    "checkbox",
    "code",
    "columnheader",
    "combobox",
    "complementary",
    "contentinfo",
    "definition",
    "deletion",
    "dialog",
    "directory",
    "document",
    "emphasis",
    "feed",
    "figure",
    "form",
    "generic",
    "grid",
    "gridcell",
    "group",
    "heading",
    "img",
    "insertion",
    "link",
    "list",
    "listbox",
    "listitem",
    "log",
    "main",
    "marquee",
    "math",
    "menu",
    "menubar",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "meter",
    "navigation",
    "none",
    "note",
    "option",
    "paragraph",
    "presentation",
    "progressbar",
    "radio",
    "radiogroup",
    "region",
    "row",
    "rowgroup",
    "rowheader",
    "scrollbar",
    "search",
    "searchbox",
    "separator",
    "slider",
    "spinbutton",
    "status",
    "strong",
    "subscript",
    "superscript",
    "switch",
    "tab",
    "table",
    "tablist",
    "tabpanel",
    "term",
    "textbox",
    "time",
    "timer",
    "toolbar",
    "tooltip",
    "tree",
    "treegrid",
    "treeitem",
]
