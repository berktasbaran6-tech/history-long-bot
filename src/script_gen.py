"""Generate high-retention documentary scripts for YouTube long-form history videos."""
import json
import time

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import config

SYSTEM = """You are an elite historical documentary writer behind top YouTube channels like 'The Armchair Historian', 'History Dose', and 'Weird History'.
Your goal is to produce deeply engaging, suspenseful, and historically authentic documentary scripts.

Narrative Rules:
1. The Opening Hook (Scene 1-2): Immediately shock the audience with an unbelievable historical mystery, bizarre decision, or forgotten conflict. Zero generic greetings.
2. Narrative Arc: Structure the story across clear chapters:
   - The Spark / The Madness
   - The Escalation
   - The Climax / The Reality
   - The Haunting Aftermath
3. Spoken Tone: Sophisticated, cinematic, dramatic, and respectful of real historical gravity.
4. Scene Length: Each scene contains 30-45 spoken words (approx 12-16 seconds per scene).
5. Visual Queries: Specify exact historical figures, battles, or events for museum paintings/statues (e.g., 'Julius Caesar crossing Rubicon painting', 'Roman senate ancient painting', 'Emperor Caligula marble sculpture')."""


class Scene(BaseModel):
    chapter_name: str = Field(description="Name of the chapter this scene belongs to")
    narration: str = Field(description="Spoken text for this scene (30-45 words)")
    wikimedia_query: str = Field(description="Exact search term for public domain historical painting or archive photo")
    pexels_query: str = Field(description="Atmospheric B-roll fallback query (e.g. 'ocean waves storm dark', 'torches castle fire')")


class HistoryScript(BaseModel):
    title: str = Field(description="Catchy, high-CTR YouTube documentary title, 45-65 chars, no hashtags")
    thumbnail_hook: str = Field(description="2-4 explosive all-caps words for the thumbnail, e.g. 'THE MAD EMPEROR', 'WAR ON THE SEA'")
    thumbnail_query: str = Field(description="Search query for the most dramatic historical painting to use as cover")
    description: str = Field(description="Engaging YouTube description explaining the historical context")
    tags: list[str] = Field(description="12-16 high-volume history SEO tags")
    scenes: list[Scene] = Field(description="12 to 16 sequential scenes building a 4-6 minute compelling documentary")


_client = None
FALLBACK_MODELS = [
    config.GEMINI_MODEL,
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]


def _client_instance():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _ask(prompt: str, schema: type[BaseModel], retries: int = 4):
    last = None
    for attempt in range(retries):
        model_name = FALLBACK_MODELS[min(attempt, len(FALLBACK_MODELS) - 1)]
        try:
            response = _client_instance().models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.7,
                ),
            )
            raw = response.text
            return schema.model_validate_json(raw)
        except Exception as exc:
            last = exc
            print(f"[script] attempt {attempt+1} ({model_name}) error: {exc}")
            time.sleep(2)
    raise RuntimeError(f"Gemini generation failed: {last}")


class TopicIdea(BaseModel):
    topic: str = Field(description="Specific, intriguing historical event or figure")
    hook: str = Field(description="Explosive first sentence hook")


class TopicPlan(BaseModel):
    ideas: list[TopicIdea]


def plan_topics(trending: list[str], recent: list[str], count: int = 1) -> list[TopicIdea]:
    """Select the most viral, unexplored historical topic."""
    prompt = f"""Review these trending history topics and our recent videos:
Trending:
{chr(10).join(f'- {t}' for t in trending[:15])}

Recently covered by us (DO NOT REPEAT):
{chr(10).join(f'- {t}' for t in recent[:40])}

Select {count} wildly captivating, lesser-known, or deeply dramatic historical events or figures from Ancient, Medieval, or Modern history that make viewers say 'Did this really happen?!'.
Focus on bizarre military blunders, secret deceptions, eccentric rulers, or shocking ancient mysteries."""

    plan = _ask(prompt, TopicPlan)
    return plan.ideas[:count]


def write_script(idea: TopicIdea) -> HistoryScript:
    """Generate the full documentary script for the chosen topic."""
    prompt = f"""Write an exceptional historical documentary script for:
Topic: {idea.topic}
Hook idea: {idea.hook}

Produce exactly 12 to 15 scenes (each 30-45 words of captivating narration).
Ensure each scene has an accurate Wikimedia Commons search query for genuine historical art, statues, or archival photos."""

    return _ask(prompt, HistoryScript)
