"""
YouTube URL parsing.

The CMS stores the canonical video id rather than whatever URL shape the user
happened to paste, so the frontend never has to parse URLs and every stored
reference is comparable.
"""

import re
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError

#: A video id is exactly 11 URL-safe base64 characters.
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def extract_video_id(url):
    """Return the video id from any supported YouTube URL shape.

    Handles:
        https://www.youtube.com/watch?v=ID
        https://youtu.be/ID
        https://www.youtube.com/embed/ID
        https://www.youtube.com/shorts/ID
        https://www.youtube.com/live/ID
        https://www.youtube.com/v/ID

    Raises ``ValidationError`` for anything else. An allowlist of hosts is used
    deliberately: a substring check for "youtube" would happily accept
    `https://youtube.evil.example/`.
    """
    if not url or not isinstance(url, str):
        raise ValidationError("A YouTube URL is required.")

    parsed = urlparse(url.strip())

    if parsed.scheme not in ("http", "https"):
        raise ValidationError("The URL must start with http:// or https://")

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValidationError(
            "That is not a YouTube URL. Supported hosts: youtube.com, youtu.be."
        )

    candidate = None

    if host in ("youtu.be", "www.youtu.be"):
        candidate = parsed.path.lstrip("/").split("/")[0]
    else:
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts and path_parts[0] == "watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in ("embed", "shorts", "live", "v"):
            candidate = path_parts[1]

    if not candidate or not VIDEO_ID.match(candidate):
        raise ValidationError(
            "No video id could be found in that URL. Paste the full link to a "
            "single video."
        )

    return candidate


def canonical_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def thumbnail_url(video_id):
    """Highest-quality thumbnail that is guaranteed to exist for every video.

    `maxresdefault` is not generated for every upload and 404s when absent;
    `hqdefault` always exists.
    """
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
