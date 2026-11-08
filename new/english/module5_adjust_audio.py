import os
import json
import subprocess
import shutil
import re


# ============================================================
# MODULE 5
# URDU AUDIO TIMING + VOLUME NORMALIZATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MANIFEST_FILE = os.path.join(
    BASE_DIR,
    "tts_segments.json"
)

OUTPUT_AUDIO = os.path.join(
    BASE_DIR,
    "synchronized_urdu_audio.wav"
)

TEMP_DIR = os.path.join(
    BASE_DIR,
    "module5_temp"
)


# ============================================================
# AUDIO SETTINGS
# ============================================================

SAMPLE_RATE = 48000

CHANNELS = 2

# Target loudness
TARGET_LUFS = -16

# Peak limit
TARGET_PEAK = -1.0


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 5 - URDU AUDIO TIMING + VOLUME")
print("=" * 70)

print()

print("Manifest:")
print(MANIFEST_FILE)

print()

print("Output:")
print(OUTPUT_AUDIO)


# ============================================================
# CHECK FFMPEG
# ============================================================

FFMPEG = shutil.which(
    "ffmpeg"
)

FFPROBE = shutil.which(
    "ffprobe"
)


if FFMPEG is None:

    print()
    print("ERROR: FFmpeg not found.")

    raise SystemExit(1)


if FFPROBE is None:

    print()
    print("ERROR: FFprobe not found.")

    raise SystemExit(1)


# ============================================================
# CHECK MANIFEST
# ============================================================

if not os.path.exists(
    MANIFEST_FILE
):

    print()
    print(
        "ERROR: tts_segments.json not found."
    )

    print(
        MANIFEST_FILE
    )

    raise SystemExit(1)


# ============================================================
# LOAD MANIFEST
# ============================================================

try:

    with open(
        MANIFEST_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

except Exception as error:

    print()
    print(
        "ERROR reading tts_segments.json:"
    )

    print(error)

    raise SystemExit(1)


segments = data.get(
    "segments",
    []
)


if not segments:

    print()
    print(
        "ERROR: No TTS segments found."
    )

    raise SystemExit(1)


print()
print(
    "Total segments:",
    len(segments)
)


# ============================================================
# CREATE TEMP DIRECTORY
# ============================================================

if os.path.exists(
    TEMP_DIR
):

    shutil.rmtree(
        TEMP_DIR
    )


os.makedirs(
    TEMP_DIR,
    exist_ok=True
)


# ============================================================
# AUDIO DURATION
# ============================================================

def get_duration(
    filename
):

    command = [

        FFPROBE,

        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-of",
        "default=noprint_wrappers=1:nokey=1",

        filename
    ]


    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


    try:

        return float(
            result.stdout.strip()
        )

    except Exception:

        return 0.0


# ============================================================
# PROCESS ONE SEGMENT
# ============================================================

processed_segments = []


for index, item in enumerate(
    segments,
    start=1
):

    source = item.get(
        "audio_file",
        ""
    )


    if not source:

        source = os.path.join(
            BASE_DIR,
            "urdu_segments_audio",
            f"segment_{index:04d}.mp3"
        )


    if not os.path.isabs(
        source
    ):

        source = os.path.join(
            BASE_DIR,
            source
        )


    if not os.path.exists(
        source
    ):

        print()
        print(
            "ERROR: Audio file not found:"
        )

        print(
            source
        )

        raise SystemExit(1)


    start = float(
        item.get(
            "start",
            0
        )
    )


    end = float(
        item.get(
            "end",
            0
        )
    )


    target_duration = max(
        0.1,
        end - start
    )


    actual_duration = get_duration(
        source
    )


    if actual_duration <= 0:

        print()
        print(
            "ERROR: Could not read audio duration:"
        )

        print(
            source
        )

        raise SystemExit(1)


    print()
    print("-" * 70)

    print(
        f"Segment {index}/{len(segments)}"
    )

    print(
        "Gender:",
        item.get(
            "gender",
            "unknown"
        )
    )

    print(
        "Voice:",
        item.get(
            "voice",
            "unknown"
        )
    )

    print(
        "Original TTS duration:",
        round(
            actual_duration,
            3
        )
    )

    print(
        "Target duration:",
        round(
            target_duration,
            3
        )
    )


    # ========================================================
    # CALCULATE SPEED
    # ========================================================

    speed = (
        actual_duration
        /
        target_duration
    )


    # --------------------------------------------------------
    # Keep speech natural
    # --------------------------------------------------------

    if speed < 0.70:

        speed = 0.70

    if speed > 1.50:

        speed = 1.50


    print(
        "Speed:",
        round(
            speed,
            3
        )
    )


    processed_file = os.path.join(
        TEMP_DIR,
        f"processed_{index:04d}.wav"
    )


    # ========================================================
    # TIME + LOUDNESS NORMALIZATION
    # ========================================================

    # atempo:
    #   adjust duration
    #
    # loudnorm:
    #   normalize speech loudness
    #
    # alimiter:
    #   prevent clipping
    #

    audio_filter = (
        f"atempo={speed:.6f},"
        f"loudnorm=I={TARGET_LUFS}:TP={TARGET_PEAK}:LRA=7,"
        f"alimiter=limit=0.95"
    )


    command = [

        FFMPEG,

        "-y",

        "-i",
        source,

        "-af",
        audio_filter,

        "-ar",
        str(SAMPLE_RATE),

        "-ac",
        str(CHANNELS),

        "-c:a",
        "pcm_s16le",

        processed_file
    ]


    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )


    if result.returncode != 0:

        print()
        print(
            "ERROR processing segment:"
        )

        print(
            result.stderr
        )

        raise SystemExit(1)


    if not os.path.exists(
        processed_file
    ):

        print(
            "ERROR: Processed segment not created."
        )

        raise SystemExit(1)


    processed_duration = get_duration(
        processed_file
    )


    print(
        "Processed duration:",
        round(
            processed_duration,
            3
        )
    )


    processed_segments.append(
        {
            "file":
                processed_file,

            "start":
                start,

            "end":
                end,

            "duration":
                target_duration,

            "gender":
                item.get(
                    "gender",
                    "unknown"
                ),

            "voice":
                item.get(
                    "voice",
                    "unknown"
                )
        }
    )


