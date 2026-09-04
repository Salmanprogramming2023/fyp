import os
import subprocess
import json


# ============================================================
# SETTINGS
# ============================================================

VIDEO_FILE = "english_video.mp4"
INPUT_AUDIO = "urdu_audio.mp3"
OUTPUT_AUDIO = "urdu_speech_adjusted.wav"


# ============================================================
# GET VIDEO DURATION
# ============================================================

def get_duration(filename):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        filename
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print("ERROR: Could not read duration.")

        print(result.stderr)

        raise SystemExit(1)

    data = json.loads(
        result.stdout
    )

    return float(
        data["format"]["duration"]
    )


# ============================================================
# CHECK FILES
# ============================================================

if not os.path.exists(VIDEO_FILE):

    print("ERROR: Video not found:")
    print(os.path.abspath(VIDEO_FILE))

    raise SystemExit(1)


if not os.path.exists(INPUT_AUDIO):

    print("ERROR: Urdu audio not found:")
    print(os.path.abspath(INPUT_AUDIO))

    raise SystemExit(1)


# ============================================================
# DISPLAY
# ============================================================

print("=" * 70)
print("             ADJUSTING URDU AUDIO")
print("=" * 70)


# ============================================================
# GET VIDEO DURATION
# ============================================================

video_duration = get_duration(
    VIDEO_FILE
)


print()
print(
    "Original video duration:",
    round(video_duration, 2),
    "seconds"
)


# ============================================================
# GET AUDIO DURATION
# ============================================================

audio_duration = get_duration(
    INPUT_AUDIO
)


print(
    "Original Urdu audio duration:",
    round(audio_duration, 2),
    "seconds"
)


# ============================================================
# CALCULATE SPEED
# ============================================================

speed = audio_duration / video_duration


print()
print(
    "Required speed factor:",
    round(speed, 3)
)


# ============================================================
# BUILD ATEMPO FILTER
# ============================================================

# FFmpeg atempo supports approximately
# 0.5 to 2.0 per filter.
#
# If the required change is larger,
# multiple filters are chained.

filters = []

remaining = speed


while remaining > 2.0:

    filters.append("atempo=2.0")

    remaining /= 2.0


while remaining < 0.5:

    filters.append("atempo=0.5")

    remaining /= 0.5


filters.append(
    f"atempo={remaining:.6f}"
)


filter_string = ",".join(
    filters
)


print()
print(
    "FFmpeg filter:",
    filter_string
)


# ============================================================
# ADJUST AUDIO
# ============================================================

command = [

    "ffmpeg",

    "-y",

    "-i",
    INPUT_AUDIO,

    "-filter:a",
    filter_string,

    "-ar",
    "44100",

    "-ac",
    "2",

    OUTPUT_AUDIO
]


print()
print("=" * 70)
print("ADJUSTING AUDIO SPEED")
print("=" * 70)


result = subprocess.run(
    command
)


if result.returncode != 0:

    print()
    print("ERROR: Audio adjustment failed.")

    raise SystemExit(1)


# ============================================================
# CHECK OUTPUT
# ============================================================

if not os.path.exists(
    OUTPUT_AUDIO
):

    print()
    print("ERROR: Adjusted audio was not created.")

    raise SystemExit(1)


# ============================================================
# SUCCESS
# ============================================================

new_duration = get_duration(
    OUTPUT_AUDIO
)


print()
print("=" * 70)
print("✓ AUDIO ADJUSTMENT COMPLETE")
print("=" * 70)

print()
print(
    "Original video:",
    round(video_duration, 2),
    "seconds"
)

print(
    "Adjusted Urdu audio:",
    round(new_duration, 2),
    "seconds"
)

print()
print(
    "Output:",
    os.path.abspath(OUTPUT_AUDIO)
)