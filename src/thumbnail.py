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


def create_thumbnail(media_path: Path, badge_text: str, hook_text: str, out_path: Path, subject_name: str = "", subhook_text: str = ""):
    """Generate an authoritative, ultra-high-CTR 1920x1080 historical thumbnail with specific figures and hooks."""
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

        w, h = src_img.size
        target_ratio = W / H
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Wider than 16:9 -> crop sides
            nw = int(h * target_ratio)
            left = (w - nw) // 2
            src_img = src_img.crop((left, 0, left + nw, h))
        else:
            # Taller than 16:9 (vertical portrait painting) -> focus on figures (upper-middle 35-45% height)
            nh = int(w / target_ratio)
            top = max(0, min(int((h - nh) * 0.42), h - nh))
            src_img = src_img.crop((0, top, w, top + nh))

        base = src_img.resize((W, H), Image.LANCZOS)

        # Boost saturation, contrast & sharpness for dramatic, punchy look
        base = ImageEnhance.Color(base).enhance(1.28)
        base = ImageEnhance.Contrast(base).enhance(1.32)
        base = ImageEnhance.Sharpness(base).enhance(1.35)

        # Gradient overlay: dark vignette + heavy left shadow for text readability
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        for x in range(1250):
            alpha = int(220 * (1 - (x / 1250) ** 1.3))
            odraw.line([(x, 0), (x, H)], fill=(6, 6, 10, alpha))

        # Top and bottom subtle vignettes
        for y in range(200):
            alpha = int(140 * (1 - y / 200))
            odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
        for y in range(900, H):
            alpha = int(170 * ((y - 900) / (H - 900)))
            odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

        comp = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(comp)

        # 1. Outer Cinema Accent Border (8px red border)
        draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(229, 9, 20), width=8)

        # 2. Red Alert Badge
        badge_font = _font(38)
        badge = (badge_text or "🔴 HISTORICAL ARCHIVE // UNSEALED").strip().upper()
        bw = draw.textlength(badge, font=badge_font)
        bx, by = 80, 95
        draw.rounded_rectangle([bx - 20, by - 10, bx + bw + 20, by + 50], radius=14, fill=(229, 9, 20))
        draw.text((bx, by), badge, font=badge_font, fill="white")

        # 3. Specific Historical Subject Name (e.g. POPE FORMOSUS) in Giant White
        ty = 185
        if subject_name:
            name_font = _font(118)
            s_name = subject_name.strip().upper()
            # 3D shadow
            for off in range(1, 14):
                draw.text((80 + off, ty + off), s_name, font=name_font, fill=(0, 0, 0, 255))
            draw.text((80, ty), s_name, font=name_font, fill="#FFFFFF", stroke_width=18, stroke_fill="black")
            ty += 145

        # 4. Explosive Hook Title in Electric Gold (e.g. TRIED AFTER DEATH)
        hook_font = _font(128 if subject_name else 138)
        hook = (hook_text or "THE FORBIDDEN TRUTH").strip().upper()
        lines = _wrap(draw, hook, hook_font, 1200)

        colors = ["#FFD700", "#FF3B30", "#FFFFFF"]
        for idx, line in enumerate(lines[:2]):
            col = colors[idx % len(colors)]
            for off in range(1, 14):
                draw.text((80 + off, ty + off), line, font=hook_font, fill=(0, 0, 0, 255))
            draw.text((80, ty), line, font=hook_font, fill=col, stroke_width=20, stroke_fill="black")
            ty += 148

        # 5. Curiosity Subhook Pill
        sub_text = (subhook_text or "WHY DID ROME PUT A CORPSE ON TRIAL?").strip().upper()
        if sub_text:
            sub_font = _font(44)
            sw = draw.textlength(sub_text, font=sub_font)
            sy = min(ty + 15, 820)
            draw.rounded_rectangle([80 - 15, sy - 8, 80 + sw + 15, sy + 58], radius=12, fill=(16, 16, 24, 230))
            draw.rounded_rectangle([80 - 15, sy - 8, 80 + sw + 15, sy + 58], radius=12, outline=(229, 9, 20), width=3)
            draw.text((80, sy), sub_text, font=sub_font, fill="#FFFFFF")

        comp.save(out_path, "JPEG", quality=95)
    finally:
        if frame_tmp.exists():
            frame_tmp.unlink(missing_ok=True)
