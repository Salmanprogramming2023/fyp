import html
import json
import os
import re
import sys
import time

import requests


# ============================================================
# MODULE 3
# ENGLISH -> URDU (gender-aware)
#
# Module 3 does NOT analyze audio and does NOT detect gender.
# It reads the gender that Module 2 stored in:
#
#     speech_segments.json
#
# and uses it to fix Urdu grammar: verbs and adjectives change
# with the speaker's gender ("I am going" is  میں جا رہا ہوں  for
# a man and  میں جا رہی ہوں  for a woman). MyMemory does not know
# who is speaking, so the gender rules below correct its output.
#
# OUTPUT:
#     urdu_transcript.txt
#     urdu_segments.json
#     translation_cache.json   (saves your daily MyMemory quota)
#
# Install:  python -m pip install requests
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

INPUT_FILE = os.path.join(BASE_DIR, "speech_segments.json")
URDU_TEXT_FILE = os.path.join(BASE_DIR, "urdu_transcript.txt")
URDU_SEGMENTS_FILE = os.path.join(BASE_DIR, "urdu_segments.json")
CACHE_FILE = os.path.join(BASE_DIR, "translation_cache.json")


# ============================================================
# SETTINGS
# ============================================================

MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# Optional: put a real e-mail address here. MyMemory then allows about
# 50,000 characters per day instead of about 5,000 for anonymous use.
MYMEMORY_EMAIL = ""

RETRY_COUNT = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 0.3

# MyMemory rejects a query longer than 500 characters.
MAX_CHARS = 450


# ============================================================
# GENDER RULES
# ============================================================
# Anchored on the first-person word "ہوں" / "ں گا", so they only touch
# verbs that belong to the speaker ("I ..."), never "he/she ...".
# They are heuristics: they cover the common patterns, not all Urdu grammar.

FEMALE_RULES = [
    (r"تا(?=\s+ہوں)", "تی"),      # کرتا ہوں   -> کرتی ہوں
    (r"رہا(?=\s+ہوں)", "رہی"),    # جا رہا ہوں -> جا رہی ہوں
    (r"چکا(?=\s+ہوں)", "چکی"),    # کر چکا ہوں -> کر چکی ہوں
    (r"گیا(?=\s+ہوں)", "گئی"),    # گیا ہوں    -> گئی ہوں
    (r"(?<!ی)ں\s+گا\b", "ں گی"),  # کروں گا    -> کروں گی
]

MALE_RULES = [
    (r"تی(?=\s+ہوں)", "تا"),
    (r"رہی(?=\s+ہوں)", "رہا"),
    (r"چکی(?=\s+ہوں)", "چکا"),
    (r"گئی(?=\s+ہوں)", "گیا"),
    (r"(?<!ی)ں\s+گی\b", "ں گا"),  # (?<!ی) keeps plural "جائیں گی" untouched
]


def apply_gender_rules(text, gender):

    if gender == "female":
        rules = FEMALE_RULES
    elif gender == "male":
        rules = MALE_RULES
    else:
        return text

    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text)

    return text


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    return re.sub(r"\s+", " ", str(text)).strip()


def looks_like_urdu(text):
    """True if the text is mostly Arabic-script (Urdu) letters."""

    urdu_letters = len(re.findall(r"[\u0600-\u06FF]", text))
    latin_letters = len(re.findall(r"[A-Za-z]", text))

    return urdu_letters > 0 and urdu_letters >= latin_letters


def strip_english_echo(urdu, english):
    """MyMemory sometimes appends a broken copy of the English sentence to the
    Urdu ("... مار رہے ہیں! You 're hit me in the face!"). A run of two or more
    Latin words that mostly repeats the English source is removed. A single
    Latin word (a name or brand) is kept."""

    source = set(re.findall(r"[a-z]+", english.lower()))

    def drop_echo(match):

        run = match.group(0)
        words = re.findall(r"[A-Za-z]+", run)

        long_enough = len(words) >= 3 or (len(words) == 2 and any(w[0].islower() for w in words))

        if long_enough and sum(w.lower() in source for w in words) / len(words) >= 0.6:
            return " "

        return run

    return clean_text(re.sub(r"[A-Za-z'][A-Za-z0-9'\s.,!?;:\-]*", drop_echo, urdu))


