import pytest

from playwright.async_api import Error, Page, Playwright


async def test_get_by_role_escaping(page: Page, playwright: Playwright) -> None:
    playwright.selectors.set_test_id_attribute("data-custom-id")
    await page.set_content(
        """
      <div>
        <div></div>
        <div>
          <div></div>
          <div></div>
        </div>
      </div>
      <div>
        <div class='foo bar:0' data-custom-id='One'>
        </div>
        <div class='foo bar:1' data-custom-id='Two'>
        </div>
      </div>
    """
    )
    with pytest.raises(Error) as exc_info:
        await page.locator(".foo").hover()
    assert "strict mode violation" in exc_info.value.message
    assert '<div class="foo bar:0' in exc_info.value.message
    assert '<div class="foo bar:1' in exc_info.value.message
    assert 'aka get_by_test_id("One")' in exc_info.value.message
    assert 'aka get_by_test_id("Two")' in exc_info.value.message
