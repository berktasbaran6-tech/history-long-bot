"""Assemble 1920x1080 horizontal documentary video with Ken Burns motion, music & transitions."""
import random
import subprocess
from pathlib import Path

import config

W, H, FPS = config.WIDTH, config.HEIGHT, config.FPS


def _run(cmd, timeout: int = 300):
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{res.stderr[-2000:]}")


def render_scene(media: Path, kind: str, audio: Path, out: Path, duration: float, idx: int):
    """Render a single scene with Ken Burns motion (for images) or seamless scale (for video)."""
    length = duration + 0.2  # tiny breathing room between scenes
    frames = int(length * FPS) + 2

    if kind == "video":
        inputs = ["-stream_loop", "-1", "-i", str(media), "-i", str(audio)]
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    else:
        # Alternating zoom-in and zoom-out for visual dynamism
        zoom_direction = "min(zoom+0.0006,1.18)" if idx % 2 == 0 else "max(1.18-on*0.0006,1.0)"
        inputs = ["-i", str(media), "-i", str(audio)]
        vf = (
            f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
            f"zoompan=z='{zoom_direction}':d={frames}:x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}"
        )

    # Add subtle cinematic vignette
    vf += ",vignette=PI/5"

    _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex",
        f"[0:v]{vf},setsar=1,format=yuv420p[v];[1:a]apad[a]",
        "-map", "[v]", "-map", "[a]", "-t", f"{length:.2f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(out),
    ])


def concat(scenes: list[Path], out: Path):
    """Concatenate rendered scenes into a continuous documentary."""
    list_file = out.with_suffix(".txt")
    list_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in scenes), encoding="utf-8")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", "-movflags", "+faststart", str(out),
    ])


def add_music(video: Path, out: Path) -> Path:
    """Mix an atmospheric royalty-free background track under the narration."""
    tracks = list(config.MUSIC_DIR.glob("*.mp3")) if config.MUSIC_DIR.exists() else []
    if not tracks:
        return video
    _run([
        "ffmpeg", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(random.choice(tracks)),
        "-filter_complex",
        f"[1:a]volume={config.MUSIC_VOLUME}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ])
    return out
