import sys
from io import StringIO
from unittest.mock import patch

import pytest

from scripts.generate_sync_api import main


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
def test_generate_sync_api():
    with patch("sys.stdout", new_callable=StringIO):
        main()
