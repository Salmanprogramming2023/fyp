
import os
import json
import time
import re
import requests


# ============================================================
# MODULE 3
# ENGLISH → URDU
# MYMEMORY TRANSLATION ONLY
#
# INPUT:
#     speech_segments.json
#
# OUTPUT:
#     urdu_transcript.txt
#     urdu_segments.json
#
# TRANSLATION:
#     MyMemory API ONLY
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
print("       MYMEMORY TRANSLATION ONLY")
print("=" * 70)

print()
print("Input:")
print(INPUT_FILE)

print()
print("Urdu transcript:")
print(URDU_TEXT_FILE)

print()
print("Urdu segment information:")
print(URDU_SEGMENTS_FILE)

print()
print("Translation service:")
print("MyMemory API ONLY")


# ============================================================
# CHECK INPUT
# ============================================================

if not os.path.exists(INPUT_FILE):

    print()
    print("ERROR:")
    print("speech_segments.json was not found.")

    print()
    print("Expected:")
    print(INPUT_FILE)

    raise SystemExit(1)


# ============================================================
# LOAD SPEECH SEGMENTS
# ============================================================

print()
print("=" * 70)
print("LOADING SPEECH SEGMENTS")
print("=" * 70)


try:

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

except Exception as error:

    print()
    print("ERROR loading speech_segments.json:")
    print(error)

    raise SystemExit(1)


# ============================================================
# SUPPORT DIFFERENT JSON FORMATS
# ============================================================

if isinstance(data, dict):

    segments = data.get(
        "segments",
        []
    )

elif isinstance(data, list):

    segments = data

else:

    segments = []


if not segments:

    print()
    print("ERROR:")
    print("No speech segments found.")

    raise SystemExit(1)


print()
print(
    "Total segments:",
    len(segments)
)


# ============================================================
# CLEAN TEXT
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

    """
    Translate English → Urdu using MyMemory API.

    No Google Translator is used.
    """

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

                    time.sleep(
                        RETRY_DELAY
                    )

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


            if translated:

                translated = translated.strip()


                # ------------------------------------------------
                # Reject empty result
                # ------------------------------------------------

                if not translated:

                    if attempt < RETRY_COUNT:

                        time.sleep(
                            RETRY_DELAY
                        )

                    continue


                # ------------------------------------------------
                # Reject obvious untranslated result
                # ------------------------------------------------

                if (
                    translated.lower()
                    == text.lower()
                ):

                    print(
                        "WARNING: MyMemory returned "
                        "the original English text."
                    )

                    if attempt < RETRY_COUNT:

                        time.sleep(
                            RETRY_DELAY
                        )

                    continue


                print(
                    "✓ MyMemory translation successful"
                )

                return translated


        except Exception as error:

            print(
                "MyMemory translation error:",
                error
            )


        if attempt < RETRY_COUNT:

            print(
                f"Waiting {RETRY_DELAY} seconds..."
            )

            time.sleep(
                RETRY_DELAY
            )


    return None


# ============================================================
# MAIN TRANSLATION FUNCTION
# ============================================================

def translate_sentence(text):

    text = clean_text(
        text
    )

    if not text:

        return ""


    # ========================================================
    # MYMEMORY ONLY
    # ========================================================

    translated = translate_mymemory(
        text
    )


    if translated:

        return translated


    # ========================================================
    # FINAL FALLBACK
    #
    # Do not stop the entire pipeline.
    # Keep original English text if translation fails.
    # ========================================================

    print()
    print(
        "WARNING: MyMemory translation failed."
    )

    print(
        "Keeping original English text "
        "for this segment."
    )

    return text


# ============================================================
# TRANSLATE SEGMENTS
# ============================================================

print()
print("=" * 70)
print("TRANSLATING SENTENCES")
print("=" * 70)

print()
print(
    "Translation engine: MyMemory ONLY"
)


urdu_segments = []

urdu_text_parts = []


