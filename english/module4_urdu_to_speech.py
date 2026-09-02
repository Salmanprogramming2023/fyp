import os
import json
import asyncio
import shutil
import edge_tts


# ============================================================
# MODULE 4
# URDU TEXT -> GENDER-SPECIFIC SPEECH
#
# SINGLE SPEAKER SAFETY MODE
# ============================================================


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# INPUT
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
# MANIFEST
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
# SINGLE SPEAKER MODE
# ============================================================
#
# CURRENT VIDEO:
# ONE MALE SPEAKER
#
# Therefore force ALL sentences to male.
#
# Later, if you have a multi-speaker video:
#
#     SINGLE_SPEAKER_MODE = False
#
# ============================================================

SINGLE_SPEAKER_MODE = True

FORCED_SPEAKER_GENDER = "male"


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

print(
    "Male voice:",
    MALE_VOICE
)

print(
    "Female voice:",
    FEMALE_VOICE
)

print()

if SINGLE_SPEAKER_MODE:

    print(
        "SINGLE SPEAKER MODE: ENABLED"
    )

    print(
        "Forced gender:",
        FORCED_SPEAKER_GENDER
    )

else:

    print(
        "SINGLE SPEAKER MODE: DISABLED"
    )


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

    print(
        INPUT_FILE
    )

    raise SystemExit(1)


# ============================================================
# CLEAN OLD AUDIO
# ============================================================

if os.path.exists(
    OUTPUT_DIR
):

    print()
    print(
        "Removing old generated audio..."
    )

    try:

        shutil.rmtree(
            OUTPUT_DIR
        )

    except Exception as error:

        print()
        print(
            "ERROR removing old audio:"
        )

        print(error)

        raise SystemExit(1)


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# REMOVE OLD MANIFEST
# ============================================================

if os.path.exists(
    MANIFEST_FILE
):

    try:

        os.remove(
            MANIFEST_FILE
        )

    except Exception:

        pass


# ============================================================
# LOAD JSON
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
    print(
        "ERROR: No Urdu segments found."
    )

    raise SystemExit(1)


print()
print(
    "Total segments:",
    len(segments)
)


# ============================================================
# SELECT VOICE
# ============================================================

def get_voice(
    gender
):

    if SINGLE_SPEAKER_MODE:

        if FORCED_SPEAKER_GENDER == "female":

            return FEMALE_VOICE

        return MALE_VOICE


    gender = str(
        gender
    ).strip().lower()


    if gender == "female":

        return FEMALE_VOICE


    if gender == "male":

        return MALE_VOICE


    # Conservative default
    return MALE_VOICE


# ============================================================
# GENERATE AUDIO
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


    for index, item in enumerate(
        segments,
        start=1
    ):

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
                f"Skipping segment {index}: empty Urdu."
            )

            continue


        original_gender = str(
            item.get(
                "gender",
                "unknown"
            )
        ).strip().lower()


        # ====================================================
        # IMPORTANT
        #
        # In single-speaker mode:
        # original gender is IGNORED.
        # ====================================================

        if SINGLE_SPEAKER_MODE:

            gender = (
                FORCED_SPEAKER_GENDER
            )

        else:

            gender = original_gender


        voice = get_voice(
            gender
        )


        # ====================================================
        # COUNT
        # ====================================================

        if gender == "male":

            male_count += 1

        else:

            female_count += 1


        # ====================================================
        # TIMING
        # ====================================================

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


        # ====================================================
        # FILE
        # ====================================================

        filename = (
            f"segment_{index:04d}.mp3"
        )


        output_file = os.path.join(
            OUTPUT_DIR,
            filename
        )


        # ====================================================
        # DISPLAY
        # ====================================================

        print()
        print("-" * 70)

        print(
            f"Segment {index}/{len(segments)}"
        )

        print(
            "Original detected gender:",
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


        # ====================================================
        # GENERATE
        # ====================================================

        try:

            await create_audio(
                urdu,
                voice,
                output_file
            )

        except Exception as error:

            print()
            print(
                "ERROR generating TTS:"
            )

            print(error)

            raise SystemExit(1)


        if not os.path.exists(
            output_file
        ):

            print()
            print(
                "ERROR: Audio file was not created."
            )

            raise SystemExit(1)


        if os.path.getsize(
            output_file
        ) <= 0:

            print()
            print(
                "ERROR: Audio file is empty."
            )

            raise SystemExit(1)


        # ====================================================
        # SAVE
        # ====================================================

        output_segments.append(
            {
                "id":
                    item.get(
                        "id",
                        index
                    ),

                "start":
                    start,

                "end":
                    end,

                "duration":
                    duration,

                "english":
                    item.get(
                        "text",
                        ""
                    ),

                "urdu":
                    urdu,

                "gender":
                    gender,

                "original_detected_gender":
                    original_gender,

                "voice":
                    voice,

                "audio_file":
                    output_file
            }
        )


        print(
            "✓ Audio created"
        )


    # ========================================================
    # SAVE MANIFEST
    # ========================================================

    manifest = {

        "tts_engine":
            "Edge TTS",

        "single_speaker_mode":
            SINGLE_SPEAKER_MODE,

        "forced_gender":
            FORCED_SPEAKER_GENDER
            if SINGLE_SPEAKER_MODE
            else None,

        "male_voice":
            MALE_VOICE,

        "female_voice":
            FEMALE_VOICE,

        "segment_count":
            len(output_segments),

        "male_segments":
            male_count,

        "female_segments":
            female_count,

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


    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 70)
    print("✓ MODULE 4 COMPLETE")
    print("=" * 70)

    print()

    print(
        "Total audio segments:",
        len(output_segments)
    )

    print(
        "Male voice segments:",
        male_count
    )

    print(
        "Female voice segments:",
        female_count
    )

    print()

    print(
        "Voice used for this video:"
    )

    if SINGLE_SPEAKER_MODE:

        print(
            MALE_VOICE
            if FORCED_SPEAKER_GENDER == "male"
            else FEMALE_VOICE
        )

    print()

    print(
        "Audio folder:"
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