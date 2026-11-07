import os
import subprocess
import shutil


# ============================================================
# MODULE 6
# ORIGINAL VIDEO + CORRECT URDU AUDIO
#
# SINGLE SPEAKER PROJECT
#
# INPUT:
#     Original English video
#     urdu_speech_adjusted.wav
#
# OUTPUT:
#     final_urdu_video.mp4
#
# IMPORTANT:
#     Original English audio is COMPLETELY removed.
#     Only the adjusted Urdu audio is included.
# ============================================================


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# URDU AUDIO
# ============================================================

URDU_AUDIO = os.path.join(
    BASE_DIR,
    "urdu_speech_adjusted.wav"
)


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_VIDEO = os.path.join(
    BASE_DIR,
    "final_urdu_video.mp4"
)


# ============================================================
# SUPPORTED VIDEO EXTENSIONS
# ============================================================

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".m4v"
}


# ============================================================
# FILES TO IGNORE
# ============================================================

IGNORED_FILES = {
    "final_urdu_video.mp4",
    "final_video.mp4",
    "urdu_video.mp4",
    "output.mp4"
}


# ============================================================
# FIND ORIGINAL VIDEO
# ============================================================

def find_original_video():

    candidates = []


    for filename in os.listdir(
        BASE_DIR
    ):

        full_path = os.path.join(
            BASE_DIR,
            filename
        )


        if not os.path.isfile(
            full_path
        ):

            continue


        extension = os.path.splitext(
            filename
        )[1].lower()


        if extension not in VIDEO_EXTENSIONS:

            continue


        if filename.lower() in {
            name.lower()
            for name in IGNORED_FILES
        }:

            continue


        candidates.append(
            full_path
        )


    # --------------------------------------------------------
    # Preferred original video names
    # --------------------------------------------------------

    preferred_names = [
        "english_video.mp4",
        "input_video.mp4",
        "input.mp4",
        "english.mp4",
        "video.mp4",
        "source.mp4"
    ]


    for name in preferred_names:

        path = os.path.join(
            BASE_DIR,
            name
        )


        if os.path.exists(
            path
        ):

            return path


    # --------------------------------------------------------
    # If there is only one video, use it
    # --------------------------------------------------------

    if len(candidates) == 1:

        return candidates[0]


    # --------------------------------------------------------
    # Multiple videos:
    # use the largest one
    # --------------------------------------------------------

    if candidates:

        candidates.sort(
            key=lambda x: os.path.getsize(x),
            reverse=True
        )

        return candidates[0]


    return None


# ============================================================
# FIND VIDEO
# ============================================================

VIDEO_FILE = find_original_video()


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 6 - FINAL URDU VIDEO")
print("=" * 70)

print()

print(
    "Working directory:"
)

print(
    BASE_DIR
)


# ============================================================
# CHECK VIDEO
# ============================================================

if VIDEO_FILE is None:

    print()
    print(
        "ERROR: Original video was not found."
    )

    print()

    print(
        "Put the original video in:"
    )

    print(
        BASE_DIR
    )

    raise SystemExit(1)


print()

print(
    "Original video:"
)

print(
    VIDEO_FILE
)


# ============================================================
# CHECK URDU AUDIO
# ============================================================

if not os.path.exists(
    URDU_AUDIO
):

    print()
    print(
        "ERROR: Corrected Urdu audio was not found."
    )

    print()

    print(
        "Expected:"
    )

    print(
        URDU_AUDIO
    )

    print()

    print(
        "Run Module 5 first."
    )

    raise SystemExit(1)


print()

print(
    "Urdu audio:"
)

print(
    URDU_AUDIO
)


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
    print(
        "ERROR: FFmpeg not found."
    )

    raise SystemExit(1)


if FFPROBE is None:

    print()
    print(
        "ERROR: FFprobe not found."
    )

    raise SystemExit(1)


print()

print(
    "FFmpeg:"
)

print(
    FFMPEG
)


# ============================================================
# REMOVE OLD OUTPUT
# ============================================================

if os.path.exists(
    OUTPUT_VIDEO
):

    print()

    print(
        "Removing old final video..."
    )

    try:

        os.remove(
            OUTPUT_VIDEO
        )

    except Exception as error:

        print()
        print(
            "ERROR removing old final video:"
        )

        print(
            error
        )

        raise SystemExit(1)


# ============================================================
# IMPORTANT:
# CREATE VIDEO WITH ONLY ONE AUDIO STREAM
# ============================================================

print()
print("=" * 70)
print("REPLACING ORIGINAL AUDIO")
print("=" * 70)

print()

print(
    "Original English audio:"
)

print(
    "REMOVED"
)

print()

print(
    "Urdu audio:"
)

print(
    "ADDED"
)

print()

print(
    "Final MP4 audio streams:"
)

print(
    "ONLY ONE - Urdu"
)


# ============================================================
# FFMPEG COMMAND
# ============================================================
#
# 0:v:0 = only original video
#
# 1:a:0 = only Urdu audio
#
# There is NO:
#
#     0:a
#
# Therefore original English audio cannot enter the output.
#
# -map 0:v:0
# -map 1:a:0
#
# also prevents accidental extra audio streams.
# ============================================================

