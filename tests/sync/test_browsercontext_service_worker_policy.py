from playwright.sync_api import Browser
from tests.server import Server


def test_should_allow_service_workers_by_default(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    page.evaluate("() => window.activationPromise")
    context.close()


def test_block_blocks_service_worker_registration(
    browser: Browser, server: Server
) -> None:
    context = browser.new_context(service_workers="block")
    page = context.new_page()
    with page.expect_console_message(
        lambda m: "Service Worker registration blocked by Playwright" == m.text
    ):
        page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    context.close()
