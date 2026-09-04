import os
import json
import whisper


# ============================================================
# SETTINGS
# ============================================================

AUDIO_FILE = "english_audio.wav"

TEXT_OUTPUT = "english_transcript.txt"

SEGMENT_OUTPUT = "transcript_segments.json"

MODEL_NAME = "small"


# ============================================================
# CHECK AUDIO
# ============================================================

print("=" * 70)
print("             SPEECH → TEXT")
print("=" * 70)


if not os.path.exists(AUDIO_FILE):

    print("\nERROR: Audio file not found.")

    print(
        os.path.abspath(AUDIO_FILE)
    )

    exit()


# ============================================================
# LOAD WHISPER
# ============================================================

print("\nLoading Whisper model...")

print("Model:", MODEL_NAME)

print("This may take some time on CPU...")


model = whisper.load_model(
    MODEL_NAME
)


print("\nWhisper model loaded successfully.")


# ============================================================
# TRANSCRIBE
# ============================================================

print("\nTranscribing audio...")


result = model.transcribe(
    AUDIO_FILE,
    language="en",
    fp16=False
)


segments = result["segments"]


# ============================================================
# SAVE NORMAL TRANSCRIPT
# ============================================================

full_text = result["text"].strip()


with open(
    TEXT_OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    file.write(full_text)


# ============================================================
# SAVE TIMESTAMPED TRANSCRIPT
# ============================================================

transcript_segments = []


for segment in segments:

    transcript_segments.append({

        "start": round(
            float(segment["start"]),
            3
        ),

        "end": round(
            float(segment["end"]),
            3
        ),

        "text": segment["text"].strip()

    })


with open(
    SEGMENT_OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        transcript_segments,
        file,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# DISPLAY
# ============================================================

print("\n")
print("=" * 70)
print("ENGLISH TRANSCRIPT")
print("=" * 70)

print(full_text)


print("\n")
print("=" * 70)
print("✓ SPEECH → TEXT COMPLETE")
print("=" * 70)

print("\nTranscript:")
print(
    os.path.abspath(TEXT_OUTPUT)
)

print("\nTimestamp segments:")
print(
    os.path.abspath(SEGMENT_OUTPUT)
)