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

"""Python only: protocol validation at the None/undefined boundary."""

from typing import Any, List

import pytest

from playwright._impl.protocol.validator_primitives import (
    ValidationError,
    ValidatorContext,
    t_any,
    t_array,
    t_object,
    t_string,
)


def test_should_skip_absent_optional_fields_and_preserve_json_null() -> None:
    context = ValidatorContext(
        lambda names, arg, path, context: arg, "base64", lambda: True
    )
    calls: List[Any] = []

    def optional_string(arg: Any, path: str, context: ValidatorContext) -> Any:
        calls.append(arg)
        return t_string(arg, path, context)

    validator = t_object({"name": t_string}, {"value": optional_string})
    assert validator({"name": "item"}, "", context) == {"name": "item"}
    assert validator({"name": "item", "value": None}, "", context) == {"name": "item"}
    assert calls == []
    assert validator({"name": "item", "value": ""}, "", context) == {
        "name": "item",
        "value": "",
    }
    assert calls == [""]
    with pytest.raises(ValidationError, match="value: expected string, got number"):
        validator({"name": "item", "value": 7}, "", context)
    with pytest.raises(ValidationError, match="name: expected string, got undefined"):
        validator({}, "", context)

    json_validator = t_object({}, {"value": t_any})
    assert json_validator({"value": None}, "", context) == {}
    assert t_array(json_validator)([{}, {"value": None}], "", context) == [
        {},
        {"value": None},
    ]
