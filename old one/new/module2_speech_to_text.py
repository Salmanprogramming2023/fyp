import os
import whisper


# ============================================================
# SETTINGS
# ============================================================

INPUT_AUDIO = "english_audio.wav"
OUTPUT_TEXT = "english_transcript.txt"

MODEL_NAME = "small"


# ============================================================
# CHECK AUDIO
# ============================================================

if not os.path.exists(INPUT_AUDIO):

    print("ERROR: english_audio.wav was not found.")
    print("Current folder:")
    print(os.getcwd())

    raise SystemExit(1)


# ============================================================
# DISPLAY INFORMATION
# ============================================================

print("=" * 70)
print("             SPEECH → TEXT")
print("=" * 70)

print()
print("Audio file:")
print(os.path.abspath(INPUT_AUDIO))

print()
print("Audio size:")
print(
    round(
        os.path.getsize(INPUT_AUDIO) / (1024 * 1024),
        2
    ),
    "MB"
)


# ============================================================
# LOAD WHISPER
# ============================================================

print()
print("=" * 70)
print("LOADING WHISPER MODEL")
print("=" * 70)

print()
print("Model:", MODEL_NAME)
print("This may take some time on CPU...")

try:

    model = whisper.load_model(
        MODEL_NAME
    )

except Exception as error:

    print()
    print("ERROR: Could not load Whisper.")
    print(error)

    raise SystemExit(1)


print()
print("Whisper model loaded successfully.")


# ============================================================
# TRANSCRIBE AUDIO
# ============================================================

print()
print("=" * 70)
print("TRANSCRIBING AUDIO")
print("=" * 70)

try:

    result = model.transcribe(
        INPUT_AUDIO,
        language="en",
        fp16=False
    )

except Exception as error:

    print()
    print("ERROR: Speech-to-text failed.")
    print(error)

    raise SystemExit(1)


# ============================================================
# GET TEXT
# ============================================================

english_text = result["text"].strip()


if not english_text:

    print()
    print("ERROR: Whisper produced empty text.")

    raise SystemExit(1)


# ============================================================
# SAVE TEXT
# ============================================================

try:

    with open(
        OUTPUT_TEXT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(english_text)

except Exception as error:

    print()
    print("ERROR: Could not save transcript.")
    print(error)

    raise SystemExit(1)


# ============================================================
# DISPLAY RESULT
# ============================================================

print()
print("=" * 70)
print("ENGLISH TRANSCRIPT")
print("=" * 70)

print()
print(english_text)


# ============================================================
# SUCCESS
# ============================================================

print()
print("=" * 70)
print("✓ SPEECH → TEXT COMPLETE")
print("=" * 70)

print()
print("Transcript saved to:")

print(
    os.path.abspath(OUTPUT_TEXT)
)