command = [

    FFMPEG,

    "-y",

    # --------------------------------------------------------
    # INPUT 0 = ORIGINAL VIDEO
    # --------------------------------------------------------

    "-i",
    VIDEO_FILE,

    # --------------------------------------------------------
    # INPUT 1 = URDU AUDIO
    # --------------------------------------------------------

    "-i",
    URDU_AUDIO,

    # --------------------------------------------------------
    # ONLY ORIGINAL VIDEO
    # --------------------------------------------------------

    "-map",
    "0:v:0",

    # --------------------------------------------------------
    # ONLY URDU AUDIO
    # --------------------------------------------------------

    "-map",
    "1:a:0",

    # --------------------------------------------------------
    # COPY VIDEO WITHOUT QUALITY LOSS
    # --------------------------------------------------------

    "-c:v",
    "copy",

    # --------------------------------------------------------
    # ENCODE URDU AUDIO
    # --------------------------------------------------------

    "-c:a",
    "aac",

    "-b:a",
    "192k",

    # --------------------------------------------------------
    # SINGLE AUDIO STREAM
    # --------------------------------------------------------

    "-disposition:a:0",
    "default",

    # --------------------------------------------------------
    # REMOVE SUBTITLES
    # --------------------------------------------------------

    "-sn",

    # --------------------------------------------------------
    # REMOVE ORIGINAL METADATA
    # --------------------------------------------------------

    "-map_metadata",
    "-1",

    # --------------------------------------------------------
    # REMOVE CHAPTERS
    # --------------------------------------------------------

    "-map_chapters",
    "-1",

    # --------------------------------------------------------
    # MP4 OPTIMIZATION
    # --------------------------------------------------------

    "-movflags",
    "+faststart",

    # --------------------------------------------------------
    # END WITH SHORTEST STREAM
    # --------------------------------------------------------

    "-shortest",

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    OUTPUT_VIDEO
]


# ============================================================
# RUN
# ============================================================

print()
print(
    "Creating final video..."
)

print()

try:

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

except Exception as error:

    print()
    print(
        "ERROR running FFmpeg:"
    )

    print(
        error
    )

    raise SystemExit(1)


# ============================================================
# CHECK FFmpeg
# ============================================================

if result.returncode != 0:

    print()
    print("=" * 70)
    print("❌ VIDEO CREATION FAILED")
    print("=" * 70)

    print()

    print(
        result.stderr
    )

    raise SystemExit(1)


# ============================================================
# CHECK OUTPUT
# ============================================================

if not os.path.exists(
    OUTPUT_VIDEO
):

    print()
    print(
        "ERROR:"
    )

    print(
        "Final video was not created."
    )

    raise SystemExit(1)


# ============================================================
# VERIFY FINAL VIDEO AUDIO STREAMS
# ============================================================

print()
print("=" * 70)
print("VERIFYING FINAL VIDEO")
print("=" * 70)


probe_command = [

    FFPROBE,

    "-v",
    "error",

    "-select_streams",
    "a",

    "-show_entries",
    "stream=index:stream_tags=language",

    "-of",
    "default=noprint_wrappers=1",

    OUTPUT_VIDEO
]


probe_result = subprocess.run(

    probe_command,

    stdout=subprocess.PIPE,

    stderr=subprocess.PIPE,

    text=True,

    encoding="utf-8",

    errors="replace"
)


print()

print(
    "Audio streams found in final video:"
)

print(
    probe_result.stdout
)


# ============================================================
# COUNT AUDIO STREAMS
# ============================================================

audio_stream_count = 0


for line in probe_result.stdout.splitlines():

    if line.startswith(
        "index="
    ):

        audio_stream_count += 1


print()

print(
    "Audio stream count:",
    audio_stream_count
)


# ============================================================
# CRITICAL CHECK
# ============================================================

if audio_stream_count != 1:

    print()
    print("=" * 70)
    print("❌ AUDIO STREAM VERIFICATION FAILED")
    print("=" * 70)

    print()

    print(
        "Expected exactly 1 audio stream."
    )

    print(
        "Found:",
        audio_stream_count
    )

    raise SystemExit(1)


# ============================================================
# FILE SIZE
# ============================================================

file_size_mb = (

    os.path.getsize(
        OUTPUT_VIDEO
    )

    /

    (1024 * 1024)
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("              MODULE 6 COMPLETE")
print("=" * 70)

print()

print(
    "✓ Original video preserved"
)

print(
    "✓ Original English audio removed"
)

print(
    "✓ Correct Urdu audio added"
)

print(
    "✓ Only ONE audio stream exists"
)

print(
    "✓ Urdu audio set as default"
)

print()

print(
    "Final video:"
)

print(
    os.path.abspath(
        OUTPUT_VIDEO
    )
)

print()

print(
    "File size:",
    f"{file_size_mb:.2f} MB"
)

print()

print("=" * 70)
print("✓ FINAL URDU VIDEO CREATED")
print("=" * 70)