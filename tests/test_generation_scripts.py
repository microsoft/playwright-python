import sys
from io import StringIO
from unittest.mock import patch

import pytest

CAN_RUN_GENERATION_SCRIPT = sys.version_info >= (3, 8)

if CAN_RUN_GENERATION_SCRIPT:
    from scripts.generate_async_api import main as generate_async_api
    from scripts.generate_sync_api import main as generate_sync_api


@pytest.mark.skipif(
    not CAN_RUN_GENERATION_SCRIPT, reason="requires python3.8 or higher"
)
@patch("sys.stderr", new_callable=StringIO)
@patch("sys.stdout", new_callable=StringIO)
def test_generate_sync_api(stdout, stderr):
    generate_sync_api()


@pytest.mark.skipif(
    not CAN_RUN_GENERATION_SCRIPT, reason="requires python3.8 or higher"
)
@patch("sys.stderr", new_callable=StringIO)
@patch("sys.stdout", new_callable=StringIO)
def test_generate_async_api(stdout, stderr):
    generate_async_api()
