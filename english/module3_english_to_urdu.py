import os
import json
import time
import re
import requests


# ============================================================
# MODULE 3
# ENGLISH → URDU
#
# IMPORTANT:
# Module 3 does NOT analyze audio.
# Module 3 does NOT detect gender.
# Module 3 only reads gender from Module 2:
#
# speech_segments.json
#
# OUTPUT:
#     urdu_transcript.txt
#     urdu_segments.json
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "speech_segments.json"
)

URDU_TEXT_FILE = os.path.join(
    BASE_DIR,
    "urdu_transcript.txt"
)

URDU_SEGMENTS_FILE = os.path.join(
    BASE_DIR,
    "urdu_segments.json"
)


# ============================================================
# SETTINGS
# ============================================================

RETRY_COUNT = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 20


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("       MODULE 3 - ENGLISH → URDU")
print("=" * 70)

print()
print("IMPORTANT:")
print("Module 3 does NOT analyze audio.")
print("Module 3 does NOT detect gender.")
print("Module 3 only copies gender from Module 2.")

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
print("Translation service:")
print("MyMemory API ONLY")


# ============================================================
# CHECK INPUT FILE
# ============================================================

if not os.path.exists(INPUT_FILE):

    print()
    print("ERROR: speech_segments.json was not found.")
    print("Expected path:")
    print(INPUT_FILE)

    raise SystemExit(1)


# ============================================================
# LOAD MODULE 2 JSON
# ============================================================

print()
print("=" * 70)
print("LOADING GENDER INFORMATION FROM MODULE 2")
print("=" * 70)

try:

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        module2_data = json.load(file)

except Exception as error:

    print()
    print("ERROR loading speech_segments.json:")
    print(error)

    raise SystemExit(1)


# ============================================================
# READ SEGMENTS
# ============================================================

if not isinstance(module2_data, dict):

    print()
    print("ERROR:")
    print("Module 2 JSON must be an object containing 'segments'.")

    raise SystemExit(1)


segments = module2_data.get("segments")


if not isinstance(segments, list):

    print()
    print("ERROR:")
    print("The 'segments' field is missing or is not a list.")

    raise SystemExit(1)


if not segments:

    print()
    print("ERROR:")
    print("Module 2 provided zero speech segments.")

    raise SystemExit(1)


print()
print("Total segments received from Module 2:")
print(len(segments))


# ============================================================
# SHOW EXACT GENDER RECEIVED FROM MODULE 2
# ============================================================

print()
print("=" * 70)
print("GENDER RECEIVED FROM MODULE 2")
print("=" * 70)

for index, segment in enumerate(
    segments,
    start=1
):

    received_gender = segment.get(
        "gender",
        "MISSING"
    )

    print(
        f"Segment {index}: {received_gender}"
    )

print("=" * 70)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\n",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# MYMEMORY TRANSLATION
# ============================================================

def translate_mymemory(text):

    text = clean_text(text)

    if not text:
        return ""

    url = (
        "https://api.mymemory.translated.net/get"
    )

    params = {
        "q": text,
        "langpair": "en|ur"
    }

    for attempt in range(
        1,
        RETRY_COUNT + 1
    ):

        try:

            print(
                f"MyMemory attempt "
                f"{attempt}/{RETRY_COUNT}..."
            )

            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code != 200:

                print(
                    "MyMemory HTTP error:",
                    response.status_code
                )

                if attempt < RETRY_COUNT:
                    time.sleep(RETRY_DELAY)

                continue

            result = response.json()

            translated = (
                result
                .get(
                    "responseData",
                    {}
                )
                .get(
                    "translatedText",
                    ""
                )
            )

            translated = clean_text(
                translated
            )

            if not translated:
                continue

            if translated.lower() == text.lower():

                print(
                    "WARNING: MyMemory returned "
                    "the original English text."
                )

                if attempt < RETRY_COUNT:
                    time.sleep(RETRY_DELAY)

                continue

            print(
                "Translation successful."
            )

            return translated

        except Exception as error:

            print(
                "MyMemory translation error:",
                error
            )

            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)

    return None


# ============================================================
# TRANSLATE ONE SENTENCE
# ============================================================

def translate_sentence(text):

    text = clean_text(text)

    if not text:
        return ""

    translated = translate_mymemory(
        text
    )

    if translated:
        return translated

    print()
    print(
        "WARNING: Translation failed."
    )

    print(
        "Keeping original English text."
    )

    return text


# ============================================================
# TRANSLATION PROCESS
# ============================================================

print()
print("=" * 70)
print("TRANSLATING SEGMENTS")
print("=" * 70)

urdu_segments = []
urdu_text_parts = []


