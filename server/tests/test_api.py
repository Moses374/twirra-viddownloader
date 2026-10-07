import os
import sys
import unittest
from unittest.mock import patch


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from fastapi import BackgroundTasks, HTTPException

import main
from downloader import NoVideoError


class DownloadApiTests(unittest.TestCase):
    @patch("main.download_video", side_effect=NoVideoError("This post does not contain a downloadable video"))
    def test_post_without_video_returns_422(self, _download_video):
        endpoint = getattr(main.download, "__wrapped__", main.download)
        with self.assertRaises(HTTPException) as raised:
            endpoint(
                request=object(),
                url="https://x.com/example/status/123",
                background_tasks=BackgroundTasks(),
                user="test-user",
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail,
            "This post does not contain a downloadable video",
        )


if __name__ == "__main__":
    unittest.main()
