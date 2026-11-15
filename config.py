"""Central configuration for the Long-Form History Documentary Bot.

Produces high-retention 16:9 (1920x1080) history documentaries:
  - Deep-dive storytelling with historical authenticity
  - Museum & archival paintings from Wikimedia Commons + cinematic B-roll
  - Authoritative documentary narration + Ken Burns motion
  - 16:9 high-CTR thumbnail with curiosity hooks
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Local testing: read KEY=VALUE lines from .env
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8-sig").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

def env(key: str, default: str = "") -> str:
    val = os.getenv(key, default)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val

OUTPUT_DIR = ROOT / "output"
HISTORY_FILE = ROOT / "data" / "history.json"
MUSIC_DIR = ROOT / "assets" / "music"

# --- Production -----------------------------------------------------------
VIDEOS_PER_DAY = int(os.getenv("VIDEOS_PER_DAY", "1"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-ChristopherNeural")  # deep, viral, authoritative voice
TTS_RATE = os.getenv("TTS_RATE", "-3%")  # deliberate documentary pacing
WIDTH, HEIGHT, FPS = 1920, 1080, 30
MUSIC_VOLUME = 0.08  # background music under documentary narration

# --- Publishing -----------------------------------------------------------
# Peak long-form viewing time: Evening Prime
PUBLISH_TIMEZONE = os.getenv("PUBLISH_TIMEZONE", "America/New_York")
PUBLISH_TIMES = os.getenv("PUBLISH_TIMES", "14:00").split(",")  # 14:00 US Eastern = 22:00 TR
CATEGORY_ID = os.getenv("CATEGORY_ID", "27")  # 27 = Education
MADE_FOR_KIDS = False  # Enables full monetization & comments

DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

# --- Trend discovery ------------------------------------------------------
TREND_QUERIES = [
    "dark history documentary",
    "untold history stories",
    "bizarre historical events documentary",
    "ancient mysteries documentary",
    "craziest rulers in history",
    "ancient rome documentary",
    "medieval history untold",
]
