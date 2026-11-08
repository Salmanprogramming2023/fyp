import os
import json
import asyncio
import edge_tts


# ============================================================
# MODULE 4
# URDU TEXT -> GENDER-SPECIFIC URDU SPEECH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


INPUT_FILE = os.path.join(
    BASE_DIR,
    "urdu_segments.json"
)


OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "urdu_segments_audio"
)


MANIFEST_FILE = os.path.join(
    BASE_DIR,
    "tts_segments.json"
)


# ============================================================
# VOICES
# ============================================================

MALE_VOICE = "ur-PK-AsadNeural"

FEMALE_VOICE = "ur-PK-UzmaNeural"


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 4 - URDU TTS + GENDER VOICE")
print("=" * 70)

print()
print("Male voice:")
print(MALE_VOICE)

print()
print("Female voice:")
print(FEMALE_VOICE)


# ============================================================
# CHECK INPUT
# ============================================================

if not os.path.exists(
    INPUT_FILE
):

    print()
    print(
        "ERROR: urdu_segments.json not found."
    )

    print(INPUT_FILE)

    raise SystemExit(1)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# LOAD
# ============================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


segments = data.get(
    "segments",
    []
)


if not segments:

    print("ERROR: No Urdu segments.")

    raise SystemExit(1)


print()
print(
    "Total segments:",
    len(segments)
)


# ============================================================
# SELECT VOICE
# ============================================================

def get_voice(gender):

    gender = str(
        gender
    ).strip().lower()


    if gender == "female":

        return FEMALE_VOICE


    if gender == "male":

        return MALE_VOICE


    # Unknown defaults to male
    return MALE_VOICE


# ============================================================
# GENERATE ONE AUDIO
# ============================================================

async def create_audio(
    text,
    voice,
    output_file
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        output_file
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    output_segments = []


    for index, item in enumerate(
        segments,
        start=1
    ):

        urdu = item.get(
            "urdu",
            ""
        ).strip()


        if not urdu:

            print(
                f"Skipping segment {index}: empty text"
            )

            continue


        gender = item.get(
            "gender",
            "unknown"
        )


        voice = get_voice(
            gender
        )


        filename = (
            f"segment_{index:04d}.mp3"
        )


        output_file = os.path.join(
            OUTPUT_DIR,
            filename
        )


        print()
        print("-" * 70)

        print(
            f"Segment {index}/{len(segments)}"
        )

        print(
            "Gender:",
            gender
        )

        print(
            "VOICE:",
            voice
        )

        print(
            "Time:",
            item["start"],
            "->",
            item["end"]
        )

        print(
            "Urdu:",
            urdu
        )


        try:

            await create_audio(
                urdu,
                voice,
                output_file
            )

        except Exception as error:

            print()
            print(
                "ERROR creating TTS:"
            )

            print(error)

            raise SystemExit(1)


        if not os.path.exists(
            output_file
        ):

            print(
                "ERROR: TTS file was not created."
            )

            raise SystemExit(1)


        output_segments.append(
            {
                "id": item.get(
                    "id",
                    index
                ),

                "start": float(
                    item["start"]
                ),

                "end": float(
                    item["end"]
                ),

                "duration": float(
                    item["duration"]
                ),

                "gender": gender,

                "voice": voice,

                "urdu": urdu,

                "audio_file": output_file
            }
        )


        print(
            "✓ Audio created"
        )


    # ========================================================
    # SAVE MANIFEST
    # ========================================================

    manifest = {

        "male_voice":
            MALE_VOICE,

        "female_voice":
            FEMALE_VOICE,

        "segment_count":
            len(output_segments),

        "segments":
            output_segments
    }


    with open(
        MANIFEST_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=4
        )


    print()
    print("=" * 70)
    print("✓ MODULE 4 COMPLETE")
    print("=" * 70)

    print()
    print(
        "Audio segments:"
    )

    print(
        OUTPUT_DIR
    )

    print()
    print(
        "Manifest:"
    )

    print(
        MANIFEST_FILE
    )


# ============================================================
# RUN
# ============================================================

asyncio.run(
    main()
)