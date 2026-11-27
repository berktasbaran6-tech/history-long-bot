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


def render_scene(media: Path, kind: str, audio: Path, out: Path, duration: float, idx: int, chapter_name: str = "", show_badge: bool = False):
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

    # Generate chapter badge when a new chapter begins
    badge_path = None
    if show_badge and chapter_name:
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

        # Particle Overlay Blend (Screen mode in planar RGB to preserve authentic colors with zero purple tint)
        if overlay_path and overlay_path.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(overlay_path)])
            filter_parts.append(f"{current_v}format=gbrp[base_rgb]")
            filter_parts.append(f"[{input_idx}:v]scale={W}:{H},setsar=1,format=gbrp[ov_rgb]")
            filter_parts.append(f"[base_rgb][ov_rgb]blend=all_mode='screen':all_opacity=0.38,format=yuv420p[v_part]")
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

        try:
            _run([
                "ffmpeg", "-y", *inputs,
                "-filter_complex", complex_filter,
                "-map", current_v, "-map", "[a]",
                "-t", f"{length:.2f}", "-r", str(FPS),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                str(out),
            ])
        except Exception as ffmpeg_err:
            print(f"   [compose] scene {idx} ffmpeg error ({ffmpeg_err}), using solid atmospheric fallback")
            _run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0x0f0e13:s={WIDTH}x{HEIGHT}:r={FPS}:d={length:.2f}",
                "-i", str(audio),
                "-t", f"{length:.2f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                str(out),
            ])
    finally:
        if badge_path and badge_path.exists():
            badge_path.unlink(missing_ok=True)


