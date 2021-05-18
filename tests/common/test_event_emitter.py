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

import pytest

from playwright._impl._event_emitter import EventEmitter


@pytest.fixture
def ee():
    return EventEmitter()


def test_event_emitter_on(ee: EventEmitter):
    emitted = []
    ee.on("foo", lambda: emitted.append("foo"))
    assert emitted == []
    ee.emit("foo")
    assert emitted[0] == "foo"


def test_event_emitter_once(ee: EventEmitter):
    emitted = []
    ee.once("foo", lambda: emitted.append("foo"))
    assert emitted == []
    ee.emit("foo")
    assert emitted[0] == "foo"
    ee.emit("foo")
    assert len(emitted) == 1


def test_event_emitter_listeners(ee: EventEmitter):
    emitted = []

    def func():
        emitted.append("foo")

    ee.on("foo", func)
    assert len(ee.listeners("foo")) == 1
    assert ee.listeners("foo")[0] == func


def test_event_emitter_remove_listener(ee: EventEmitter):
    emitted = []

    def func():
        emitted.append("foo")

    ee.once("foo", func)
    assert len(ee.listeners("foo")) == 1
    ee.remove_listener("foo", func)
    assert len(ee.listeners("foo")) == 0


@pytest.mark.asyncio
async def test_event_emitter_async(ee: EventEmitter):
    emitted = []

    async def func():
        emitted.append("foo")

    ee.once("foo", func)
    ee.emit("foo")
    await asyncio.sleep(0)
    assert emitted[0] == "foo"
