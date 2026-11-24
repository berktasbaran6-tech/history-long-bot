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
4. Authentic Museum Visuals: Specify authentic, museum-documented paintings, archival engravings, medieval manuscripts, ancient coin portraits, or archaeological maps (e.g. 'Jean Paul Laurens Cadaver Synod painting', 'Vatican archive manuscript 9th century illumination', 'Lateran basilica ancient Rome reconstruction painting', 'Tiber river Rome 16th century engraving').
5. Verifiable Historical Sources: Always cite 3-5 authentic primary historical chronicles, archival manuscripts, or academic sources (e.g. chronicler names, original historical texts, museum references) that verify the event."""


class Scene(BaseModel):
    chapter_name: str = Field(description="Name of the chapter this scene belongs to")
    narration: str = Field(description="Spoken text for this scene (50-65 words with dramatic pauses like em-dashes and ellipses)")
    wikimedia_query: str = Field(description="Exact search term for public domain historical painting, engraving, or archive photo")
    pexels_query: str = Field(description="Atmospheric B-roll fallback query (e.g. 'cathedral dark candles', 'torches castle fire', 'storm night')")


class HistoryScript(BaseModel):
    title: str = Field(description="Catchy, high-CTR YouTube documentary title, 45-65 chars, no hashtags")
    subject_name: str = Field(default="POPE FORMOSUS", description="The primary historical figure or empire in 2-3 all-caps words (e.g. 'POPE FORMOSUS', 'EMPEROR CALIGULA')")
    thumbnail_hook: str = Field(description="2-4 explosive all-caps shock words for the thumbnail, e.g. 'TRIED AFTER DEATH', 'WAR ON THE SEA'")
    thumbnail_subhook: str = Field(default="WHY DID ROME PUT A CORPSE ON TRIAL?", description="An intriguing curiosity question or revelation (e.g. 'WHY DID POPE STEPHEN EXHUME HIS PREDECESSOR?')")
    thumbnail_badge: str = Field(default="🔴 HISTORICAL ARCHIVE // 897 AD", description="Archive tag with year/place (e.g. '🔴 VATICAN ARCHIVES // 897 AD')")
    thumbnail_query: str = Field(description="Search query for the most dramatic historical painting to use as cover")
    description: str = Field(description="Engaging YouTube description explaining the historical context")
    sources: list[str] = Field(default_factory=list, description="3-5 primary historical chronicles or archival academic references validating the events (e.g. 'Liutprand of Cremona - Antapodosis', 'Liber Pontificalis', 'Catholic Encyclopedia')")
    tags: list[str] = Field(description="20-28 high-volume history SEO tags: specific historical names, broad genres ('history documentary', 'ancient history', 'medieval history', 'dark ages', 'bizarre history', 'untold history', 'world history'), search queries, and audience-match tags ('armchair historian', 'history dose', 'kings and generals', 'weird history', 'biographics')")
    scenes: list[Scene] = Field(description="Exactly 44 to 48 sequential scenes building a guaranteed 12-14 minute deep documentary")


_client = None
FALLBACK_MODELS = [
    config.GEMINI_MODEL,
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
]


def _client_instance():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


TOPIC_SYSTEM = "You are an elite history documentary producer selecting viral, fascinating, lesser-known history topics for YouTube."


def _ask(prompt: str, schema: type[BaseModel], system_instruction: str = SYSTEM, retries: int = 8):
    last = None
    for attempt in range(retries):
        model_name = FALLBACK_MODELS[attempt % len(FALLBACK_MODELS)]
        try:
            response = _client_instance().models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.7,
                ),
            )
            raw = response.text
            return schema.model_validate_json(raw)
        except Exception as exc:
            last = exc
            wait_time = min(60, (attempt + 1) * 15)
            print(f"[script] attempt {attempt+1}/{retries} ({model_name}) error: {exc}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    raise RuntimeError(f"Gemini generation failed: {last}")


class TopicIdea(BaseModel):
    topic: str = Field(description="Specific, intriguing historical event or figure")
    hook: str = Field(description="Explosive first sentence hook")


EMERGENCY_TOPICS = [
    TopicIdea(
        topic="The Dancing Plague of 1518",
        hook="In July 1518, a woman stepped into a narrow street in Strasbourg and began to dance feverishly—and she didn't stop until hundreds joined her in dancing themselves to death."
    ),
    TopicIdea(
        topic="The War of the Bucket: 1325",
        hook="In 1325, two Italian city-states waged a bloody war that killed thousands of soldiers—all over a single stolen wooden oak bucket."
    ),
    TopicIdea(
        topic="The Great Molasses Flood of 1919",
        hook="On an unseasonably warm January afternoon in Boston, a 50-foot steel tank ruptured, unleashing a 35-mile-per-hour tidal wave of boiling black molasses that suffocated the city."
    ),
    TopicIdea(
        topic="The London Monster of 1788",
        hook="For two terrifying years, wealthy women across Georgian London were stalked and slashed by a phantom predator who vanished into the London fog."
    ),
    TopicIdea(
        topic="The Tang Dynasty Poison Emperor: Emperor Wuzong",
        hook="Obsessed with achieving physical immortality, a powerful Chinese emperor consumed toxic elixirs of mercury and sulfur, slowly descending into murderous madness."
    ),
]


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

    try:
        plan = _ask(prompt, TopicPlan, system_instruction=TOPIC_SYSTEM)
        if plan.ideas:
            return plan.ideas[:count]
    except Exception as exc:
        print(f"[warning] plan_topics AI generation failed ({exc}), falling back to emergency verified topic")

    # Fallback to unused emergency topic
    for fallback in EMERGENCY_TOPICS:
        if fallback.topic not in recent:
            return [fallback]
    return [EMERGENCY_TOPICS[0]]


def write_script(idea: TopicIdea) -> HistoryScript:
    """Generate the full documentary script for the chosen topic."""
    prompt = f"""Write an exceptional, deep-dive 12-to-14 minute historical documentary script for:
Topic: {idea.topic}
Hook idea: {idea.hook}

Produce exactly 44 to 48 sequential scenes (each 50-65 words of captivating, emphatic narration, ensuring the total length is at least 12 minutes).
Ensure each scene has an accurate, museum-verified Wikimedia Commons search query for genuine historical art, statues, or archival photos."""

    return _ask(prompt, HistoryScript, system_instruction=SYSTEM)
