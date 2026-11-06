"""
Module 4: Urdu text -> speech (gender-matched voice, NORMALIZED speed)
----------------------------------------------------------------------
Input : urdu_segments.json        (from module 3, next to this file)
Output: output/tts/seg_0001.wav, seg_0002.wav, ...   (one wav per segment)
        output/segments_tts.json  (segments + audio info, consumed by module 5)

Speed normalization
  Every segment is generated at the SAME speaking speed. The old version
  sped up each segment by a different amount to fit its time slot, which
  made the voice change speed from sentence to sentence.
  Now: (1) all segments are generated at natural speed, (2) ONE global speed
  is chosen so that most segments fit their slot, (3) all segments are
  regenerated at that speed. Segments that still do not fit are handled by
  module 5 without slowing anything down.

Added to every segment:
{
  "voice": "ur-PK-UzmaNeural",
  "audio_path": ".../output/tts/seg_0001.wav",
  "tts_duration": 2.85,      # seconds of generated speech
  "slot_duration": 3.10,     # seconds available in the original video
  "tts_rate": "+12%"         # the same value for every segment
}

Voices: Microsoft Edge neural voices via edge-tts (free, needs internet)
  male   -> ur-PK-AsadNeural
  female -> ur-PK-UzmaNeural

Install:  python -m pip install edge-tts pydub numpy   (pydub also needs ffmpeg)
"""
import asyncio
import json
import os

import numpy as np
import edge_tts
from pydub import AudioSegment

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_JSON = os.path.join(BASE_DIR, "urdu_segments.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "output", "segments_tts.json")
TTS_DIR = os.path.join(BASE_DIR, "output", "tts")

VOICES = {
    "male": "ur-PK-AsadNeural",
    "female": "ur-PK-UzmaNeural",
}

# --- speed normalization ---------------------------------------------------
TARGET_PERCENTILE = 75        # this share of segments should fit its slot
MAX_GLOBAL_SPEEDUP_PCT = 30   # never speak faster than +30% (sounds rushed)
MIN_GLOBAL_SPEEDUP_PCT = 3    # below this keep natural speed
RETRIES = 3


async def synthesize(text, voice, mp3_path, rate="+0%"):
    for attempt in range(1, RETRIES + 1):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(mp3_path)
            return
        except Exception as e:   # network hiccup etc.
            if attempt == RETRIES:
                raise
            print(f"    TTS failed ({e}); retry {attempt}/{RETRIES - 1} ...")
            await asyncio.sleep(2 * attempt)


def mp3_to_wav(mp3_path, wav_path):
    audio = AudioSegment.from_file(mp3_path)
    audio.export(wav_path, format="wav")
    return len(audio) / 1000.0   # seconds


def available_slot(segments, idx):
    """Time the dubbed line may use: its own slot, or up to the next line's start."""
    seg = segments[idx]
    own = seg["end"] - seg["start"]
    if idx + 1 < len(segments):
        gap = segments[idx + 1]["start"] - seg["start"] - 0.15   # keep a tiny pause
        return max(own, gap)
    return own


def choose_global_rate(needs):
    """needs = natural_duration / slot for every spoken segment.
    Returns ONE edge-tts rate string used for all segments."""
    if not needs:
        return "+0%"
    factor = float(np.percentile(needs, TARGET_PERCENTILE))
    pct = int(round((factor - 1.0) * 100))
    pct = max(0, min(MAX_GLOBAL_SPEEDUP_PCT, pct))
    return f"+{pct}%" if pct >= MIN_GLOBAL_SPEEDUP_PCT else "+0%"


async def generate(job, rate):
    """(Re)generate one segment's wav at the given speed."""
    mp3_path = job["base"] + ".mp3"
    await synthesize(job["text"], job["voice"], mp3_path, rate)
    job["duration"] = mp3_to_wav(mp3_path, job["wav"])
    os.remove(mp3_path)


async def process(segments):
    os.makedirs(TTS_DIR, exist_ok=True)

    jobs = []
    for idx, seg in enumerate(segments):
        text = (seg.get("urdu") or seg.get("text_ur") or "").strip()
        if seg.get("translation_failed"):
            text = ""   # untranslated English cannot be read by an Urdu voice
        voice = VOICES.get(seg.get("gender", "male"), VOICES["male"])
        base = os.path.join(TTS_DIR, f"seg_{seg['id']:04d}")
        slot = available_slot(segments, idx)

        seg["voice"] = voice
        seg["slot_duration"] = round(slot, 3)
        seg["audio_path"] = base + ".wav"

        if not text:   # nothing to say -> silence keeps the timeline intact
            AudioSegment.silent(duration=int(slot * 1000)).export(base + ".wav", format="wav")
            seg["tts_duration"] = round(slot, 3)
            seg["tts_rate"] = "+0%"
            continue

        jobs.append({"seg": seg, "text": text, "voice": voice,
                     "base": base, "wav": base + ".wav", "slot": slot})

    # Pass 1: natural speed for every segment
    print("[Module 4] Pass 1: natural speed ...")
    for job in jobs:
        await generate(job, "+0%")

    # Choose ONE speed for the whole video
    needs = [j["duration"] / j["slot"] for j in jobs if j["slot"] > 0]
    global_rate = choose_global_rate(needs)
    print(f"[Module 4] Global speaking speed for ALL segments: {global_rate}")

    # Pass 2: regenerate everything at the same speed
    if global_rate != "+0%":
        print("[Module 4] Pass 2: regenerating all segments at the global speed ...")
        for job in jobs:
            await generate(job, global_rate)

    for seg in segments:
        seg["tts_rate"] = global_rate   # same value everywhere (silent segments included)

    for job in jobs:
        seg = job["seg"]
        seg["tts_duration"] = round(job["duration"], 3)
        print(f"  #{seg['id']:03d} {job['voice']:18s} slot={job['slot']:5.2f}s  "
              f"speech={job['duration']:5.2f}s  rate={global_rate}")


def run(input_json=INPUT_JSON, output_json=OUTPUT_JSON):
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"{input_json} not found (run module 3 first)")
    with open(input_json, encoding="utf-8") as f:
        data = json.load(f)
    # module 3 writes {"segments": [...], ...}; a plain list also works
    segments = data["segments"] if isinstance(data, dict) else data

    os.makedirs(os.path.dirname(output_json), exist_ok=True)

    print(f"[Module 4] Generating Urdu speech for {len(segments)} segments ...")
    asyncio.run(process(segments))

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    print(f"[Module 4] Saved -> {output_json}")
    return output_json


if __name__ == "__main__":
    run()