# ============================================================
# CREATE SILENCE + DELAYED AUDIO
# ============================================================

print()
print("=" * 70)
print("PLACING AUDIO ON ORIGINAL TIMELINE")
print("=" * 70)


timeline_files = []


for index, item in enumerate(
    processed_segments,
    start=1
):

    source = item[
        "file"
    ]


    start_ms = int(
        round(
            item["start"] * 1000
        )
    )


    delayed_file = os.path.join(
        TEMP_DIR,
        f"timeline_{index:04d}.wav"
    )


    # --------------------------------------------------------
    # adelay sends the sentence to its original start time.
    # --------------------------------------------------------

    command = [

        FFMPEG,

        "-y",

        "-i",
        source,

        "-af",
        f"adelay={start_ms}:all=1",

        "-ar",
        str(SAMPLE_RATE),

        "-ac",
        str(CHANNELS),

        "-c:a",
        "pcm_s16le",

        delayed_file
    ]


    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )


    if result.returncode != 0:

        print()
        print(
            "ERROR placing segment on timeline:"
        )

        print(
            result.stderr
        )

        raise SystemExit(1)


    timeline_files.append(
        delayed_file
    )


# ============================================================
# MIX ALL TIMELINE AUDIO
# ============================================================

print()
print("=" * 70)
print("MIXING TIMELINE")
print("=" * 70)


inputs = []


for filename in timeline_files:

    inputs.extend(
        [
            "-i",
            filename
        ]
    )


filter_complex = (
    f"amix="
    f"inputs={len(timeline_files)}:"
    f"duration=longest:"
    f"dropout_transition=0,"
    f"loudnorm=I={TARGET_LUFS}:TP={TARGET_PEAK}:LRA=7,"
    f"alimiter=limit=0.95"
)


command = [

    FFMPEG,

    "-y"

] + inputs + [

    "-filter_complex",
    filter_complex,

    "-ar",
    str(SAMPLE_RATE),

    "-ac",
    str(CHANNELS),

    "-c:a",
    "pcm_s16le",

    OUTPUT_AUDIO
]


result = subprocess.run(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace"
)


if result.returncode != 0:

    print()
    print(
        "ERROR mixing Urdu audio:"
    )

    print(
        result.stderr
    )

    raise SystemExit(1)


# ============================================================
# VERIFY
# ============================================================

if not os.path.exists(
    OUTPUT_AUDIO
):

    print()
    print(
        "ERROR: Output audio was not created."
    )

    raise SystemExit(1)


final_duration = get_duration(
    OUTPUT_AUDIO
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("                 MODULE 5 COMPLETE")
print("=" * 70)

print()

print(
    "Segments processed:",
    len(processed_segments)
)

print()

print(
    "Final synchronized audio:"
)

print(
    OUTPUT_AUDIO
)

print()

print(
    "Final duration:",
    round(
        final_duration,
        3
    ),
    "seconds"
)

print()

print(
    "Audio loudness normalized:"
)

print(
    "YES"
)

print()

print(
    "✓ Timing synchronized"
)

print(
    "✓ Volume normalized"
)

print(
    "✓ Stereo WAV created"
)

print()

print("=" * 70)
print("✓ READY FOR MODULE 6")
print("=" * 70)