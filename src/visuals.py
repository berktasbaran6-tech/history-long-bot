"""Fetch historical paintings and archival media from Wikimedia Commons + Pexels/Pixabay."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import requests

import config

USER_AGENT = "HistoryDocumentaryBot/1.0 (https://github.com/berktasbaran6-tech/history-long-bot)"


SAFE_ELEMENTAL_WORDS = {"fire", "flame", "candle", "candles", "torches", "storm", "clouds", "lightning", "smoke", "fog", "mist", "ocean", "waves"}
FORBIDDEN_MODERN_WORDS = {"person", "people", "man", "woman", "crowd", "city", "street", "building", "rome", "italy", "tourist", "modern", "court", "hall", "cathedral", "church", "palace"}


def _is_safe_elemental_query(query: str) -> bool:
    """Only allow purely timeless elemental nature videos (fire, candles, storm)."""
    words = set(query.lower().split())
    if words & FORBIDDEN_MODERN_WORDS:
        return False
    return bool(words & SAFE_ELEMENTAL_WORDS)


def _fetch_wikimedia(query: str, work_dir: Path, idx: int) -> Path | None:
    """Fetch high-resolution public domain museum painting, engraving, or manuscript from Wikimedia Commons."""
    try:
        # Guarantee historical art terms
        art_query = query
        lower_q = query.lower()
        if not any(k in lower_q for k in ("painting", "engraving", "manuscript", "fresco", "sculpture", "bust", "tapestry", "woodcut")):
            art_query = f"{query} painting"

        url = (
            "https://commons.wikimedia.org/w/api.php?"
            "action=query&format=json&generator=search&"
            f"gsrsearch={urllib.parse.quote(art_query)}&gsrnamespace=6&"
            "prop=imageinfo&iiprop=url|size|mime&gsrlimit=10"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", {})
        candidates = []
        for pid, pdata in pages.items():
            title = pdata.get("title", "").lower()
            # Reject modern photos
            if any(bad in title for bad in ("tourist", "selfie", "vacation", "2024", "2025", "2026", "renovation")):
                continue

            infos = pdata.get("imageinfo", [])
            if not infos:
                continue
            info = infos[0]
            mime = info.get("mime", "")
            width = info.get("width", 0)
            height = info.get("height", 0)
            url_img = info.get("url")

            # Prefer high-res jpg/png images
            if mime in ("image/jpeg", "image/png", "image/webp") and width >= 700 and url_img:
                candidates.append((width * height, url_img))

        if not candidates:
            return None

        # Pick highest resolution
        candidates.sort(reverse=True)
        best_url = candidates[0][1]

        ext = ".jpg" if "png" not in best_url.lower() else ".png"
        out_file = work_dir / f"media_{idx}{ext}"
        dreq = urllib.request.Request(best_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(dreq, timeout=20) as dresp, open(out_file, "wb") as f:
            f.write(dresp.read())

        if out_file.stat().st_size > 10000:
            # Normalize and downscale any giant museum archive scans to avoid ffmpeg crashes
            try:
                from PIL import Image
                Image.MAX_IMAGE_PIXELS = None
                with Image.open(out_file) as im:
                    im = im.convert("RGB")
                    w, h = im.size
                    if w > 2560 or h > 1440:
                        im.thumbnail((2560, 1440), Image.Resampling.LANCZOS)
                    out_jpg = work_dir / f"media_{idx}.jpg"
                    im.save(out_jpg, "JPEG", quality=90)
                    if out_jpg != out_file and out_file.exists():
                        out_file.unlink(missing_ok=True)
                    return out_jpg
            except Exception as resize_err:
                print(f"   [wikimedia] image resize note: {resize_err}")
            return out_file
    except Exception as exc:
        print(f"   [wikimedia] error searching '{query}': {exc}")
    return None


def _fetch_pixabay(query: str, work_dir: Path, idx: int) -> tuple[Path, str] | None:
    """Fetch purely elemental timeless video (candle, fire, storm) from Pixabay."""
    key = os.getenv("PIXABAY_API_KEY", "")
    if not key or not _is_safe_elemental_query(query):
        return None
    try:
        v_url = f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(query)}&per_page=5"
        r = requests.get(v_url, timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            v_hit = hits[0]["videos"].get("large", hits[0]["videos"].get("medium", {}))
            dl_url = v_hit.get("url")
            if dl_url:
                out_path = work_dir / f"media_{idx}.mp4"
                with requests.get(dl_url, stream=True, timeout=25) as stream:
                    with open(out_path, "wb") as f:
                        for chunk in stream.iter_content(chunk_size=8192):
                            f.write(chunk)
                return out_path, "video"
    except Exception as exc:
        print(f"   [pixabay] error: {exc}")
    return None


import os

def fetch_media(wikimedia_query: str, pexels_query: str, work_dir: Path, idx: int) -> tuple[Path, str]:
    """Fetch 100% authentic historical museum art or purely timeless elemental footage (ZERO modern world)."""
    # 1. First priority: genuine historical painting, manuscript, or engraving from Wikimedia Commons
    wiki_file = _fetch_wikimedia(wikimedia_query, work_dir, idx)
    if wiki_file:
        return wiki_file, "image"

    # 2. Try simpler historical art query on Wikimedia
    words = [w for w in wikimedia_query.split() if w.lower() not in ("painting", "oil", "ancient", "the", "and", "in", "of")]
    if words:
        simple_query = " ".join(words[:2]) + " painting"
        wiki_file2 = _fetch_wikimedia(simple_query, work_dir, idx)
        if wiki_file2:
            return wiki_file2, "image"

    # 3. Only if query is strictly elemental (fire, candle, storm), allow motion video
    if _is_safe_elemental_query(pexels_query):
        pix = _fetch_pixabay(pexels_query, work_dir, idx)
        if pix:
            return pix

    # 4. Final emergency fallback: museum medieval oil painting (Never modern photos!)
    emergency = _fetch_wikimedia("medieval oil painting historical", work_dir, idx)
    if emergency:
        return emergency, "image"

    raise RuntimeError(f"Could not find authentic historical media for scene {idx} ('{wikimedia_query}')")
