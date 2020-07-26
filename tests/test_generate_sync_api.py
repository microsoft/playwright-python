from io import StringIO
from unittest.mock import patch

from scripts.generate_sync_api import main


def test_generate_sync_api():
    with patch("sys.stdout", new_callable=StringIO):
        main()
