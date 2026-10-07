import os
import sys
import unittest
from unittest.mock import MagicMock, patch


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import yt_dlp

from downloader import DownloadError, InvalidUrlError, NoVideoError, download_video, validate_twitter_url


class TwitterDownloaderTests(unittest.TestCase):
    def test_rejects_non_twitter_urls(self):
        with self.assertRaises(InvalidUrlError):
            validate_twitter_url("https://example.com/video")

    @patch("downloader.yt_dlp.YoutubeDL")
    def test_post_without_video_has_specific_error(self, youtube_dl):
        downloader = MagicMock()
        downloader.__enter__.return_value = downloader
        downloader.extract_info.side_effect = yt_dlp.utils.DownloadError(
            "ERROR: [twitter] 123: No video could be found in this tweet"
        )
        youtube_dl.return_value = downloader

        with self.assertRaisesRegex(NoVideoError, "does not contain a downloadable video"):
            download_video("https://x.com/example/status/123")

    @patch("downloader.yt_dlp.YoutubeDL")
    def test_other_extractor_failures_remain_upstream_errors(self, youtube_dl):
        downloader = MagicMock()
        downloader.__enter__.return_value = downloader
        downloader.extract_info.side_effect = yt_dlp.utils.DownloadError("HTTP Error 503")
        youtube_dl.return_value = downloader

        with self.assertRaises(DownloadError) as raised:
            download_video("https://x.com/example/status/123")

        self.assertNotIsInstance(raised.exception, NoVideoError)


if __name__ == "__main__":
    unittest.main()
