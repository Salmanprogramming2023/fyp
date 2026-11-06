
import os
import json
import asyncio
import shutil
import edge_tts


# ============================================================
# MODULE 4
# URDU TEXT -> GENDER-SPECIFIC SPEECH
#
# IMPORTANT:
# Gender is read from Module 2 / Module 3 JSON.
# Module 4 does NOT detect gender.
# Module 4 does NOT force one gender.
# ============================================================


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# INPUT FILE
# ============================================================

INPUT_FILE = os.path.join(
    BASE_DIR,
    "urdu_segments.json"
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "urdu_segments_audio"
)


# ============================================================
# MANIFEST FILE
# ============================================================

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
# TTS SETTINGS
# ============================================================

RATE = "+0%"
VOLUME = "+0%"
PITCH = "+0Hz"


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 4 - URDU TTS + VOICE SELECTION")
print("=" * 70)

print()
print("Running file:", os.path.abspath(__file__))
print("Input file:", INPUT_FILE)

print()
print("Male voice:", MALE_VOICE)
print("Female voice:", FEMALE_VOICE)

print()
print("MULTI-GENDER MODE: ENABLED")
print("Gender source: Module 2 / Module 3 JSON")
print("Gender detection in Module 4: DISABLED")


# ============================================================
# CHECK INPUT FILE
# ============================================================

if not os.path.exists(INPUT_FILE):

    print()
    print("ERROR: urdu_segments.json not found.")
    print("Expected location:")
    print(INPUT_FILE)

    raise SystemExit(1)


# ============================================================
# REMOVE OLD AUDIO
# ============================================================

if os.path.exists(OUTPUT_DIR):

    print()
    print("Removing old generated audio...")

    try:

        shutil.rmtree(OUTPUT_DIR)

    except Exception as error:

        print()
        print("ERROR removing old audio:")
        print(error)

        raise SystemExit(1)


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# REMOVE OLD MANIFEST
# ============================================================

if os.path.exists(MANIFEST_FILE):

    try:

        os.remove(MANIFEST_FILE)

    except Exception as error:

        print()
        print("WARNING: Could not remove old manifest.")
        print(error)


# ============================================================
# LOAD URDU SEGMENTS
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

    print()
    print("ERROR: No Urdu segments found.")

    raise SystemExit(1)


print()
print("Total segments:", len(segments))


# ============================================================
# VOICE SELECTION
# ============================================================

def get_voice(gender):

    gender = str(
        gender
    ).strip().lower()

    if gender == "female":

        return FEMALE_VOICE

    if gender == "male":

        return MALE_VOICE

    print()
    print("WARNING: Unknown gender:", repr(gender))
    print("Using male voice as conservative fallback.")

    return MALE_VOICE


# ============================================================
# CREATE AUDIO
# ============================================================

async def create_audio(
    text,
    voice,
    output_file
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=RATE,
        volume=VOLUME,
        pitch=PITCH
    )

    await communicate.save(
        output_file
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    output_segments = []

    male_count = 0
    female_count = 0
    unknown_count = 0

    for index, item in enumerate(
        segments,
        start=1
    ):

        # ----------------------------------------------------
        # READ URDU TEXT
        # ----------------------------------------------------

        urdu = str(
            item.get(
                "urdu",
                ""
            )
        ).strip()

        if not urdu:

            urdu = str(
                item.get(
                    "urdu_text",
                    ""
                )
            ).strip()

        if not urdu:

            print()
            print(
                f"Skipping segment {index}: empty Urdu text."
            )

            continue

        # ----------------------------------------------------
        # READ GENDER FROM MODULE 2 / MODULE 3
        # ----------------------------------------------------

        original_gender = str(
            item.get(
                "gender",
                "unknown"
            )
        ).strip().lower()

        # IMPORTANT:
        # Do not force male.
        # Do not force female.
        # Use the gender already stored in JSON.

        gender = original_gender

        # ----------------------------------------------------
        # SELECT VOICE
        # ----------------------------------------------------

        voice = get_voice(
            gender
        )

        # ----------------------------------------------------
        # COUNT GENDERS
        # ----------------------------------------------------

        if gender == "male":

            male_count += 1

        elif gender == "female":

            female_count += 1

        else:

            unknown_count += 1

        # ----------------------------------------------------
        # TIMING
        # ----------------------------------------------------

        start = float(
            item.get(
                "start",
                0
            )
        )

        end = float(
            item.get(
                "end",
                start
            )
        )

        duration = max(
            0,
            end - start
        )

        # ----------------------------------------------------
        # OUTPUT FILE
        # ----------------------------------------------------

        filename = (
            f"segment_{index:04d}.mp3"
        )

        output_file = os.path.join(
            OUTPUT_DIR,
            filename
        )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print()
        print("-" * 70)

        print(
            f"Segment {index}/{len(segments)}"
        )

        print(
            "Gender from JSON:",
            original_gender
        )

        print(
            "FINAL gender used:",
            gender
        )

        print(
            "FINAL VOICE:",
            voice
        )

        print(
            "Time:",
            f"{start:.3f}",
            "->",
            f"{end:.3f}"
        )

        print(
            "Urdu:",
            urdu
        )

        # ----------------------------------------------------
        # GENERATE TTS AUDIO
        # ----------------------------------------------------

        try:

            await create_audio(
                urdu,
                voice,
                output_file
            )

        except Exception as error:

            print()
            print("ERROR generating TTS audio:")
            print(error)

            raise SystemExit(1)

        # ----------------------------------------------------
        # VERIFY AUDIO FILE
        # ----------------------------------------------------

        if not os.path.exists(output_file):

            print()
            print("ERROR: Audio file was not created.")
            print(output_file)

            raise SystemExit(1)

        if os.path.getsize(output_file) <= 0:

            print()
            print("ERROR: Audio file is empty.")
            print(output_file)

            raise SystemExit(1)

        # ----------------------------------------------------
        # SAVE MANIFEST SEGMENT
        # ----------------------------------------------------

        output_segments.append(
            {
                "id": item.get(
                    "id",
                    index
                ),

                "start": start,

                "end": end,

                "duration": duration,

                "english": item.get(
                    "text",
                    ""
                ),

                "urdu": urdu,

                "gender": gender,

                "original_detected_gender": original_gender,

                "voice": voice,

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

        "tts_engine": "Edge TTS",

        "gender_source": (
            "gender field from urdu_segments.json"
        ),

        "gender_detection_in_module4": False,

        "male_voice": MALE_VOICE,

        "female_voice": FEMALE_VOICE,

        "segment_count": len(output_segments),

        "male_segments": male_count,

        "female_segments": female_count,

        "unknown_segments": unknown_count,

        "segments": output_segments
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

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("✓ MODULE 4 COMPLETE")
    print("=" * 70)

    print()
    print("Total audio segments:", len(output_segments))
    print("Male voice segments:", male_count)
    print("Female voice segments:", female_count)
    print("Unknown voice segments:", unknown_count)

    print()
    print("Male voice:", MALE_VOICE)
    print("Female voice:", FEMALE_VOICE)

    print()
    print("Audio folder:")
    print(OUTPUT_DIR)

    print()
    print("Manifest:")
    print(MANIFEST_FILE)

    print()
    print("=" * 70)
    print("✓ READY FOR MODULE 5")
    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )