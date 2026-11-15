"""Text-to-speech for history documentary narration using edge-tts."""
import asyncio
from pathlib import Path

import edge_tts

import config


async def _synthesize_async(text: str, out_path: Path):
    communicate = edge_tts.Communicate(
        text=text,
        voice=config.TTS_VOICE,
        rate=config.TTS_RATE,
    )
    await communicate.save(str(out_path))


def synthesize(text: str, out_path: Path) -> float:
    """Generate audio and return duration in seconds using ffmpeg probe."""
    import subprocess

    asyncio.run(_synthesize_async(text, out_path))

    # Probe duration
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())
