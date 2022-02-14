from typing import Dict

import pytest

from playwright.sync_api import sync_playwright
from tests.server import Server


def test_events(browser_name: str, launch_arguments: Dict, server: Server) -> None:
    with pytest.raises(Exception, match="fail"):

        def fail() -> None:
            raise Exception("fail")

        with sync_playwright() as p:
            with p[browser_name].launch(**launch_arguments) as browser:
                with browser.new_page() as page:
                    page.on("response", lambda _: fail())
                    page.goto(server.PREFIX + "/grid.html")
