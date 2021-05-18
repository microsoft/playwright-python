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
from asyncio import AbstractEventLoop
from collections import defaultdict
from threading import Lock
from typing import (
    Any,
    Callable,
    Coroutine,
    DefaultDict,
    List,
    Optional,
    OrderedDict,
    cast,
)


class EventEmitter:
    def __init__(self, loop: Optional[AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_event_loop()
        self._lock = Lock()
        self._events: DefaultDict[
            str,
            OrderedDict[
                Callable[..., Optional[Coroutine]],
                Callable[..., Optional[Coroutine]],
            ],
        ] = defaultdict(OrderedDict)

    def on(self, event: str, f: Callable[..., Optional[Coroutine]]) -> None:
        self._add_event_handler(event, f)

    def _add_event_handler(
        self, event: str, f: Callable[..., Optional[Coroutine]]
    ) -> None:
        with self._lock:
            self._events[event][f] = f

    def once(self, event: str, f: Callable[..., Optional[Coroutine]]) -> None:
        def wrapper(*args: Any, **kwargs: Any) -> Optional[Coroutine]:
            with self._lock:
                if event in self._events and f in self._events[event]:
                    self._events[event].pop(f)
            return f(*args, **kwargs)

        with self._lock:
            self._events[event][f] = wrapper

    def remove_listener(
        self, event: str, f: Callable[..., Optional[Coroutine]]
    ) -> None:
        with self._lock:
            self._events[event].pop(f)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            funcs = list(self._events[event].values())
        for f in funcs:
            coroutine = cast(Coroutine, f(*args, **kwargs))
            if asyncio.iscoroutine(coroutine):
                self._loop.create_task(coroutine)

    def listeners(self, event: str) -> List[Callable[..., Optional[Coroutine]]]:
        return list(self._events[event].keys())
