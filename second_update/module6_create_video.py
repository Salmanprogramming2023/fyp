import os
import subprocess
import shutil


# ============================================================
# MODULE 6
# CREATE FINAL URDU VIDEO
#
# INPUT:
#   Original video - automatically detected
#   output/urdu_dubbed_audio.wav   (written by Module 5)
#
# OUTPUT:
#   final_urdu_video.mp4
#
# The original English audio is removed.
# The synchronized Urdu audio is added.
# The original video stream is preserved.
# ============================================================


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# AUDIO FILE
# ============================================================

URDU_AUDIO = os.path.join(
    BASE_DIR,
    "output",
    "urdu_dubbed_audio.wav"
)


# ============================================================
# OUTPUT VIDEO
# ============================================================

OUTPUT_VIDEO = os.path.join(
    BASE_DIR,
    "final_urdu_video.mp4"
)


# ============================================================
# SUPPORTED VIDEO FORMATS
# ============================================================

VIDEO_EXTENSIONS = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".m4v"
]


# ============================================================
# FILES TO IGNORE
# ============================================================

IGNORED_VIDEO_NAMES = {
    "final_urdu_video.mp4",
    "output.mp4",
    "urdu_video.mp4",
    "final_video.mp4"
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


        # Ignore directories

        if not os.path.isfile(
            full_path
        ):

            continue


        extension = os.path.splitext(
            filename
        )[1].lower()


        if extension not in VIDEO_EXTENSIONS:

            continue


        if filename.lower() in (
            name.lower()
            for name in IGNORED_VIDEO_NAMES
        ):

            continue


        candidates.append(
            full_path
        )


    # --------------------------------------------------------
    # No video
    # --------------------------------------------------------

    if not candidates:

        return None


    # --------------------------------------------------------
    # Prefer common original-video names
    # --------------------------------------------------------

    preferred_names = [
        "input.mp4",
        "input_video.mp4",
        "english_video.mp4",
        "english.mp4",
        "video.mp4",
        "source.mp4"
    ]


    for preferred in preferred_names:

        preferred_path = os.path.join(
            BASE_DIR,
            preferred
        )


        if os.path.exists(
            preferred_path
        ):

            return preferred_path


    # --------------------------------------------------------
    # If only one video exists, use it
    # --------------------------------------------------------

    if len(candidates) == 1:

        return candidates[0]


    # --------------------------------------------------------
    # Multiple videos
    # Try to find largest one.
    #
    # Usually the original video is larger than generated
    # preview/output files.
    # --------------------------------------------------------

    candidates.sort(
        key=lambda path: os.path.getsize(path),
        reverse=True
    )


    return candidates[0]


# ============================================================
# MEDIA DURATION (needs ffprobe, which comes with FFmpeg)
# ============================================================

def get_duration(path):

    ffprobe = shutil.which(
        "ffprobe"
    )

    if ffprobe is None:

        return None

    try:

        output = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1",
                path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        ).stdout.strip()

        return float(output)

    except Exception:

        return None


# ============================================================
# FIND VIDEO
# ============================================================

VIDEO_FILE = find_original_video()


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 6 - CREATE FINAL URDU VIDEO")
print("=" * 70)

print()

print(
    "Working directory:"
)

print(
    BASE_DIR
)


# ============================================================
# SHOW DETECTED VIDEO
# ============================================================

print()

print(
    "Detecting original video..."
)


if VIDEO_FILE is None:

    print()
    print("=" * 70)
    print("ERROR: NO ORIGINAL VIDEO FOUND")
    print("=" * 70)

    print()

    print(
        "Put your original video inside:"
    )

    print(
        BASE_DIR
    )

    print()

    print(
        "Supported formats:"
    )

    print(
        ", ".join(
            VIDEO_EXTENSIONS
        )
    )

    print()

    print(
        "Files currently in the folder:"
    )

    for filename in os.listdir(
        BASE_DIR
    ):

        print(
            "  ",
            filename
        )

    raise SystemExit(1)


print()

print(
    "Original video detected:"
)

print(
    VIDEO_FILE
)


# ============================================================
# CHECK URDU AUDIO
# ============================================================

print()

print(
    "Checking synchronized Urdu audio..."
)


if not os.path.exists(
    URDU_AUDIO
):

    print()
    print("=" * 70)
    print("ERROR: URDU AUDIO NOT FOUND")
    print("=" * 70)

    print()

    print(
        "Expected:"
    )

    print(
        URDU_AUDIO
    )

    print()

    print(
        "Make sure Module 5 completed successfully."
    )

    raise SystemExit(1)


