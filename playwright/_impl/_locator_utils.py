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

"""Port of packages/isomorphic/locatorUtils.ts."""

from typing import List, Pattern, Tuple, Union

from playwright._impl._internal_structures import AriaRole
from playwright._impl._str_utils import (
    escape_for_attribute_selector,
    escape_for_text_selector,
)


def get_by_test_id_selector(
    test_id_attribute_name: str, test_id: Union[str, Pattern[str]]
) -> str:
    return f"internal:testid=[{test_id_attribute_name}={escape_for_attribute_selector(test_id, True)}]"


def get_by_attribute_text_selector(
    attr_name: str, text: Union[str, Pattern[str]], exact: bool = None
) -> str:
    return f"internal:attr=[{attr_name}={escape_for_attribute_selector(text, exact=exact)}]"


def get_by_label_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return "internal:label=" + escape_for_text_selector(text, exact=exact)


def get_by_alt_text_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return get_by_attribute_text_selector("alt", text, exact=exact)


def get_by_title_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return get_by_attribute_text_selector("title", text, exact=exact)


def get_by_placeholder_selector(
    text: Union[str, Pattern[str]], exact: bool = None
) -> str:
    return get_by_attribute_text_selector("placeholder", text, exact=exact)


def get_by_text_selector(text: Union[str, Pattern[str]], exact: bool = None) -> str:
    return "internal:text=" + escape_for_text_selector(text, exact=exact)


def bool_to_js_bool(value: bool) -> str:
    return "true" if value else "false"


def get_by_role_selector(
    role: AriaRole,
    checked: bool = None,
    disabled: bool = None,
    expanded: bool = None,
    include_hidden: bool = None,
    level: int = None,
    name: Union[str, Pattern[str]] = None,
    pressed: bool = None,
    selected: bool = None,
    exact: bool = None,
    description: Union[str, Pattern[str]] = None,
) -> str:
    props: List[Tuple[str, str]] = []
    if checked is not None:
        props.append(("checked", bool_to_js_bool(checked)))
    if disabled is not None:
        props.append(("disabled", bool_to_js_bool(disabled)))
    if selected is not None:
        props.append(("selected", bool_to_js_bool(selected)))
    if expanded is not None:
        props.append(("expanded", bool_to_js_bool(expanded)))
    if include_hidden is not None:
        props.append(("include-hidden", bool_to_js_bool(include_hidden)))
    if level is not None:
        props.append(("level", str(level)))
    if name is not None:
        props.append(
            (
                "name",
                escape_for_attribute_selector(name, exact=exact),
            )
        )
    if description is not None:
        props.append(
            (
                "description",
                escape_for_attribute_selector(description, exact=exact),
            )
        )
    if pressed is not None:
        props.append(("pressed", bool_to_js_bool(pressed)))
    props_str = "".join([f"[{t[0]}={t[1]}]" for t in props])
    return f"internal:role={role}{props_str}"
