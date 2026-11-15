"""Generate 16:9 high-CTR documentary thumbnails for YouTube history videos."""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

import config

W, H = 1920, 1080
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_w):
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
    return lines


def create_thumbnail(media_path: Path, badge_text: str, hook_text: str, out_path: Path):
    """Generate an authoritative, ultra-high-CTR 1920x1080 historical thumbnail."""
    frame_tmp = out_path.with_suffix(".tmp.jpg")
    try:
        if str(media_path).endswith(".mp4"):
            subprocess.run([
                "ffmpeg", "-y", "-ss", "00:00:01", "-i", str(media_path),
                "-vframes", "1", "-q:v", "2", str(frame_tmp)
            ], capture_output=True, timeout=20, check=True)
            src_img = Image.open(frame_tmp).convert("RGB")
        else:
            src_img = Image.open(media_path).convert("RGB")

        # Resize and crop to 16:9 (1920x1080)
        w, h = src_img.size
        scale = max(W / w, H / h)
        nw, nh = int(w * scale), int(h * scale)
        base = src_img.resize((nw, nh), Image.LANCZOS)
        left = (nw - W) // 2
        top = (nh - H) // 2
        base = base.crop((left, top, left + W, top + H))

        # Boost saturation, contrast & sharpness for dramatic, punchy look
        base = ImageEnhance.Color(base).enhance(1.30)
        base = ImageEnhance.Contrast(base).enhance(1.35)
        base = ImageEnhance.Sharpness(base).enhance(1.40)

        # Gradient overlay: dark vignette + heavy left shadow for text readability
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        for x in range(1300):
            alpha = int(225 * (1 - (x / 1300) ** 1.2))
            odraw.line([(x, 0), (x, H)], fill=(5, 5, 8, alpha))

        # Top and bottom subtle vignettes
        for y in range(250):
            alpha = int(140 * (1 - y / 250))
            odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
        for y in range(850, H):
            alpha = int(180 * ((y - 850) / (H - 850)))
            odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

        comp = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(comp)

        # 1. Outer Cinema Accent Border (subtle crimson/red trim)
        draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(229, 9, 20), width=8)

        # 2. Red Alert Badge
        badge_font = _font(42)
        badge = (badge_text or "🔴 FORBIDDEN ARCHIVE").strip().upper()
        bw = draw.textlength(badge, font=badge_font)
        bx, by = 90, 110
        draw.rounded_rectangle([bx - 22, by - 12, bx + bw + 22, by + 56], radius=16, fill=(229, 9, 20))
        draw.text((bx, by), badge, font=badge_font, fill="white")

        # 3. Explosive Two-Tone Hook Title (3D shadow + heavy black stroke)
        title_font = _font(124)
        hook = (hook_text or "THE FORBIDDEN TRUTH").strip().upper()
        lines = _wrap(draw, hook, title_font, 1200)

        ty = 220
        colors = ["#FFFFFF", "#FFD700", "#FF3B30"]  # White, Electric Gold, Crimson

        for idx, line in enumerate(lines[:3]):
            col = colors[idx % len(colors)]
            # Multi-layered 3D drop shadow
            for off in range(1, 12):
                draw.text((90 + off, ty + off), line, font=title_font, fill=(0, 0, 0, 255))
            # Heavy black stroke for mobile thumbnail readability
            draw.text((90, ty), line, font=title_font, fill=col, stroke_width=18, stroke_fill="black")
            ty += 145

        # 4. Curiosity Subtitle Pill
        sub_font = _font(40)
        sub_text = "⚡ THE SECRET THE CHURCH TRIED TO BURY"
        sw = draw.textlength(sub_text, font=sub_font)
        draw.rounded_rectangle([90 - 15, ty + 15 - 8, 90 + sw + 15, ty + 15 + 50], radius=12, fill=(15, 15, 20))
        draw.rounded_rectangle([90 - 15, ty + 15 - 8, 90 + sw + 15, ty + 15 + 50], radius=12, outline=(255, 215, 0), width=3)
        draw.text((90, ty + 15), sub_text, font=sub_font, fill="#FFFFFF")

        comp.save(out_path, "JPEG", quality=95)
    finally:
        if frame_tmp.exists():
            frame_tmp.unlink(missing_ok=True)
