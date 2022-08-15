import pytest


@pytest.mark.only_browser("chromium")
async def test_should_work(playwright, launch_arguments) -> None:
    device_descriptor = playwright.devices["Pixel 2"]
    device_type = device_descriptor["default_browser_type"]
    browser = await playwright[device_type].launch(**launch_arguments)
    context = await browser.new_context(
        **device_descriptor,
    )
    page = await context.new_page()
    assert device_descriptor["default_browser_type"] == "chromium"
    assert browser.browser_type.name == "chromium"

    assert "Pixel 2" in device_descriptor["user_agent"]
    assert "Pixel 2" in await page.evaluate("navigator.userAgent")

    assert device_descriptor["device_scale_factor"] > 2
    assert await page.evaluate("window.devicePixelRatio") > 2

    assert device_descriptor["viewport"]["height"] > 700
    assert device_descriptor["viewport"]["height"] < 800
    inner_height = await page.evaluate("window.innerHeight")
    inner_height > 700
    inner_height < 800

    assert device_descriptor["viewport"]["width"] > 400
    assert device_descriptor["viewport"]["width"] < 500
    inner_width = await page.evaluate("window.innerWidth")
    inner_width > 400
    inner_width < 500

    assert device_descriptor["has_touch"]
    assert device_descriptor["is_mobile"]

    await browser.close()
