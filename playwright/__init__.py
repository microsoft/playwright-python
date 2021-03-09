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

"""
Python package `playwright` is a Python library to automate Chromium,
Firefox and WebKit with a single API. Playwright is built to enable cross-browser
web automation that is ever-green, capable, reliable and fast.
For more information you'll find the documentation for the sync API [here](sync_api.html)
and for the async API [here](async_api.html).
"""
from contextlib import contextmanager

from playwright.sync_api import sync_playwright


@contextmanager
def chromium(url=None, incognito=False, *args, **kwargs):
    with sync_playwright() as p:
        browser = p.chromium.launch(**kwargs)
        context = browser.new_context(**kwargs) if incognito else browser
        page = context.new_page()
        if url is not None:
            page.goto(url)
        try:
            yield page
        finally:
            browser.close()


@contextmanager
def firefox(url=None, incognito=False, *args, **kwargs):
    with sync_playwright() as p:
        browser = p.firefox.launch(**kwargs)
        context = browser.new_context(**kwargs) if incognito else browser
        page = context.new_page()
        if url is not None:
            page.goto(url)
        try:
            yield page
        finally:
            browser.close()


@contextmanager
def webkit(url=None, incognito=False, *args, **kwargs):
    with sync_playwright() as p:
        browser = p.webkit.launch(**kwargs)
        context = browser.new_context(**kwargs) if incognito else browser
        page = context.new_page()
        if url is not None:
            page.goto(url)
        try:
            yield page
        finally:
            browser.close()
