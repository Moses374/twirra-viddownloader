"""Fetch Twitter/X videos with yt-dlp and clean up temp files after serving."""
import os
import re
import uuid

import yt_dlp

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/twirra_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

_TWITTER_URL_RE = re.compile(
    r"^https?://(www\.)?(twitter\.com|x\.com)/\w+/status/\d+", re.IGNORECASE
)


class InvalidUrlError(ValueError):
    pass


class DownloadError(RuntimeError):
    pass


class NoVideoError(DownloadError):
    """The X post exists, but it has no downloadable video."""


_NO_VIDEO_MESSAGES = (
    "no video could be found",
    "no downloadable video",
    "there is no video",
)


def _is_no_video_error(message: str) -> bool:
    normalized = message.casefold()
    return any(fragment in normalized for fragment in _NO_VIDEO_MESSAGES)


def validate_twitter_url(url: str) -> None:
    if not _TWITTER_URL_RE.match(url.strip()):
        raise InvalidUrlError("URL must be a valid Twitter/X status link")


def download_video(url: str) -> str:
    """Downloads the video for a tweet URL and returns the local file path."""
    validate_twitter_url(url)

    job_id = str(uuid.uuid4())
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": 500 * 1024 * 1024,  # 500MB safety cap
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as exc:
        message = str(exc)
        if _is_no_video_error(message):
            raise NoVideoError("This post does not contain a downloadable video") from exc
        raise DownloadError(message) from exc

    if not os.path.exists(filename):
        raise DownloadError("Download completed but output file was not found")

    return filename


def cleanup_file(path: str) -> None:
    try:
        if os.path.exists(path) and os.path.commonpath([os.path.abspath(path), os.path.abspath(DOWNLOAD_DIR)]) == os.path.abspath(DOWNLOAD_DIR):
            os.remove(path)
    except OSError:
        pass
