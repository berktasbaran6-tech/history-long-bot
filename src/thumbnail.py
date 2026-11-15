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
    """Generate an authoritative, eye-catching 1920x1080 historical thumbnail."""
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

        # Boost saturation & contrast for dramatic historical look
        base = ImageEnhance.Color(base).enhance(1.25)
        base = ImageEnhance.Contrast(base).enhance(1.20)

        # Gradient overlay on the left/center for text readability
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        for x in range(1200):
            alpha = int(210 * (1 - x / 1200))
            odraw.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))

        # Bottom shadow
        for y in range(800, H):
            alpha = int(180 * ((y - 800) / (H - 800)))
            odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

        comp = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(comp)

        badge_font = _font(42)
        title_font = _font(110)

        # 1. Red Badge Pill
        badge = (badge_text or "⚡ UNTOLD HISTORY").strip().upper()
        bw = draw.textlength(badge, font=badge_font)
        bx = 90
        by = 130
        draw.rounded_rectangle([bx - 20, by - 12, bx + bw + 20, by + 52], radius=18, fill=(229, 9, 20))
        draw.text((bx, by), badge, font=badge_font, fill="white")

        # 2. Explosive Hook Title
        hook = (hook_text or "THE FORBIDDEN TRUTH").strip().upper()
        lines = _wrap(draw, hook, title_font, 1150)
        ty = 230
        for line in lines[:3]:
            draw.text((90, ty), line, font=title_font,
                      fill="#FFE135", stroke_width=14, stroke_fill="black")
            ty += 130

        comp.save(out_path, "JPEG", quality=95)
    finally:
        if frame_tmp.exists():
            frame_tmp.unlink(missing_ok=True)
