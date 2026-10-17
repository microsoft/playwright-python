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

"""Port of tests/library/browsercontext-device.spec.ts."""

from typing import Awaitable, Callable

import pytest

from playwright.async_api import Browser, BrowserContext, Playwright
from tests.server import Server

ContextFactory = Callable[..., Awaitable[BrowserContext]]

# The upstream describe 'device' skips firefox (but not firefox over BiDi).
pytestmark = pytest.mark.skip_browser("firefox")

SCROLL_TWICE_CONTENT = """
          <meta name="viewport" content="width=device-width, user-scalable=no" />
          Lorem ipsum dolor sit amet consectetur adipiscing elit proin, integer curabitur imperdiet rhoncus cursus tincidunt bibendum, consequat sed magnis laoreet luctus mollis tellus. Nisl parturient mus accumsan feugiat sem laoreet magnis nisi, aptent per sollicitudin gravida orci ac blandit, viverra eros praesent auctor vivamus semper bibendum. Consequat sed habitasse luctus dictumst gravida platea semper phasellus, nascetur ridiculus purus est varius quisque et scelerisque, id vehicula eleifend montes sollicitudin dis velit. Pellentesque ridiculus per natoque et eleifend taciti nunc, laoreet auctor at condimentum imperdiet ante, conubia mi cubilia scelerisque sociosqu sem.</p> <p>Curabitur magna per felis primis mauris non dapibus luctus ultricies eros, quis et egestas condimentum lobortis eget semper montes litora purus, ridiculus elementum sollicitudin imperdiet dictum lacinia parturient cras eu. Risus cum varius rhoncus eros torquent pretium taciti id erat dis egestas, nibh tristique montes convallis metus lacus phasellus blandit ut auctor bibendum semper, facilisis mi integer eget ultrices lobortis odio viverra duis dui. Risus ullamcorper lacinia in venenatis sodales fusce tortor potenti volutpat quis, dictum vulputate suspendisse velit mollis torquent sociis aptent morbi, senectus nascetur justo maecenas conubia magnis viverra gravida fames. Phasellus sed nec gravida nibh class augue lectus, blandit quis turpis orci diam nam pellentesque, ultricies metus imperdiet hendrerit lacinia lacus.</p> <p>Inceptos facilisi montes cum hendrerit, pulvinar ut tellus eget velit, arcu nulla aenean. Phasellus augue urna nostra molestie interdum vehicula, posuere fames cum euismod massa curabitur donec, inceptos cubilia tellus facilisis fermentum. Lacus laoreet facilisis ultrices cursus quisque at ad porta vestibulum massa inceptos, curae class aliquet maecenas cum ullamcorper pulvinar erat mus vitae. Cum in aenean convallis dis quam tincidunt justo sed quisque, imperdiet faucibus hendrerit felis commodo scelerisque magnis vehicula etiam leo, eros varius platea lobortis maecenas condimentum nisi phasellus. Turpis vulputate mus himenaeos sociosqu facilisis dignissim leo quam, ultricies habitasse commodo molestie est tortor vitae et, porttitor risus erat cursus phasellus facilisi litora.</p> <p>Nostra habitasse egestas magnis velit pellentesque parturient cum lectus viverra, vestibulum sociosqu nunc vel urna consequat lacinia phasellus at sapien, aenean pretium dictum sed montes interdum imperdiet iaculis. Leo hac eros arcu senectus maecenas, tortor pulvinar venenatis lacinia volutpat, mattis platea ut facilisi. Aenean condimentum at et donec sociosqu fermentum luctus potenti semper vulputate, sapien justo non est auctor gravida ultricies fames per commodo, sed habitasse facilisi nulla quisque hendrerit aliquet viverra bibendum.</p> <p>Interdum nisl quam etiam montes porttitor laoreet nullam senectus velit, mauris proin tellus imperdiet litora venenatis fames massa quis, sollicitudin justo vivamus curae in sociis suscipit facilisi. Platea inceptos lacus elementum pellentesque quam euismod dictumst sociis tincidunt vulputate porttitor eros, turpis netus ut ad tempor sapien aliquet sodales molestie consequat nostra. Cum augue in quisque primis ut nunc sodales, sem orci tempus posuere cubilia suspendisse lacinia ligula, magna sed ridiculus at maecenas habitant.</p> <p>Natoque magna ac feugiat tellus bibendum diam, metus lobortis nisl ornare varius praesent, dictumst gravida lacus parturient semper. Pellentesque faucibus congue fusce posuere placerat dictum vitae, dui vestibulum eu sociis tempus aliquam ultricies malesuada, potenti laoreet lacus sem gravida nisi. Nostra platea sagittis hendrerit congue conubia senectus bibendum quis sapien pharetra, scelerisque nam imperdiet fermentum feugiat suspendisse viverra luctus at, semper ac consequat vitae mi gravida parturient mollis nascetur. Vel taciti justo consequat primis et blandit convallis sed, felis purus fusce a venenatis etiam aenean scelerisque, fringilla volutpat sagittis egestas rutrum id dis.</p> <p>Feugiat fermentum tortor ante ac iaculis sollicitudin ut interdum, cras orci ullamcorper potenti tristique vehicula. Molestie tortor ullamcorper rutrum turpis malesuada phasellus sem ultricies praesent mattis lobortis porta, senectus venenatis diam nostra laoreet volutpat per aptent justo elementum cum. Urna cursus vel felis cras eleifend arcu enim magnis, duis rutrum nibh nascetur cubilia interdum ultrices curae, id lacus aliquam dictumst diam fringilla lacinia.</p> <p>Luctus diam morbi eget tellus libero taciti faucibus inceptos, natoque facilisis lectus maecenas risus dapibus suscipit nibh, vel curae conubia orci imperdiet metus fusce. Condimentum massa donec luctus pharetra cum, in viverra placerat nisl litora facilisis, neque nascetur sociis dictumst. Suscipit accumsan eget rhoncus pharetra justo malesuada aliquet, suspendisse metus eleifend tincidunt varius ridiculus, convallis primis vitae curabitur quis mus.</p> <p>Gravida donec lacus molestie tortor aenean ultricies blandit per tempor, nostra penatibus orci vestibulum semper lectus vel a, montes potenti cum dapibus natoque eu volutpat nulla. Himenaeos purus nam malesuada habitasse nisl pharetra laoreet feugiat mi non, ultrices ultricies a cras ante eu venenatis ligula. Suscipit ut mus habitasse at aliquet sodales commodo justo, feugiat platea sagittis phasellus eleifend pellentesque interdum iaculis, integer cubilia montes metus hendrerit tincidunt purus.</p> <p>Vel posuere tellus dapibus eget duis cubilia, nec class vehicula libero gravida ligula, tempus urna taciti donec congue. Facilisis ridiculus congue cum dui per augue natoque, molestie hac etiam pellentesque dignissim urna class, feugiat aenean massa himenaeos penatibus ut eu, convallis purus et fusce tempus mattis. At mattis suscipit porta nostra nec facilisis sodales turpis, integer et lectus conubia justo nam congue taciti odio, fermentum semper cubilia fusce nunc purus velit.
          <button>hi</button>
  """