for index, segment in enumerate(
    segments,
    start=1
):

    # --------------------------------------------------------
    # READ ENGLISH TEXT
    # --------------------------------------------------------

    english = clean_text(
        segment.get(
            "text",
            ""
        )
    )


    if not english:

        continue


    # --------------------------------------------------------
    # READ TIMING
    # --------------------------------------------------------

    try:

        start = float(
            segment.get(
                "start",
                0
            )
        )

    except Exception:

        start = 0.0


    try:

        end = float(
            segment.get(
                "end",
                0
            )
        )

    except Exception:

        end = start


    duration = max(
        0,
        end - start
    )


    # --------------------------------------------------------
    # READ GENDER
    # --------------------------------------------------------

    gender = str(
        segment.get(
            "gender",
            "unknown"
        )
    ).lower().strip()


    # --------------------------------------------------------
    # NORMALIZE GENDER
    # --------------------------------------------------------

    if gender not in (
        "male",
        "female",
        "unknown"
    ):

        gender = "unknown"


    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print()
    print("-" * 70)

    print(
        f"Sentence {index}/{len(segments)}"
    )

    print(
        f"Time: {start:.3f} -> {end:.3f}"
    )

    print(
        "Duration:",
        f"{duration:.3f}s"
    )

    print(
        "Gender:",
        gender
    )

    print(
        "English:",
        english
    )


    # --------------------------------------------------------
    # TRANSLATE
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

    print(
        "✓ Completed"
    )


    # --------------------------------------------------------
    # CREATE URDU SEGMENT
    # --------------------------------------------------------

    urdu_segment = {

        "id":
            len(urdu_segments) + 1,

        "start":
            round(
                start,
                3
            ),

        "end":
            round(
                end,
                3
            ),

        "duration":
            round(
                duration,
                3
            ),

        "english":
            english,

        "urdu":
            urdu,

        "gender":
            gender
    }


    # --------------------------------------------------------
    # PRESERVE OPTIONAL SPEAKER INFORMATION
    # --------------------------------------------------------

    if "speaker" in segment:

        urdu_segment[
            "speaker"
        ] = segment[
            "speaker"
        ]


    if "speaker_index" in segment:

        urdu_segment[
            "speaker_index"
        ] = segment[
            "speaker_index"
        ]


    if "pitch" in segment:

        urdu_segment[
            "pitch"
        ] = segment[
            "pitch"
        ]


    if "confidence" in segment:

        urdu_segment[
            "confidence"
        ] = segment[
            "confidence"
        ]


    # --------------------------------------------------------
    # SAVE SEGMENT IN MEMORY
    # --------------------------------------------------------

    urdu_segments.append(
        urdu_segment
    )


    urdu_text_parts.append(
        urdu
    )


# ============================================================
# CHECK RESULT
# ============================================================

if not urdu_segments:

    print()
    print(
        "ERROR:"
    )

    print(
        "No translated segments were created."
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
        "ERROR saving Urdu transcript:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# CREATE OUTPUT JSON
# ============================================================

output = {

    "language":
        "ur",

    "source_language":
        "en",

    "segment_count":
        len(urdu_segments),

    "segments":
        urdu_segments
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
# SUMMARY
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
# FINAL OUTPUT
# ============================================================

print()
print("=" * 70)
print("✓ MODULE 3 COMPLETE")
print("=" * 70)

print()

print(
    "Translation service:"
)

print(
    "✓ MyMemory API ONLY"
)

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
    "Urdu transcript:"
)

print(
    os.path.abspath(
        URDU_TEXT_FILE
    )
)

print()

print(
    "Urdu segment information:"
)

print(
    os.path.abspath(
        URDU_SEGMENTS_FILE
    )
)

print()

print(
    "Gender information preserved:"
)

print(
    "✓ Male"
)

print(
    "✓ Female"
)

print(
    "✓ Unknown"
)

print()

print(
    "Timing information preserved:"
)

print(
    "✓ Start time"
)

print(
    "✓ End time"
)

print(
    "✓ Duration"
)

print()

print("=" * 70)
print("READY FOR MODULE 4")
print("=" * 70)