print()

print(
    "Urdu audio found:"
)

print(
    URDU_AUDIO
)


# ============================================================
# CHECK FFMPEG
# ============================================================

print()
print(
    "Checking FFmpeg..."
)


FFMPEG = shutil.which(
    "ffmpeg"
)


if FFMPEG is None:

    print()
    print("=" * 70)
    print("ERROR: FFMPEG NOT FOUND")
    print("=" * 70)

    print()

    print(
        "Run:"
    )

    print(
        "ffmpeg -version"
    )

    print()

    print(
        "If not found, install FFmpeg and add it to PATH."
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
        "Removing previous final video..."
    )

    try:

        os.remove(
            OUTPUT_VIDEO
        )

    except Exception as error:

        print()
        print(
            "ERROR removing old output:"
        )

        print(error)

        raise SystemExit(1)


# ============================================================
# COMPARE LENGTHS
# ============================================================

video_seconds = get_duration(
    VIDEO_FILE
)

audio_seconds = get_duration(
    URDU_AUDIO
)

if video_seconds and audio_seconds:

    print()

    print(
        f"Video length: {video_seconds:.2f}s   "
        f"Urdu audio length: {audio_seconds:.2f}s"
    )

    # Module 5 adds about 0.5 s of silence at the end, so only a
    # bigger difference means real Urdu speech runs past the video.
    if audio_seconds > video_seconds + 0.75:

        print(
            f"WARNING: the Urdu audio is "
            f"{audio_seconds - video_seconds:.2f}s longer than the video. "
            f"The end of the Urdu speech may be cut."
        )


# ============================================================
# DISPLAY PLAN
# ============================================================

print()
print("=" * 70)
print("CREATING FINAL VIDEO")
print("=" * 70)

print()

print(
    "Video input:"
)

print(
    VIDEO_FILE
)

print()

print(
    "Urdu audio input:"
)

print(
    URDU_AUDIO
)

print()

print(
    "Original English audio:"
)

print(
    "REMOVE"
)

print()

print(
    "Original video:"
)

print(
    "PRESERVE"
)


# ============================================================
# FFMPEG COMMAND
# ============================================================
#
# 0:v:0 = original video stream
# 1:a:0 = synchronized Urdu audio
#
# -c:v copy = don't re-encode video
# -c:a aac = encode Urdu audio for MP4
# -map prevents original English audio from being copied
# ============================================================

command = [

    FFMPEG,

    "-y",

    # --------------------------------------------------------
    # INPUT 1
    # --------------------------------------------------------

    "-i",
    VIDEO_FILE,

    # --------------------------------------------------------
    # INPUT 2
    # --------------------------------------------------------

    "-i",
    URDU_AUDIO,

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    "-map",
    "0:v:0",

    # --------------------------------------------------------
    # URDU AUDIO ONLY
    # --------------------------------------------------------

    "-map",
    "1:a:0",

    # --------------------------------------------------------
    # PRESERVE ORIGINAL VIDEO
    # --------------------------------------------------------

    "-c:v",
    "copy",

    # --------------------------------------------------------
    # AAC AUDIO
    # --------------------------------------------------------

    "-c:a",
    "aac",

    "-b:a",
    "192k",

    # --------------------------------------------------------
    # MP4 compatibility
    # --------------------------------------------------------

    "-movflags",
    "+faststart",

    # --------------------------------------------------------
    # Pad the audio with silence, then stop when the VIDEO ends.
    # (Without "apad", -shortest cuts the video whenever the
    #  Urdu audio is shorter than the video.)
    # --------------------------------------------------------

    "-af",
    "apad",

    "-shortest",

    OUTPUT_VIDEO
]


# ============================================================
# RUN FFMPEG
# ============================================================

print()

print(
    "Combining video and Urdu audio..."
)

print(
    "Please wait..."
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
        "ERROR starting FFmpeg:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# CHECK FFMPEG RESULT
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
        "FFmpeg completed but final video was not created."
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
    "✓ Original English audio removed"
)

print(
    "✓ Synchronized Urdu audio added"
)

print(
    "✓ Original video preserved"
)

print()

print(
    "Detected original video:"
)

print(
    VIDEO_FILE
)

print()

print(
    "Final Urdu video:"
)

print(
    OUTPUT_VIDEO
)

print()

print(
    f"File size: {file_size_mb:.2f} MB"
)

print()

print("=" * 70)
print("✓ FINAL URDU VIDEO CREATED")
print("=" * 70)