for index, source_segment in enumerate(
    segments,
    start=1
):

    # --------------------------------------------------------
    # READ ENGLISH TEXT FROM MODULE 2
    # --------------------------------------------------------

    english = clean_text(
        source_segment.get(
            "text",
            ""
        )
    )

    if not english:
        print(
            f"Skipping empty segment {index}."
        )
        continue

    # --------------------------------------------------------
    # READ TIMING FROM MODULE 2
    # --------------------------------------------------------

    try:

        start = float(
            source_segment.get(
                "start",
                0.0
            )
        )

    except Exception:

        start = 0.0

    try:

        end = float(
            source_segment.get(
                "end",
                start
            )
        )

    except Exception:

        end = start

    duration = max(
        0.0,
        end - start
    )

    # --------------------------------------------------------
    # COPY GENDER FROM MODULE 2
    #
    # NO AUDIO ANALYSIS HERE
    # NO GENDER MODEL HERE
    # --------------------------------------------------------

    original_gender = source_segment.get(
        "gender",
        "unknown"
    )

    if original_gender is None:
        original_gender = "unknown"

    gender = str(
        original_gender
    ).strip().lower()

    # Keep only the values supplied by Module 2.
    # Do not predict or calculate anything here.

    if gender not in (
        "male",
        "female",
        "unknown"
    ):

        print()
        print(
            f"WARNING: Unknown gender value "
            f"'{gender}' in segment {index}."
        )

        gender = "unknown"

    print()
    print("-" * 70)

    print(
        f"Segment {index}/{len(segments)}"
    )

    print(
        f"Time: {start:.3f} -> {end:.3f}"
    )

    print(
        "Gender copied from Module 2:",
        gender
    )

    print(
        "English:",
        english
    )

    # --------------------------------------------------------
    # TRANSLATE ONLY TEXT
    # --------------------------------------------------------

    urdu = translate_sentence(
        english
    )

    if not urdu:
        urdu = english

    print(
        "Urdu:",
        urdu
    )

    # --------------------------------------------------------
    # CREATE OUTPUT SEGMENT
    #
    # The gender is copied, not detected.
    # --------------------------------------------------------

    urdu_segment = {
        "id": len(urdu_segments) + 1,

        "start": round(
            start,
            3
        ),

        "end": round(
            end,
            3
        ),

        "duration": round(
            duration,
            3
        ),

        "english": english,

        "urdu": urdu,

        "gender": gender
    }

    # --------------------------------------------------------
    # COPY OPTIONAL INFORMATION FROM MODULE 2
    # --------------------------------------------------------

    fields_to_copy = [
        "speaker",
        "speaker_index",
        "pitch",
        "mean_pitch",
        "voiced_ratio",
        "confidence",
        "raw_gender",
        "raw_confidence"
    ]

    for field_name in fields_to_copy:

        if field_name in source_segment:

            urdu_segment[field_name] = (
                source_segment[field_name]
            )

    # --------------------------------------------------------
    # SAVE IN MEMORY
    # --------------------------------------------------------

    urdu_segments.append(
        urdu_segment
    )

    urdu_text_parts.append(
        urdu
    )


# ============================================================
# CHECK OUTPUT
# ============================================================

if not urdu_segments:

    print()
    print(
        "ERROR: No Urdu segments were created."
    )

    raise SystemExit(1)


# ============================================================
# CREATE URDU TRANSCRIPT
# ============================================================

urdu_text = "\n".join(
    urdu_text_parts
)


# ============================================================
# SAVE URDU TRANSCRIPT
# ============================================================

try:

    with open(
        URDU_TEXT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            urdu_text
        )

except Exception as error:

    print()
    print(
        "ERROR saving urdu_transcript.txt:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# COUNT GENDERS
# ============================================================

male_count = sum(
    1
    for segment in urdu_segments
    if segment["gender"] == "male"
)

female_count = sum(
    1
    for segment in urdu_segments
    if segment["gender"] == "female"
)

unknown_count = sum(
    1
    for segment in urdu_segments
    if segment["gender"] == "unknown"
)


# ============================================================
# CREATE OUTPUT JSON
# ============================================================

output = {
    "language": "ur",

    "source_language": "en",

    "gender_source": (
        "Copied directly from Module 2 "
        "speech_segments.json"
    ),

    "audio_analysis_in_module3": False,

    "segment_count": len(urdu_segments),

    "segments": urdu_segments
}


# ============================================================
# SAVE URDU SEGMENTS
# ============================================================

try:

    with open(
        URDU_SEGMENTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=4
        )

except Exception as error:

    print()
    print(
        "ERROR saving urdu_segments.json:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("MODULE 3 COMPLETE")
print("=" * 70)

print()
print(
    "Total translated segments:",
    len(urdu_segments)
)

print(
    "Male segments:",
    male_count
)

print(
    "Female segments:",
    female_count
)

print(
    "Unknown segments:",
    unknown_count
)

print()
print(
    "Gender source:"
)

print(
    "Module 2 speech_segments.json"
)

print()
print(
    "Audio analysis performed in Module 3:"
)

print(
    "NO"
)

print()
print(
    "Gender information:"
)

print(
    "Copied from Module 2 for every segment"
)

print()
print(
    "Urdu transcript:"
)

print(
    os.path.abspath(
        URDU_TEXT_FILE
    )
)

print()
print(
    "Urdu segments:"
)

print(
    os.path.abspath(
        URDU_SEGMENTS_FILE
    )
)

print()
print("=" * 70)
print("READY FOR MODULE 4")
print("=" * 70)