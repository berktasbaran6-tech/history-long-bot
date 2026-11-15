"""Generate 1 trial documentary video and place final.mp4 and thumbnail.jpg directly on Desktop."""
import os
import shutil
from pathlib import Path

os.environ["DRY_RUN"] = "1"

import config
from src import script_gen, trends
from main import build_documentary, format_timestamp


def run_demo():
    print("=== 1. Selecting Historical Topic ===")
    trending = trends.FALLBACK_TOPICS
    ideas = script_gen.plan_topics(trending, [], count=1)
    idea = ideas[0]
    print(f"Selected: {idea.topic}")

    work_dir = config.OUTPUT_DIR / "demo"
    work_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== 2. Writing Documentary Script ===")
    script = script_gen.write_script(idea)
    (work_dir / "script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")
    print(f"Title: {script.title}")
    print(f"Thumbnail Hook: {script.thumbnail_hook}")
    print(f"Total Scenes: {len(script.scenes)}")

    print("\n=== 3. Building Scenes (Museum Art + Edge-TTS + Ken Burns Motion) ===")
    video, thumb, chapters, seconds = build_documentary(script, work_dir)
    mins = seconds / 60
    print(f"\nDocumentary built: {video.name} ({mins:.1f} minutes / {seconds:.1f}s)")

    # Copy directly to Desktop
    desktop = Path("C:/Users/ACER/OneDrive/Masaüstü")
    dest_video = desktop / "Deneme_Tarih_Videosu.mp4"
    dest_thumb = desktop / "Deneme_Tarih_Kapagi.jpg"

    shutil.copy2(video, dest_video)
    if thumb.exists():
        shutil.copy2(thumb, dest_thumb)

    print("\n=== SUCCESS! ===")
    print(f"Video copied to Desktop: {dest_video}")
    print(f"Thumbnail copied to Desktop: {dest_thumb}")


if __name__ == "__main__":
    run_demo()
