"""Daily long-form documentary pipeline: trends -> script -> narration -> historical art -> video -> upload."""
import json
import os
import socket
import sys
import traceback
from datetime import date
from pathlib import Path

# Set global 60s socket timeout
socket.setdefaulttimeout(60)

import config
from src import compose, script_gen, thumbnail, trends, tts, visuals


def load_history() -> list[dict]:
    if config.HISTORY_FILE.exists():
        return json.loads(config.HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def save_history(history: list[dict]):
    config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.HISTORY_FILE.write_text(json.dumps(history[-500:], indent=2, ensure_ascii=False), encoding="utf-8")


def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def build_documentary(script: script_gen.HistoryScript, work_dir: Path):
    scene_files = []
    chapters = []
    current_time = 0.0
    last_chapter = ""
    primary_art = None

    print(f"   Building {len(script.scenes)} historical scenes...")
    for i, scene in enumerate(script.scenes):
        print(f"   - Scene {i+1}/{len(script.scenes)}: {scene.chapter_name}")
        audio = work_dir / f"voice_{i:02d}.mp3"
        dur = tts.synthesize(scene.narration, audio)

        media, kind = visuals.fetch_media(scene.wikimedia_query, scene.pexels_query, work_dir, i)
        if primary_art is None and kind == "image":
            primary_art = media

        is_new_chapter = (i == 0) or (bool(scene.chapter_name) and scene.chapter_name != last_chapter)
        out_scene = work_dir / f"scene_{i:02d}.mp4"
        compose.render_scene(media, kind, audio, out_scene, dur, i, scene.chapter_name, show_badge=is_new_chapter)
        scene_files.append(out_scene)

        # Record chapters
        if is_new_chapter and scene.chapter_name:
            chapters.append((current_time, scene.chapter_name))
            last_chapter = scene.chapter_name

        current_time += dur + 0.2

    # Render Outro Scene (12 seconds of silence + ambient music reflection & fade to black)
    outro_media = primary_art
    if not outro_media or not Path(outro_media).exists():
        jpgs = sorted(work_dir.glob("media_*.jpg"))
        outro_media = jpgs[-1] if jpgs else (jpgs[0] if jpgs else None)

    if outro_media and Path(outro_media).exists():
        print("   - Outro Scene: Historical Reflection & Archive Complete (12s ambient silence)")
        outro_scene = work_dir / "scene_outro.mp4"
        try:
            compose.render_outro(Path(outro_media), outro_scene, duration=12.0)
            scene_files.append(outro_scene)
            chapters.append((current_time, "Historical Reflection & Outro"))
            current_time += 12.0
        except Exception as exc:
            print(f"   [outro] error creating outro scene: {exc}")

    # If first chapter isn't at 00:00, ensure 00:00 exists for YouTube
    if not chapters or chapters[0][0] > 0.5:
        chapters.insert(0, (0.0, "Introduction"))

    # Concat scenes
    raw = work_dir / "raw.mp4"
    compose.concat(scene_files, raw)
    final_video = compose.add_music(raw, work_dir / "final.mp4")

    # Generate 16:9 High-Impact Thumbnail with Subject Name & Curiosity Subhook
    thumb_path = work_dir / "thumbnail.jpg"
    thumb_media = primary_art or scene_files[0]
    try:
        badge = getattr(script, "thumbnail_badge", "🔴 HISTORICAL ARCHIVE // UNSEALED")
        subject = getattr(script, "subject_name", "")
        subhook = getattr(script, "thumbnail_subhook", "")
        thumbnail.create_thumbnail(
            thumb_media, badge, script.thumbnail_hook, thumb_path,
            subject_name=subject, subhook_text=subhook
        )
        print(f"   created 16:9 thumbnail {thumb_path.name}")
    except Exception as exc:
        print(f"   [thumbnail] error: {exc}")

    return final_video, thumb_path, chapters, current_time


def main():
    today = date.today().isoformat()
    history = load_history()
    youtube = None
    if not config.DRY_RUN:
        from src import uploader
        youtube = uploader.build_youtube()

    print("== 1. Analyzing History Trends")
    trending = trends.fetch_trending(youtube, config.TREND_QUERIES)
    print(f"   {len(trending)} trending history topics")

    print("== 2. Planning Next Documentary")
    publish_now = "--now" in sys.argv or "--publish-now" in sys.argv or os.getenv("PUBLISH_NOW", "0") == "1"
    count = 1 if publish_now else config.VIDEOS_PER_DAY
    if "--count" in sys.argv:
        try:
            count = int(sys.argv[sys.argv.index("--count") + 1])
        except Exception:
            pass

    recent = [h["title"] for h in history[-80:]]
    ideas = script_gen.plan_topics(trending, recent, count)
    if publish_now:
        slots = [None] * len(ideas)
        print("   [mode] Publishing IMMEDIATELY as PUBLIC")
    else:
        slots = uploader.publish_slots(len(ideas)) if youtube else [None] * len(ideas)

    ok = 0
    for idx, (idea, slot) in enumerate(zip(ideas, slots), 1):
        print(f"\n== Documentary {idx}: {idea.topic}")
        work_dir = config.OUTPUT_DIR / today / f"{idx:02d}"
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            script = script_gen.write_script(idea)
            (work_dir / "script.json").write_text(script.model_dump_json(indent=2), encoding="utf-8")
            print(f"   Script ready: '{script.title}'")

            video, thumb, chapters, seconds = build_documentary(script, work_dir)
            mins = seconds / 60
            print(f"   Completed documentary: {video.name} ({mins:.1f} minutes)")

            # Format YouTube chapters in description
            chapter_lines = ["\nTIMESTAMPS:"]
            for sec, ch_name in chapters:
                chapter_lines.append(f"{format_timestamp(sec)} - {ch_name}")
            timestamps_text = "\n".join(chapter_lines)

            # Format primary sources & archival citations
            sources_lines = []
            if getattr(script, "sources", None):
                sources_lines = ["\n📚 HISTORICAL SOURCES & ARCHIVAL REFERENCES:"]
                for src_item in script.sources:
                    sources_lines.append(f"• {src_item}")
            sources_text = "\n".join(sources_lines) if sources_lines else ""

            # High-CTR SEO Description with timestamps, sources, CTA, and engagement prompt
            description = (
                f"{script.description}\n\n"
                f"{timestamps_text}\n"
                f"{sources_text}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏛️ Welcome to UNTOLD HISTORIES — uncovering the dark secrets, lost civilizations, bizarre trials, "
                f"and forgotten truths of world history through in-depth documentary storytelling.\n\n"
                f"🔔 Subscribe for daily historical investigations and documentary deep dives.\n"
                f"💬 What part of this story surprised you the most? Share your thoughts in the comments below!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"#history #documentary #ancienthistory #untoldhistory #medievalhistory #worldhistory #darkhistory"
            )

            video_id = None
            if youtube:
                video_id = uploader.upload(youtube, video, script.title, description, script.tags, slot)
                pub_msg = slot.isoformat() if slot else "NOW (public)"
                print(f"   uploaded https://youtube.com/watch?v={video_id} -> publishes {pub_msg}")
                if thumb.exists():
                    uploader.set_thumbnail(youtube, video_id, thumb)

            # Build and upload vertical teaser Short pointing to the full documentary
            short_id = None
            try:
                print("   Building vertical teaser Short...")
                short_out = work_dir / "short_final.mp4"
                short_video = compose.render_teaser_short(script, work_dir, short_out)
                if youtube and short_video and short_video.exists():
                    full_link = f"https://youtube.com/watch?v={video_id}" if video_id else ""
                    short_title = f"{script.thumbnail_hook}: {script.subject_name} #shorts"[:95]
                    short_desc = (
                        f"{script.description[:250]}...\n\n"
                        f"👉 WATCH THE FULL 14-MINUTE INVESTIGATION ON OUR CHANNEL:\n"
                        f"{full_link}\n\n"
                        f"#shorts #history #documentary #untoldhistory #ancienthistory"
                    )
                    short_tags = ["shorts", "history shorts", "untold history", script.subject_name.lower(), "documentary"]
                    short_id = uploader.upload(youtube, short_video, short_title, short_desc, short_tags, slot)
                    print(f"   uploaded teaser short https://youtube.com/watch?v={short_id}")
            except Exception as exc:
                print(f"   [teaser short] error: {exc}")
            else:
                if not youtube:
                    print("   DRY_RUN: video built, not uploaded")

            history.append({
                "date": today,
                "topic": idea.topic,
                "title": script.title,
                "video_id": video_id,
                "short_id": short_id,
                "duration_seconds": round(seconds, 1),
                "publish_at": slot.isoformat() if slot else None,
            })
            save_history(history)
            ok += 1
        except Exception:
            traceback.print_exc()
            print(f"   !! documentary {idx} failed")

    print(f"\nDone: {ok}/{len(ideas)} documentaries created")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
