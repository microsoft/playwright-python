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

import inspect
from typing import Any, Callable, Dict, List, Optional
from weakref import WeakKeyDictionary

from playwright._types import Error


class ImplWrapper:
    def __init__(self, impl_obj: Any) -> None:
        self._impl_obj = impl_obj


class ImplToApiMapping:
    def __init__(self) -> None:
        self._mapping: Dict[type, type] = {}
        self._instances: WeakKeyDictionary[Any, Any] = WeakKeyDictionary()

    def register(self, impl_class: type, api_class: type) -> None:
        self._mapping[impl_class] = api_class

    def from_maybe_impl(self, obj: Any) -> Any:
        if not obj:
            return obj
        if isinstance(obj, dict):
            return {name: self.from_maybe_impl(value) for name, value in obj.items()}
        if isinstance(obj, list):
            return [self.from_maybe_impl(item) for item in obj]
        if obj not in self._instances:
            api_class = self._mapping.get(type(obj))
            if not api_class:
                return obj
            api_instance = api_class(obj)
            self._instances[obj] = api_instance
        return self._instances[obj]

    def from_impl(self, obj: Any) -> Any:
        assert obj
        result = self.from_maybe_impl(obj)
        assert result
        return result

    def from_impl_nullable(self, obj: Any = None) -> Optional[Any]:
        return self.from_impl(obj) if obj else None

    def from_impl_list(self, items: List[Any]) -> List[Any]:
        return list(map(lambda a: self.from_impl(a), items))

    def from_impl_dict(self, map: Dict[str, Any]) -> Dict[str, Any]:
        return {name: self.from_impl(value) for name, value in map.items()}

    def to_impl(self, obj: Any) -> Any:
        try:
            if not obj:
                return obj
            if isinstance(obj, dict):
                return {name: self.to_impl(value) for name, value in obj.items()}
            if isinstance(obj, list):
                return [self.to_impl(item) for item in obj]
            if isinstance(obj, ImplWrapper):
                return obj._impl_obj
            return obj
        except RecursionError:
            raise Error("Maximum argument depth exceeded")

    def wrap_handler(self, handler: Callable[..., None]) -> Callable[..., None]:
        if handler in self._instances:
            return self._instances[handler]

        def wrapper(*args: Any) -> Any:
            arg_count = len(inspect.signature(handler).parameters)
            return handler(
                *list(map(lambda a: self.from_maybe_impl(a), args))[:arg_count]
            )

        self._instances[handler] = wrapper
        return wrapper
