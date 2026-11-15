"""YouTube Data API v3 uploader for long-form history documentary videos."""
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def build_youtube():
    creds = Credentials(
        token=None,
        refresh_token=config.env("YT_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.env("YT_CLIENT_ID"),
        client_secret=config.env("YT_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def publish_slots(n: int) -> list[datetime]:
    """Next n publish times (UTC) from PUBLISH_TIMES in PUBLISH_TIMEZONE."""
    tz = ZoneInfo(config.PUBLISH_TIMEZONE)
    now = datetime.now(tz) + timedelta(minutes=20)
    times = [tuple(map(int, t.strip().split(":"))) for t in config.PUBLISH_TIMES]
    slots, day = [], now.date()
    while len(slots) < n:
        for h, m in times:
            dt = datetime(day.year, day.month, day.day, h, m, tzinfo=tz)
            if dt > now and len(slots) < n:
                slots.append(dt.astimezone(timezone.utc))
        day += timedelta(days=1)
    return slots


def _clean(text: str, limit: int) -> str:
    return text.replace("<", "").replace(">", "")[:limit]


def _fit_tags(tags: list[str], limit: int = 480) -> list[str]:
    out, total = [], 0
    for t in tags:
        t = _clean(t.strip().lstrip("#"), 60)
        cost = len(t) + (2 if " " in t else 0) + 1
        if t and total + cost <= limit:
            out.append(t)
            total += cost
    return out


def upload(youtube, video_path: Path, title: str, description: str, tags: list[str], publish_at: datetime | None = None) -> str:
    status = {
        "selfDeclaredMadeForKids": config.MADE_FOR_KIDS,
        "embeddable": True,
        "license": "youtube",
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        status["privacyStatus"] = "public"

    body = {
        "snippet": {
            "title": _clean(title, 100),
            "description": _clean(description, 4900),
            "tags": _fit_tags(tags),
            "categoryId": config.CATEGORY_ID,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en-US",
        },
        "status": status,
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=16 << 20, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response, retries = None, 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except Exception as exc:
            retries += 1
            if retries > 5:
                raise
            print(f"[upload] chunk error, retrying: {exc}")
            time.sleep(2 ** retries)
    return response["id"]


def set_thumbnail(youtube, video_id: str, thumbnail_path: Path) -> bool:
    """Set custom 16:9 thumbnail for the video."""
    if not thumbnail_path or not thumbnail_path.exists():
        return False
    try:
        media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"   custom 16:9 thumbnail set for {video_id}")
        return True
    except Exception as exc:
        print(f"   [thumbnail] note: custom thumbnail upload skipped ({exc})")
        return False