def media_duration(path: Path) -> float:
    """Return duration of media file in seconds using ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def render_outro(media: Path, out: Path, duration: float = 12.0):
    """Render a silent, reflective 12-second outro with ambient particles, ending card, and fade to black."""
    frames = int(duration * FPS) + 2
    fade_start = duration - 3.0

    # Create sleek, cinematic outro card
    card_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_img)
    tag_font = _font(28)
    title_font = _font(50)
    sub_font = _font(28)

    cx, cy = W // 2, H // 2
    bw, bh = 820, 210
    bx, by = cx - bw // 2, cy - bh // 2

    # Dark rounded card with subtle gold/red accent line
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16, fill=(10, 10, 14, 220))
    draw.rounded_rectangle([bx, by, bx + bw, by + 5], radius=3, fill=(229, 9, 20, 255))

    tag = "ARCHIVE RECORD // COMPLETE"
    title = "UNTOLD HISTORIES"
    sub = "SUBSCRIBE FOR DAILY HISTORICAL INVESTIGATIONS"

    draw.text((cx, by + 42), tag, font=tag_font, fill="#E50914", anchor="mm")
    draw.text((cx, by + 100), title, font=title_font, fill="#FFFFFF", anchor="mm")
    draw.text((cx, by + 158), sub, font=sub_font, fill="#CCCCCC", anchor="mm")

    badge_path = out.with_suffix(".outro_card.png")
    card_img.save(badge_path)

    # Silent audio track
    silent_audio = out.with_suffix(".silent.wav")
    _run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{duration:.2f}", "-c:a", "pcm_s16le", str(silent_audio)
    ])

    overlay_path = None
    if OVERLAYS_DIR.exists():
        embers = OVERLAYS_DIR / "embers.mp4"
        dust = OVERLAYS_DIR / "dust.mp4"
        overlay_path = dust if dust.exists() else embers

    try:
        inputs = ["-i", str(media)]
        filter_parts = [
            f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
            f"zoompan=z='min(zoom+0.0004,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"fade=t=out:st={fade_start:.2f}:d=3.0:color=black[base]"
        ]

        current_v = "[base]"
        input_idx = 1

        if overlay_path and overlay_path.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(overlay_path)])
            filter_parts.append(f"{current_v}format=gbrp[base_rgb]")
            filter_parts.append(f"[{input_idx}:v]scale={W}:{H},setsar=1,format=gbrp[ov_rgb]")
            filter_parts.append(f"[base_rgb][ov_rgb]blend=all_mode='screen':all_opacity=0.35,format=yuv420p[v_part]")
            filter_parts.append(f"[v_part]fade=t=out:st={fade_start:.2f}:d=3.0:color=black[v_part_fade]")
            current_v = "[v_part_fade]"
            input_idx += 1

        inputs.extend(["-i", str(badge_path)])
        filter_parts.append(f"{current_v}[{input_idx}:v]overlay=0:0:enable='between(t,0.8,{fade_start:.2f})',format=yuv420p[v_card]")
        current_v = "[v_card]"
        input_idx += 1

        inputs.extend(["-i", str(silent_audio)])
        filter_parts.append(f"[{input_idx}:a]apad[a]")

        _run([
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", current_v, "-map", "[a]",
            "-t", f"{duration:.2f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            str(out),
        ])
    finally:
        badge_path.unlink(missing_ok=True)
        silent_audio.unlink(missing_ok=True)


def concat(scenes: list[Path], out: Path):
    """Concatenate rendered scenes into a continuous documentary."""
    list_file = out.with_suffix(".txt")
    list_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in scenes), encoding="utf-8")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", "-movflags", "+faststart", str(out),
    ])


def add_music(video: Path, out: Path) -> Path:
    """Mix an atmospheric royalty-free background track under narration with smooth outro fade."""
    tracks = []
    if config.MUSIC_DIR.exists():
        tracks = list(config.MUSIC_DIR.glob("*.mp3")) + list(config.MUSIC_DIR.glob("*.ogg")) + list(config.MUSIC_DIR.glob("*.wav"))
    if not tracks:
        return video
    track = random.choice(tracks)

    try:
        dur = media_duration(video)
        fade_st = max(0.0, dur - 3.5)
        fade_filter = f"[1:a]volume={config.MUSIC_VOLUME},afade=t=out:st={fade_st:.2f}:d=3.5[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={max(0.0, dur - 1.0):.2f}:d=1.0[a]"
    except Exception:
        fade_filter = f"[1:a]volume={config.MUSIC_VOLUME}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]"

    _run([
        "ffmpeg", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(track),
        "-filter_complex", fade_filter,
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ])
    return out


def make_short_caption(text: str, out_path: Path, max_w: int = 920):
    """Generate high-contrast bold subtitle overlay for 9:16 vertical Shorts."""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(72)

    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=font) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    line_h = 92
    total_h = line_h * len(lines[:3])
    top = int(1920 * 0.68) - total_h // 2

    # Rounded dark translucent box
    draw.rounded_rectangle([50, top - 24, 1080 - 50, top + total_h + 20], radius=28, fill=(8, 8, 12, 160))

    colors = ["#FFFFFF", "#FFD700", "#FFFFFF"]
    for i, l in enumerate(lines[:3]):
        w = draw.textlength(l, font=font)
        draw.text(((1080 - w) / 2, top + i * line_h), l, font=font,
                  fill=colors[i % len(colors)], stroke_width=12, stroke_fill="black")

    img.save(out_path)


def make_short_cta_card(out_path: Path):
    """Call-To-Action card at the end of the Short directing to the full 14-min documentary."""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    tag_font = _font(36)
    main_font = _font(52)
    sub_font = _font(34)

    bx, by = 60, 1420
    bw, bh = 960, 240

    # Dark rounded card with red accent line
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=24, fill=(10, 10, 16, 235))
    draw.rounded_rectangle([bx, by, bx + bw, by + 8], radius=4, fill=(229, 9, 20, 255))

    draw.text((540, by + 45), "🏛️ UNTOLD HISTORIES", font=tag_font, fill="#E50914", anchor="mm")
    draw.text((540, by + 115), "WATCH FULL 14-MIN INVESTIGATION", font=main_font, fill="#FFFFFF", anchor="mm")
    draw.text((540, by + 185), "👉 LINK IN COMMENTS & DESCRIPTION", font=sub_font, fill="#FFD700", anchor="mm")

    img.save(out_path)


def render_teaser_short(script, work_dir: Path, out_path: Path) -> Path | None:
    """Assemble a high-retention 45-55 second vertical 9:16 teaser Short from the opening scenes."""
    short_scenes = []
    total_dur = 0.0

    # Pick opening hook scenes up to ~48-52s
    selected_indices = []
    for i in range(len(script.scenes)):
        audio_file = work_dir / f"voice_{i:02d}.mp3"
        if not audio_file.exists():
            continue
        dur = media_duration(audio_file)
        if total_dur + dur <= 56.0 or len(selected_indices) < 3:
            selected_indices.append(i)
            total_dur += dur + 0.2
            if total_dur >= 45.0:
                break

    if not selected_indices:
        return None

    cta_badge = work_dir / "short_cta.png"
    make_short_cta_card(cta_badge)

    try:
        for seq, i in enumerate(selected_indices):
            audio = work_dir / f"voice_{i:02d}.mp3"
            dur = media_duration(audio)
            length = dur + 0.2
            frames = int(length * FPS) + 2

            # Find visual media
            media = work_dir / f"media_{i}.jpg"
            kind = "image"
            if not media.exists():
                media = work_dir / f"media_{i}.mp4"
                kind = "video"
            if not media.exists():
                media = work_dir / "media_0.jpg"
                kind = "image"

            cap_badge = work_dir / f"cap_{i:02d}.png"
            scene_obj = script.scenes[i]
            short_text = " ".join(scene_obj.narration.split()[:14])
            make_short_caption(short_text, cap_badge)

            is_last = (seq == len(selected_indices) - 1)
            out_vscene = work_dir / f"vscene_{i:02d}.mp4"

            inputs = []
            filter_parts = []

            if kind == "video":
                inputs.extend(["-stream_loop", "-1", "-i", str(media)])
                filter_parts.append(f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},vignette=PI/4[base]")
            else:
                inputs.extend(["-i", str(media)])
                zoom_dir = "min(zoom+0.0006,1.22)" if i % 2 == 0 else "max(1.22-on*0.0006,1.0)"
                filter_parts.append(
                    f"[0:v]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                    f"zoompan=z='{zoom_dir}':d={frames}:x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':s=1080x1920:fps={FPS},vignette=PI/4[base]"
                )

            current_v = "[base]"
            input_idx = 1

            # Floating particles
            overlay_path = None
            if OVERLAYS_DIR.exists():
                embers = OVERLAYS_DIR / "embers.mp4"
                dust = OVERLAYS_DIR / "dust.mp4"
                overlay_path = embers if i % 2 == 1 and embers.exists() else dust

            if overlay_path and overlay_path.exists():
                inputs.extend(["-stream_loop", "-1", "-i", str(overlay_path)])
                filter_parts.append(f"{current_v}format=gbrp[base_rgb]")
                filter_parts.append(f"[{input_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=gbrp[ov_rgb]")
                filter_parts.append(f"[base_rgb][ov_rgb]blend=all_mode='screen':all_opacity=0.35,format=yuv420p[v_part]")
                current_v = "[v_part]"
                input_idx += 1

            # Caption overlay
            inputs.extend(["-i", str(cap_badge)])
            filter_parts.append(f"{current_v}[{input_idx}:v]overlay=0:0:enable='between(t,0.2,{length-0.1:.2f})',format=yuv420p[v_cap]")
            current_v = "[v_cap]"
            input_idx += 1

            # CTA Card on last scene
            if is_last and cta_badge.exists():
                inputs.extend(["-i", str(cta_badge)])
                filter_parts.append(f"{current_v}[{input_idx}:v]overlay=0:0:enable='gte(t,{max(0.0, length-4.5):.2f})',format=yuv420p[v_cta]")
                current_v = "[v_cta]"
                input_idx += 1

            # Audio
            inputs.extend(["-i", str(audio)])
            filter_parts.append(f"[{input_idx}:a]apad[a]")

            _run([
                "ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(filter_parts),
                "-map", current_v, "-map", "[a]",
                "-t", f"{length:.2f}", "-r", str(FPS),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                str(out_vscene),
            ])
            short_scenes.append(out_vscene)
            cap_badge.unlink(missing_ok=True)
    finally:
        cta_badge.unlink(missing_ok=True)

    if not short_scenes:
        return None

    # Concat vertical scenes
    raw_short = work_dir / "short_raw.mp4"
    concat(short_scenes, raw_short)

    # Mix background music
    final_short = add_music(raw_short, out_path)
    return final_short
