"""Fetch historical paintings and archival media from Wikimedia Commons + Pexels/Pixabay."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import requests

import config

USER_AGENT = "HistoryDocumentaryBot/1.0 (https://github.com/berktasbaran6-tech/history-long-bot)"


def _fetch_wikimedia(query: str, work_dir: Path, idx: int) -> Path | None:
    """Fetch high-resolution public domain museum painting or photo from Wikimedia Commons."""
    try:
        url = (
            "https://commons.wikimedia.org/w/api.php?"
            "action=query&format=json&generator=search&"
            f"gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&"
            "prop=imageinfo&iiprop=url|size|mime&gsrlimit=8"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", {})
        candidates = []
        for pid, pdata in pages.items():
            infos = pdata.get("imageinfo", [])
            if not infos:
                continue
            info = infos[0]
            mime = info.get("mime", "")
            width = info.get("width", 0)
            height = info.get("height", 0)
            url_img = info.get("url")

            # Prefer high-res jpg/png images
            if mime in ("image/jpeg", "image/png", "image/webp") and width >= 800 and url_img:
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
            return out_file
    except Exception as exc:
        print(f"   [wikimedia] error searching '{query}': {exc}")
    return None


def _fetch_pixabay(query: str, work_dir: Path, idx: int) -> tuple[Path, str] | None:
    """Fallback: fetch atmospheric video or image from Pixabay."""
    key = os.getenv("PIXABAY_API_KEY", "")
    if not key:
        return None
    try:
        # Try video first
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

        # Try image
        i_url = f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(query)}&per_page=5&image_type=photo"
        r = requests.get(i_url, timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            dl_url = hits[0].get("largeImageURL")
            if dl_url:
                out_path = work_dir / f"media_{idx}.jpg"
                with requests.get(dl_url, stream=True, timeout=20) as stream:
                    with open(out_path, "wb") as f:
                        for chunk in stream.iter_content(chunk_size=8192):
                            f.write(chunk)
                return out_path, "image"
    except Exception as exc:
        print(f"   [pixabay] error: {exc}")
    return None


import os

def fetch_media(wikimedia_query: str, pexels_query: str, work_dir: Path, idx: int) -> tuple[Path, str]:
    """Fetch the best historical or atmospheric media for the scene."""
    # For dynamic visual pacing, interleave real HD atmospheric motion video on scenes 1, 4, 7, 10
    if idx % 3 == 1 and pexels_query:
        pix = _fetch_pixabay(pexels_query, work_dir, idx)
        if pix and pix[1] == "video":
            return pix

    # 1. First priority: genuine historical painting or archival photo from Wikimedia Commons
    wiki_file = _fetch_wikimedia(wikimedia_query, work_dir, idx)
    if wiki_file:
        return wiki_file, "image"

    # 2. Try simpler query on Wikimedia
    words = wikimedia_query.split()
    if len(words) > 2:
        simple_query = " ".join(words[:2]) + " painting"
        wiki_file2 = _fetch_wikimedia(simple_query, work_dir, idx)
        if wiki_file2:
            return wiki_file2, "image"

    # 3. Fallback to atmospheric Pixabay footage
    pix = _fetch_pixabay(pexels_query, work_dir, idx)
    if pix:
        return pix

    # 4. Final emergency fallback: generic ancient history painting
    emergency = _fetch_wikimedia("ancient history painting", work_dir, idx)
    if emergency:
        return emergency, "image"

    raise RuntimeError(f"Could not find any media for scene {idx} ('{wikimedia_query}')")
