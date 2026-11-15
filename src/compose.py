"""Assemble 1920x1080 horizontal documentary video with Ken Burns motion, atmospheric overlays, music & stamps."""
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config

W, H, FPS = config.WIDTH, config.HEIGHT, config.FPS
OVERLAYS_DIR = config.ROOT / "assets" / "overlays"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _run(cmd, timeout: int = 300):
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{res.stderr[-2000:]}")


def make_chapter_badge(chapter_name: str, out_path: Path):
    """Generate a sleek documentary lower-third / upper-left stamp."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    tag_font = _font(28)
    title_font = _font(46)

    tag_text = "📍 HISTORICAL RECORD"
    title_text = chapter_name.upper().strip()

    tw = max(draw.textlength(tag_text, font=tag_font), draw.textlength(title_text, font=title_font))
    box_w = int(tw + 70)
    box_h = 110

    bx, by = 80, 80
    # Semi-transparent dark background card
    draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=14, fill=(10, 10, 12, 210))
    # Red accent left bar
    draw.rounded_rectangle([bx, by, bx + 10, by + box_h], radius=5, fill=(229, 9, 20, 255))

    draw.text((bx + 26, by + 16), tag_text, font=tag_font, fill="#E50914")
    draw.text((bx + 26, by + 50), title_text, font=title_font, fill="#FFFFFF")

    img.save(out_path)


def render_scene(media: Path, kind: str, audio: Path, out: Path, duration: float, idx: int, chapter_name: str = ""):
    """Render a single scene with Ken Burns motion, atmospheric floating particles, and chapter badges."""
    length = duration + 0.2
    frames = int(length * FPS) + 2

    # Choose particle overlay (embers for dramatic moments, dust for ambient mystery)
    overlay_path = None
    if OVERLAYS_DIR.exists():
        embers = OVERLAYS_DIR / "embers.mp4"
        dust = OVERLAYS_DIR / "dust.mp4"
        if idx % 2 == 1 and embers.exists():
            overlay_path = embers
        elif dust.exists():
            overlay_path = dust

    # Generate chapter badge if chapter_name is given
    badge_path = None
    if chapter_name and idx in (0, 3, 6, 9):
        badge_path = out.with_suffix(".badge.png")
        try:
            make_chapter_badge(chapter_name, badge_path)
        except Exception:
            badge_path = None

    try:
        inputs = []
        filter_parts = []

        if kind == "video":
            inputs.extend(["-stream_loop", "-1", "-i", str(media)])
            filter_parts.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},vignette=PI/5[base]")
        else:
            zoom_dir = "min(zoom+0.0007,1.20)" if idx % 2 == 0 else "max(1.20-on*0.0007,1.0)"
            inputs.extend(["-i", str(media)])
            filter_parts.append(
                f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                f"zoompan=z='{zoom_dir}':d={frames}:x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},vignette=PI/4[base]"
            )

        current_v = "[base]"
        input_idx = 1

        # Particle Overlay Blend (Screen mode)
        if overlay_path and overlay_path.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(overlay_path)])
            filter_parts.append(f"[{input_idx}:v]scale={W}:{H},setsar=1,format=yuv420p[ov]")
            filter_parts.append(f"{current_v}[ov]blend=all_mode='screen':all_opacity=0.55,format=yuv420p[v_part]")
            current_v = "[v_part]"
            input_idx += 1

        # Badge Overlay (fade in at 0.5s, stay until 5.0s, fade out)
        if badge_path and badge_path.exists():
            inputs.extend(["-i", str(badge_path)])
            filter_parts.append(f"{current_v}[{input_idx}:v]overlay=0:0:enable='between(t,0.3,5.5)',format=yuv420p[v_badged]")
            current_v = "[v_badged]"
            input_idx += 1

        # Audio Input
        audio_idx = input_idx
        inputs.extend(["-i", str(audio)])
        filter_parts.append(f"[{audio_idx}:a]apad[a]")

        complex_filter = ";".join(filter_parts)

        _run([
            "ffmpeg", "-y", *inputs,
            "-filter_complex", complex_filter,
            "-map", current_v, "-map", "[a]",
            "-t", f"{length:.2f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            str(out),
        ])
    finally:
        if badge_path and badge_path.exists():
            badge_path.unlink(missing_ok=True)


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
    tracks = []
    if config.MUSIC_DIR.exists():
        tracks = list(config.MUSIC_DIR.glob("*.mp3")) + list(config.MUSIC_DIR.glob("*.ogg")) + list(config.MUSIC_DIR.glob("*.wav"))
    if not tracks:
        return video
    track = random.choice(tracks)
    _run([
        "ffmpeg", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(track),
        "-filter_complex",
        f"[1:a]volume={config.MUSIC_VOLUME}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ])
    return out