def split_text(text, limit=MAX_CHARS):
    """Split long text into pieces below MyMemory's length limit."""

    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""

    for sentence in re.split(r"(?<=[.!?])\s+", text):

        # A single very long sentence: cut it on a space.
        while len(sentence) > limit:

            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit

            if current:
                chunks.append(current)
                current = ""

            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()

        if not sentence:
            continue

        if current and len(current) + 1 + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks


# ============================================================
# CACHE
# ============================================================

def load_cache():

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(cache):

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as file:
            json.dump(cache, file, ensure_ascii=False, indent=2)
    except Exception as error:
        print("WARNING: could not save translation cache:", error)


# ============================================================
# MYMEMORY
# ============================================================

class QuotaExhausted(Exception):
    pass


def translate_chunk(text):
    """Translate one chunk (<= 500 chars). Returns Urdu text or None."""

    params = {
        "q": text,
        "langpair": "en|ur"
    }

    if MYMEMORY_EMAIL:
        params["de"] = MYMEMORY_EMAIL

    for attempt in range(1, RETRY_COUNT + 1):

        problem = ""

        try:

            response = requests.get(
                MYMEMORY_URL,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 429:
                raise QuotaExhausted()

            if response.status_code != 200:

                problem = f"HTTP error {response.status_code}"

            else:

                data = response.json()

                translated = clean_text(
                    html.unescape(
                        str(
                            (data.get("responseData") or {}).get(
                                "translatedText",
                                ""
                            )
                        )
                    )
                )

                status = str(data.get("responseStatus", 200))

                # MyMemory reports a used-up daily limit INSIDE the
                # translated text, so it must be checked explicitly.
                if (
                    status == "429"
                    or
                    "MYMEMORY WARNING" in translated.upper()
                ):
                    raise QuotaExhausted()

                if status != "200":

                    problem = f"service status {status}: {translated[:80]}"

                elif not looks_like_urdu(strip_english_echo(translated, text)):

                    problem = "result is not Urdu text"

                else:

                    return strip_english_echo(translated, text)

        except QuotaExhausted:

            raise

        except Exception as error:

            problem = str(error)

        print(f"    attempt {attempt}/{RETRY_COUNT} failed: {problem}")

        if attempt < RETRY_COUNT:
            time.sleep(RETRY_DELAY)

    return None


def translate_text(text, cache):
    """Returns (urdu_or_None, used_network)."""

    if text in cache:
        return strip_english_echo(cache[text], text), False

    pieces = []

    for chunk in split_text(text):

        urdu = translate_chunk(chunk)

        if not urdu:
            return None, True

        pieces.append(urdu)

    result = " ".join(pieces)

    cache[text] = result
    save_cache(cache)

    return result, True


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       MODULE 3 - ENGLISH -> URDU (gender-aware)")
    print("=" * 70)

    print()
    print("Input file:")
    print(INPUT_FILE)

    print()
    print("Output Urdu text:")
    print(URDU_TEXT_FILE)

    print()
    print("Output Urdu segments:")
    print(URDU_SEGMENTS_FILE)

    print()
    print("Translation service: MyMemory API")


    # --------------------------------------------------------
    # Load Module 2 output
    # --------------------------------------------------------

    if not os.path.exists(INPUT_FILE):

        print()
        print("ERROR: speech_segments.json was not found.")
        print(INPUT_FILE)

        return 1

    try:

        with open(INPUT_FILE, "r", encoding="utf-8") as file:
            module2_data = json.load(file)

    except Exception as error:

        print()
        print("ERROR loading speech_segments.json:")
        print(error)

        return 1

    if not isinstance(module2_data, dict):

        print()
        print("ERROR: Module 2 JSON must be an object containing 'segments'.")

        return 1

    segments = module2_data.get("segments")

    if not isinstance(segments, list) or not segments:

        print()
        print("ERROR: 'segments' is missing, not a list, or empty.")

        return 1

    print()
    print("Total segments received from Module 2:", len(segments))


    # --------------------------------------------------------
    # Translate
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TRANSLATING SEGMENTS")
    print("=" * 70)

    cache = load_cache()

    urdu_segments = []
    urdu_text_parts = []
    failed_ids = []
    adjusted_count = 0
    quota_exhausted = False

    for index, source in enumerate(segments, start=1):

        english = clean_text(
            source.get("text_en") or source.get("text") or ""
        )

        if not english:

            print(f"Skipping empty segment {index}.")

            continue

        try:
            start = float(source.get("start", 0.0))
        except Exception:
            start = 0.0

        try:
            end = float(source.get("end", start))
        except Exception:
            end = start

        gender = str(
            source.get("gender") or "unknown"
        ).strip().lower()

        if gender not in ("male", "female", "unknown"):

            print(f"WARNING: bad gender value '{gender}' in segment {index}.")

            gender = "unknown"

        print()
        print("-" * 70)
        print(f"Segment {index}/{len(segments)}  "
              f"[{start:.3f} -> {end:.3f}]  gender: {gender}")
        print("English:", english)

        # ----------------------------------------------------
        # Translate the text only
        # ----------------------------------------------------

        urdu = None
        used_network = False

        if not quota_exhausted:

            try:

                urdu, used_network = translate_text(english, cache)

            except QuotaExhausted:

                quota_exhausted = True

                print()
                print("MyMemory daily limit reached. Remaining segments will")
                print("not be translated. Already translated text is cached,")
                print("so re-run later, or set MYMEMORY_EMAIL to raise the limit.")

        translation_failed = not urdu

        gender_adjusted = False

        if translation_failed:

            urdu = english

            failed_ids.append(index)

            print("WARNING: translation failed, keeping English text.")

        else:

            adjusted = apply_gender_rules(urdu, gender)

            gender_adjusted = adjusted != urdu

            urdu = adjusted

            if gender_adjusted:
                adjusted_count += 1

        print("Urdu:   ", urdu, "(gender-adjusted)" if gender_adjusted else "")

        # ----------------------------------------------------
        # Build output segment
        # ----------------------------------------------------

        urdu_segment = {
            "id": len(urdu_segments) + 1,
            "source_id": source.get("id", index),
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(max(0.0, end - start), 3),
            "english": english,
            "urdu": urdu,
            "gender": gender,
            "gender_adjusted": gender_adjusted,
            "translation_failed": translation_failed
        }

        for field_name in (
            "gender_uncertain",
            "speaker",
            "speaker_index",
            "pitch",
            "mean_pitch",
            "voiced_ratio",
            "confidence",
            "raw_gender",
            "raw_confidence"
        ):

            if field_name in source:
                urdu_segment[field_name] = source[field_name]

        urdu_segments.append(urdu_segment)
        urdu_text_parts.append(urdu)

        if used_network:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    if not urdu_segments:

        print()
        print("ERROR: No Urdu segments were created.")

        return 1


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:

        with open(URDU_TEXT_FILE, "w", encoding="utf-8") as file:
            file.write("\n".join(urdu_text_parts))

        output = {
            "language": "ur",
            "source_language": "en",
            "translation_service": "MyMemory",
            "gender_source": "Copied directly from Module 2 speech_segments.json",
            "audio_analysis_in_module3": False,
            "segment_count": len(urdu_segments),
            "gender_adjusted_segments": adjusted_count,
            "failed_segments": len(failed_ids),
            "segments": urdu_segments
        }

        with open(URDU_SEGMENTS_FILE, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=4)

    except Exception as error:

        print()
        print("ERROR saving output files:")
        print(error)

        return 1


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    def count(gender_name):
        return sum(1 for s in urdu_segments if s["gender"] == gender_name)

    print()
    print("=" * 70)
    print("MODULE 3 COMPLETE")
    print("=" * 70)

    print()
    print("Total segments:", len(urdu_segments))
    print("Male segments:", count("male"))
    print("Female segments:", count("female"))
    print("Unknown segments:", count("unknown"))
    print("Gender-adjusted translations:", adjusted_count)

    print()
    print("Urdu transcript:", os.path.abspath(URDU_TEXT_FILE))
    print("Urdu segments:  ", os.path.abspath(URDU_SEGMENTS_FILE))

    if failed_ids:

        print()
        print("=" * 70)
        print(f"WARNING: {len(failed_ids)} segment(s) were NOT translated:")
        print(failed_ids)
        print("They still contain English text. Re-run Module 3 to retry them")
        print("(finished translations are cached) before running Module 4.")
        print("=" * 70)

        return 1

    print()
    print("=" * 70)
    print("READY FOR MODULE 4")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())