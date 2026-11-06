import os
from moviepy import VideoFileClip


# ============================================================
# FILE SETTINGS
# ============================================================

INPUT_VIDEO = "english_video.mp4"
OUTPUT_AUDIO = "english_audio.wav"


# ============================================================
# CHECK VIDEO
# ============================================================

if not os.path.exists(INPUT_VIDEO):
    print("ERROR: english_video.mp4 was not found.")
    exit()


# ============================================================
# EXTRACT AUDIO
# ============================================================

print("======================================")
print("EXTRACTING AUDIO")
print("======================================")

video = VideoFileClip(INPUT_VIDEO)

if video.audio is None:
    print("ERROR: The video has no audio track.")
    video.close()
    exit()


video.audio.write_audiofile(
    OUTPUT_AUDIO,
    fps=16000,
    nbytes=2,
    codec="pcm_s16le",
    logger=None
)

video.close()


# ============================================================
# CHECK RESULT
# ============================================================

if os.path.exists(OUTPUT_AUDIO):

    size = os.path.getsize(OUTPUT_AUDIO)

    print("\n======================================")
    print("SUCCESS")
    print("======================================")

    print("Audio extracted successfully.")
    print("Audio file:")
    print(os.path.abspath(OUTPUT_AUDIO))

    print(
        "File size:",
        round(size / 1024, 2),
        "KB"
    )

else:

    print("ERROR: Audio file was not created.")