
import os
import json
import time
import re
import requests
from deep_translator import GoogleTranslator


# ============================================================
# MODULE 3
# ENGLISH → URDU
# GENDER + TIMING PRESERVED
#
# INPUT:
#     speech_segments.json
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

MAX_TRANSLATION_CHARS = 4500

RETRY_COUNT = 3

RETRY_DELAY = 2

REQUEST_TIMEOUT = 20


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("       MODULE 3 - ENGLISH → URDU + GENDER")
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
# CREATE TRANSLATORS
# ============================================================

print()
print("=" * 70)
print("CREATING TRANSLATOR")
print("=" * 70)


try:

    google_translator = GoogleTranslator(
        source="en",
        target="ur"
    )

except Exception as error:

    print()
    print(
        "WARNING: GoogleTranslator initialization failed."
    )

    print(error)

    google_translator = None


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
# GOOGLE TRANSLATION
# ============================================================

def translate_google(text):

    if google_translator is None:

        return None

    for attempt in range(
        1,
        RETRY_COUNT + 1
    ):

        try:

            result = google_translator.translate(
                text
            )

            if result:

                result = result.strip()

                if result:

                    return result

        except Exception as error:

            print(
                f"Retry {attempt}/{RETRY_COUNT}..."
            )

            if attempt == RETRY_COUNT:

                print(
                    "Google translation failed:"
                )

                print(error)

            time.sleep(
                RETRY_DELAY
            )

    return None


# ============================================================
# BACKUP TRANSLATION
#
# MyMemory public translation service
# ============================================================

def translate_backup(text):

    try:

        url = (
            "https://api.mymemory.translated.net/get"
        )

        params = {
            "q": text,
            "langpair": "en|ur"
        }

        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:

            return None

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

            # Reject obvious failure responses
            if (
                translated.lower()
                != text.lower()
            ):

                return translated

    except Exception as error:

        print(
            "Backup translation error:",
            error
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

    # --------------------------------------------------------
    # METHOD 1
    # GoogleTranslator
    # --------------------------------------------------------

    translated = translate_google(
        text
    )

    if translated:

        return translated


    # --------------------------------------------------------
    # METHOD 2
    # Backup translator
    # --------------------------------------------------------

    print()
    print(
        "Trying backup translation..."
    )

    translated = translate_backup(
        text
    )

    if translated:

        print(
            "✓ Backup translation successful"
        )

        return translated


    # --------------------------------------------------------
    # FINAL FALLBACK
    #
    # Do NOT stop the entire pipeline.
    # --------------------------------------------------------

    print()
    print(
        "WARNING: Translation failed."
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


urdu_segments = []

urdu_text_parts = []


for index, segment in enumerate(
    segments,
    start=1
):

    # --------------------------------------------------------
    # READ VALUES
    # --------------------------------------------------------

    english = clean_text(
        segment.get(
            "text",
            ""
        )
    )

    if not english:

        continue


    start = float(
        segment.get(
            "start",
            0
        )
    )

    end = float(
        segment.get(
            "end",
            0
        )
    )

    duration = max(
        0,
        end - start
    )


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
    # SAVE SEGMENT
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

