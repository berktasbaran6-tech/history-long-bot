"""Generate high-retention documentary scripts for YouTube long-form history videos."""
import json
import time

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import config

SYSTEM = """You are an elite historical documentary writer behind top YouTube channels like 'The Armchair Historian', 'History Dose', and 'MagnatesMedia'.
Your goal is to produce deeply immersive, richly detailed, 12-to-14 minute YouTube history documentaries (approx 1,800 to 2,200 words total).

CRITICAL IMMERSION RULE (STRICT):
ABSOLUTELY ZERO MODERN FOOTAGE. No cars, no modern tourists, no modern clothing, no modern asphalt cities.
Every visual MUST be an authentic historical museum oil painting, medieval manuscript illumination, classical woodcut/engraving, antique marble sculpture, or timeless elemental nature (candle flame, torch fire, dark storm).

Narrative & Emphatic Vocal Rules:
1. High-Impact Vocal Delivery: Write narration specifically optimized for dynamic speech. Use dramatic pauses with em-dashes (—) and ellipses (...), sharp contrasts, punchy revelations, and rhetorical questions. Never write flat, monotone textbook text; make the spoken words grip the listener with suspense, horror, and curiosity.
2. Structure (6 In-Depth Chapters across 44 to 48 Scenes):
   - Chapter 1: The Gathering Darkness / The Opening Horror (Shocking hook setting the stakes)
   - Chapter 2: The Political Shadows & Ancient Feuds (Deep historical intrigue and rivalries)
   - Chapter 3: The Unhinged Decree (The obsession and fatal decision)
   - Chapter 4: The Corpse on Trial / The Unbelievable Spectacle (The courtroom trial in vivid detail)
   - Chapter 5: The Brutal Sentence & The River Tiber (The desecration and violent punishment)
   - Chapter 6: The Fall & The Historical Reckoning (The furious rebellion and the killer's fate)
3. Scene Pacing: Produce exactly 44 to 48 scenes. Each scene contains 50-65 words of intense, evocative narration (~17-21 seconds per cut, ensuring total video length is comfortably between 12 and 14 minutes).
4. Authentic Museum Visuals: Specify authentic, museum-documented paintings, archival engravings, medieval manuscripts, ancient coin portraits, or archaeological maps (e.g. 'Jean Paul Laurens Cadaver Synod painting', 'Vatican archive manuscript 9th century illumination', 'Lateran basilica ancient Rome reconstruction painting', 'Tiber river Rome 16th century engraving')."""


class Scene(BaseModel):
    chapter_name: str = Field(description="Name of the chapter this scene belongs to")
    narration: str = Field(description="Spoken text for this scene (50-65 words with dramatic pauses like em-dashes and ellipses)")
    wikimedia_query: str = Field(description="Exact search term for public domain historical painting, engraving, or archive photo")
    pexels_query: str = Field(description="Atmospheric B-roll fallback query (e.g. 'cathedral dark candles', 'torches castle fire', 'storm night')")


class HistoryScript(BaseModel):
    title: str = Field(description="Catchy, high-CTR YouTube documentary title, 45-65 chars, no hashtags")
    thumbnail_hook: str = Field(description="2-4 explosive all-caps words for the thumbnail, e.g. 'THE MAD EMPEROR', 'WAR ON THE SEA'")
    thumbnail_query: str = Field(description="Search query for the most dramatic historical painting to use as cover")
    description: str = Field(description="Engaging YouTube description explaining the historical context")
    tags: list[str] = Field(description="12-16 high-volume history SEO tags")
    scenes: list[Scene] = Field(description="Exactly 44 to 48 sequential scenes building a guaranteed 12-14 minute deep documentary")


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
    prompt = f"""Write an exceptional, deep-dive 12-to-14 minute historical documentary script for:
Topic: {idea.topic}
Hook idea: {idea.hook}

Produce exactly 44 to 48 sequential scenes (each 50-65 words of captivating, emphatic narration, ensuring the total length is at least 12 minutes).
Ensure each scene has an accurate, museum-verified Wikimedia Commons search query for genuine historical art, statues, or archival photos."""

    return _ask(prompt, HistoryScript)
