"""Fetch trending and top-performing long-form history video topics via YouTube Data API."""
import config

FALLBACK_TOPICS = [
    "The Emperor Who Declared War on the Ocean: Caligula's Mad War",
    "The 1518 Dancing Plague: The Medieval Town That Danced to Death",
    "The Ghost Army of World War II: The Secret Deception Unit",
    "Why Did the Bronze Age Civilizations Collapse All at Once?",
    "The Corpse Synod: The Day a Dead Pope Was Put on Trial",
    "The Night Witches: The Female Soviet Pilots Who Terrified the Nazis",
    "The Great Molasses Flood: Boston's Most Bizarre Disaster",
    "The Sacred Band of Thebes: The 300 Unbeatable Ancient Warriors",
]


def fetch_trending(youtube, queries: list[str]) -> list[str]:
    """Return top-performing video titles from search queries to seed topic planning."""
    if youtube is None:
        return FALLBACK_TOPICS

    titles = []
    for q in queries:
        try:
            req = youtube.search().list(
                part="snippet",
                q=q,
                type="video",
                videoDuration="medium",  # 4-20 minutes
                order="viewCount",
                regionCode="US",
                relevanceLanguage="en",
                maxResults=8,
            )
            res = req.execute()
            for item in res.get("items", []):
                t = item.get("snippet", {}).get("title", "").strip()
                if t and t not in titles:
                    titles.append(t)
        except Exception as exc:
            print(f"[trends] search error for '{q}': {exc}")

    return titles if titles else FALLBACK_TOPICS