async def test_DV_001_device_should_work_smoke(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    iphone = playwright.devices["iPhone 6"]
    context = await browser.new_context(**iphone)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/mobile.html")
    assert await page.evaluate("() => window.innerWidth") == 375
    assert "iPhone" in await page.evaluate("() => navigator.userAgent")
    await context.close()


async def test_DV_002_device_should_support_clicking(
    playwright: Playwright, browser: Browser, server: Server
) -> None:
    iphone = playwright.devices["iPhone 6"]
    context = await browser.new_context(**iphone)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/button.html")
    button = await page.query_selector("button")
    assert button
    await page.evaluate("button => button.style.marginTop = '200px'", button)
    await button.click()
    assert await page.evaluate("result") == "Clicked"
    await context.close()


async def test_DV_003_device_should_scroll_to_click(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(
        viewport={
            "width": 400,
            "height": 400,
        },
        device_scale_factor=1,
        is_mobile=True,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/scrollable.html")
    element = await page.query_selector("#button-91")
    assert element
    await element.click()
    assert await element.text_content() == "clicked"
    await context.close()


async def test_DV_004_device_should_scroll_twice_when_emulated(
    context_factory: ContextFactory, playwright: Playwright
) -> None:
    device = playwright.devices["iPhone 6"]
    context = await context_factory(**device)
    page = await context.new_page()
    await page.set_content(SCROLL_TWICE_CONTENT)
    await page.evaluate("() => window.scroll(0, 100)")
    assert await page.evaluate("() => window.scrollY") == 100

    await page.evaluate("() => window.scroll(0, 200)")
    assert await page.evaluate("() => window.scrollY") == 200

    await context.close()


async def test_DV_005_device_should_reset_scroll_top_after_a_navigation(
    server: Server,
    context_factory: ContextFactory,
    playwright: Playwright,
    browser_name: str,
) -> None:
    if browser_name == "webkit":
        pytest.skip("skipped upstream for webkit")

    device = playwright.devices["iPhone 6"]
    context = await context_factory(**device)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/scrollable.html")
    await page.evaluate("() => window.scroll(0, 100)")

    await page.goto(server.PREFIX + "/input/scrollable2.html")
    assert await page.evaluate("() => window.scrollY") == 0
    await context.close()


async def test_DV_006_device_should_scroll_to_a_precise_position_with_mobile_scale(
    server: Server,
    context_factory: ContextFactory,
    playwright: Playwright,
    browser_name: str,
) -> None:
    if browser_name == "webkit":
        pytest.skip("skipped upstream for webkit")

    device = playwright.devices["iPhone 6"]
    context = await context_factory(**device)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/input/scrollable.html")
    assert await page.evaluate("() => document.body.scrollHeight") > 1000
    await page.evaluate("() => window.scroll(0, 100)")
    assert await page.evaluate("() => window.scrollY") == 100
    await context.close()


@pytest.mark.xfail(
    reason="python: playwright.devices drops the descriptor's screen, so screen is the viewport size",
    strict=True,
)
async def test_DV_007_device_should_emulate_viewport_and_screen_size(
    context_factory: ContextFactory, playwright: Playwright
) -> None:
    device = playwright.devices["iPhone 12"]
    context = await context_factory(**device)
    page = await context.new_page()
    await page.set_content(
        '<meta name="viewport" content="width=device-width, user-scalable=no" />'
    )

    assert (
        await page.evaluate(
            """() => ({
            width: window.screen.width,
            height: window.screen.height
        })"""
        )
        == {"width": 390, "height": 844}
    )

    assert (
        await page.evaluate(
            """() => ({
            width: window.innerWidth,
            height: window.innerHeight
        })"""
        )
        == {"width": 390, "height": 664}
    )

    await context.close()


async def test_DV_008_device_should_emulate_viewport_without_screen_size(
    context_factory: ContextFactory, playwright: Playwright
) -> None:
    device = playwright.devices["iPhone 6"]
    context = await context_factory(**device)
    page = await context.new_page()
    await page.set_content(
        '<meta name="viewport" content="width=device-width, user-scalable=no" />'
    )

    assert (
        await page.evaluate(
            """() => ({
            width: window.screen.width,
            height: window.screen.height
        })"""
        )
        == {"width": 375, "height": 667}
    )

    assert (
        await page.evaluate(
            """() => ({
            width: window.innerWidth,
            height: window.innerHeight
        })"""
        )
        == {"width": 375, "height": 667}
    )

    await context.close()
