import os
import asyncio
import numpy as np
import librosa
import edge_tts
from moviepy import VideoFileClip


# ============================================================
# FILES
# ============================================================

VIDEO_FILE = "english_video.mp4"
URDU_TEXT_FILE = "urdu_transcript.txt"
OUTPUT_AUDIO = "urdu_speech.mp3"


# ============================================================
# VOICE ANALYSIS
# ============================================================

def detect_voice(video_file):

    print("Extracting original audio...")

    video = VideoFileClip(video_file)

    audio_file = "voice_analysis.wav"

    video.audio.write_audiofile(
        audio_file,
        logger=None
    )

    video.close()

    print("Analyzing original voice...")

    y, sr = librosa.load(
        audio_file,
        sr=None,
        mono=True
    )

    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=70,
        fmax=400,
        sr=sr
    )

    valid_f0 = f0[
        np.isfinite(f0)
    ]

    if len(valid_f0) == 0:

        print("Could not detect voice pitch.")

        return None

    median_pitch = float(
        np.median(valid_f0)
    )

    average_pitch = float(
        np.mean(valid_f0)
    )

    print()
    print("Average pitch:",
          round(average_pitch, 2),
          "Hz")

    print("Median pitch:",
          round(median_pitch, 2),
          "Hz")


    # --------------------------------------------------------
    # APPROXIMATE VOICE CLASSIFICATION
    # --------------------------------------------------------

    if median_pitch < 180:

        voice_type = "MALE-LIKE"

        selected_voice = "ur-PK-AsadNeural"

    else:

        voice_type = "FEMALE-LIKE"

        selected_voice = "ur-PK-UzmaNeural"


    print()
    print("Detected voice:",
          voice_type)

    print("Automatically selected:",
          selected_voice)

    return selected_voice


# ============================================================
# GENERATE URDU SPEECH
# ============================================================

async def generate_urdu_voice(
    text,
    voice
):

    print()
    print("Generating Urdu speech...")

    communicator = edge_tts.Communicate(
        text=text,
        voice=voice
    )

    await communicator.save(
        OUTPUT_AUDIO
    )

    print()
    print("Urdu speech generated:")
    print(os.path.abspath(OUTPUT_AUDIO))


# ============================================================
# MAIN
# ============================================================

if not os.path.exists(VIDEO_FILE):

    print("ERROR: Video not found.")
    exit()


if not os.path.exists(URDU_TEXT_FILE):

    print("ERROR: Urdu transcript not found.")
    exit()


# Read Urdu text
with open(
    URDU_TEXT_FILE,
    "r",
    encoding="utf-8"
) as file:

    urdu_text = file.read().strip()


if not urdu_text:

    print("ERROR: Urdu text is empty.")
    exit()


# Detect original voice automatically
selected_voice = detect_voice(
    VIDEO_FILE
)


if selected_voice is None:

    print("Voice detection failed.")
    exit()


# Generate matching Urdu voice
asyncio.run(
    generate_urdu_voice(
        urdu_text,
        selected_voice
    )
)


print()
print("=" * 60)
print("COMPLETE")
print("=" * 60)