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
import json
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page
from tests.server import Server


async def test_should_capture_local_storage(context: BrowserContext) -> None:
    page1 = await context.new_page()
    await page1.route(
        "**/*", lambda route: asyncio.create_task(route.fulfill(body="<html></html>"))
    )
    await page1.goto("https://www.example.com")
    await page1.evaluate("localStorage['name1'] = 'value1'")
    await page1.goto("https://www.domain.com")
    await page1.evaluate("localStorage['name2'] = 'value2'")

    state = await context.storage_state()
    origins = state["origins"]
    assert len(origins) == 2
    assert origins[0] == {
        "origin": "https://www.example.com",
        "localStorage": [{"name": "name1", "value": "value1"}],
    }
    assert origins[1] == {
        "origin": "https://www.domain.com",
        "localStorage": [{"name": "name2", "value": "value2"}],
    }


async def test_should_set_local_storage(browser: Browser) -> None:
    context = await browser.new_context(
        storage_state={
            "origins": [
                {
                    "origin": "https://www.example.com",
                    "localStorage": [{"name": "name1", "value": "value1"}],
                }
            ]
        }
    )

    page = await context.new_page()
    await page.route(
        "**/*", lambda route: asyncio.create_task(route.fulfill(body="<html></html>"))
    )
    await page.goto("https://www.example.com")
    local_storage = await page.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}
    await context.close()


async def test_should_round_trip_through_the_file(
    browser: Browser, context: BrowserContext, tmpdir: Path
) -> None:
    page1 = await context.new_page()
    await page1.route(
        "**/*",
        lambda route: asyncio.create_task(route.fulfill(body="<html></html>")),
    )
    await page1.goto("https://www.example.com")
    await page1.evaluate(
        """() => {
            localStorage["name1"] = "value1"
            document.cookie = "username=John Doe"
            return document.cookie
        }"""
    )

    path = tmpdir / "storage-state.json"
    state = await context.storage_state(path=path)
    with open(path, "r") as f:
        written = json.load(f)
    assert state == written

    context2 = await browser.new_context(storage_state=path)
    page2 = await context2.new_page()
    await page2.route(
        "**/*",
        lambda route: asyncio.create_task(route.fulfill(body="<html></html>")),
    )
    await page2.goto("https://www.example.com")
    local_storage = await page2.evaluate("window.localStorage")
    assert local_storage == {"name1": "value1"}
    cookie = await page2.evaluate("document.cookie")
    assert cookie == "username=John Doe"
    await context2.close()


async def test_should_serialiser_storage_state_with_lone_surrogates(
    page: Page, context: BrowserContext, server: Server
) -> None:
    chars = [
        14210,
        8342,
        610,
        1472,
        19632,
        13824,
        29376,
        52231,
        24579,
        88,
        36890,
        4099,
        29440,
        26416,
        368,
        7872,
        9985,
        62632,
        6848,
        21248,
        60513,
        2332,
        816,
        5504,
        9068,
        280,
        720,
        8260,
        54576,
        60417,
        14515,
        3472,
        4292,
        21022,
        23588,
        62856,
        15618,
        54344,
        16400,
        224,
        1729,
        31022,
        13314,
        55489,
        24597,
        51409,
        33318,
        22595,
        704,
        14765,
        778,
        56631,
        24578,
        56476,
        32964,
        39424,
        7828,
        8221,
        51744,
        3712,
        6344,
        53892,
        35214,
        12930,
        54335,
        17412,
        38458,
        35221,
        38530,
        12828,
        36826,
        52929,
        54075,
        14117,
        38543,
        51596,
        3520,
        9406,
        49282,
        46281,
        33302,
        38109,
        38419,
        5659,
        6227,
        1101,
        5,
        20566,
        6667,
        23670,
        6695,
        35098,
        16395,
        17190,
        49346,
        5565,
        46010,
        1051,
        47039,
        45173,
        1132,
        25204,
        31265,
        6934,
        352,
        33321,
        36748,
        40073,
        38546,
        1552,
        21249,
        6751,
        1046,
        12933,
        40065,
        22076,
        40682,
        6667,
        25192,
        32952,
        2312,
        49105,
        42577,
        9084,
        31760,
        49257,
        16515,
        37715,
        20904,
        2595,
        11524,
        35137,
        45905,
        25278,
        30832,
        13765,
        50053,
        714,
        1574,
        13587,
        5456,
        31714,
        51728,
        27160,
        204,
        18500,
        32854,
        57112,
        10241,
        11029,
        12673,
        16108,
        36873,
        40065,
        16816,
        16625,
        15436,
        13392,
        19254,
        37433,
        15982,
        8520,
        45550,
        11584,
        40368,
        52490,
        19,
        56704,
        1622,
        63553,
        51238,
        27755,
        34758,
        50245,
        12517,
        40704,
        7298,
        33479,
        35072,
        132,
        5252,
        1341,
        8513,
        37323,
        39640,
        6971,
        16403,
        17185,
        61873,
        32168,
        39565,
        32796,
        23697,
        24656,
        45365,
        52524,
        24701,
        20486,
        5280,
        10806,
        17,
        40,
        34384,
        21352,
        378,
        32109,
        27116,
        25868,
        39443,
        46994,
        36014,
        3254,
        24990,
        50578,
        57588,
        95,
        17205,
        2238,
        19477,
        12360,
        31960,
        34491,
        23471,
        54313,
        3566,
        22047,
        46654,
        16911,
        45251,
        54280,
        54371,
        11533,
        27568,
        7502,
        38757,
        24987,
        16635,
        9792,
        46500,
        864,
        35905,
        47223,
        41120,
        12047,
        40824,
        8224,
        1154,
        8560,
        37954,
        10000,
        18724,
        21097,
        18305,
        2338,
        17186,
        61967,
        8227,
        64361,
        63895,
        28094,
        22567,
        45901,
        35044,
        24343,
        17361,
        62467,
        12428,
        12940,
        58130,
        1794,
        2257,
        13824,
        33696,
        59144,
        3707,
        1121,
        9283,
        5060,
        35122,
        16882,
        16099,
        15720,
        55934,
        52917,
        44987,
        68,
        16649,
        720,
        31773,
        19171,
        36912,
        15372,
        33184,
        22574,
        64,
        142,
        13843,
        1477,
        44223,
        3872,
        1602,
        27321,
        3096,
        32826,
        33415,
        43034,
        62624,
        57963,
        48163,
        39146,
        7046,
        37300,
        27027,
        31927,
        15592,
        60218,
        24619,
        41025,
        22156,
        39659,
        27246,
        31265,
        36426,
        21236,
        15014,
        19376,
        26,
        43265,
        16592,
        6402,
        18144,
        63725,
        1389,
        368,
        26770,
        18656,
        10448,
        44291,
        37489,
        60845,
        49161,
        26831,
        198,
        32780,
        18498,
        2535,
        31051,
        11046,
        53820,
        22530,
        534,
        41057,
        29215,
        22784,
        0,
    ]
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """chars => window.localStorage.setItem('foo', chars.map(c => String.fromCharCode(c)).join(''))""",
        chars,
    )
    storage_state = await context.storage_state()
    assert storage_state["origins"][0]["localStorage"][0]["value"] == "".join(
        map(chr, chars)
    )
