from pathlib import Path
import json

import numpy as np
import soundfile as sf
import torch

from transformers import (
    AutoFeatureExtractor,
    AutoModelForAudioClassification,
)

import whisper


# ============================================================
# SETTINGS
# ============================================================

MODEL_NAME = "7wolf/wav2vec2-base-gender-classification"

WHISPER_MODEL_NAME = "small"
WHISPER_LANGUAGE = "en"

BASE_DIR = Path(__file__).resolve().parent

AUDIO_PATH = BASE_DIR / "english_audio.wav"

TRANSCRIPT_PATH = BASE_DIR / "english_transcript.txt"
TRANSCRIPT_SEGMENTS_PATH = (
    BASE_DIR / "transcript_segments.json"
)
SPEECH_SEGMENTS_PATH = (
    BASE_DIR / "speech_segments.json"
)
OVERALL_GENDER_PATH = (
    BASE_DIR / "overall_gender.json"
)
GENDER_WINDOWS_PATH = (
    BASE_DIR / "gender_windows.json"
)


# ============================================================
# LOAD AUDIO
# ============================================================

if not AUDIO_PATH.exists():

    raise FileNotFoundError(
        f"Audio file not found:\n{AUDIO_PATH}\n\n"
        "Run module1_extract_audio.py first."
    )


audio, sr = sf.read(
    AUDIO_PATH
)

if audio.ndim > 1:

    audio = np.mean(
        audio,
        axis=1
    )

audio = audio.astype(
    np.float32
)


print("=" * 70)
print("MODULE 2 - GENDER DETECTION + SPEECH TO TEXT")
print("=" * 70)

print(
    f"Audio file: {AUDIO_PATH}"
)

print(
    f"Sample rate: {sr}"
)

print(
    f"Duration: "
    f"{len(audio) / sr:.2f} seconds"
)


# ============================================================
# LOAD GENDER MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING GENDER MODEL")
print("=" * 70)

print(
    f"Model: {MODEL_NAME}"
)

processor = AutoFeatureExtractor.from_pretrained(
    MODEL_NAME
)

model = AutoModelForAudioClassification.from_pretrained(
    MODEL_NAME
)

model.eval()


# ============================================================
# MODEL LABELS
# ============================================================

print()
print("MODEL LABELS:")

print(
    model.config.id2label
)


# ============================================================
# GENDER DETECTION
# ============================================================
#
# THIS PART IS KEPT THE SAME AS YOUR WORKING CODE.
#
# It analyzes the FIRST 10 SECONDS.
#
# Do not change this section if this is the
# gender behavior you want to preserve.
# ============================================================

duration = min(
    180,
    len(audio) / sr
)

chunk = audio[
    :int(duration * sr)
]


inputs = processor(

    chunk,

    sampling_rate=sr,

    return_tensors="pt",

    padding=True,
)


with torch.no_grad():

    outputs = model(
        **inputs
    )

    logits = outputs.logits[0]

    probabilities = torch.softmax(
        logits,
        dim=-1,
    )


# ============================================================
# DISPLAY RAW LOGITS
# ============================================================

print()
print("RAW LOGITS:")

print(
    logits
)


# ============================================================
# DISPLAY PROBABILITIES
# ============================================================

print()
print("PROBABILITIES:")

male_probability = 0.0
female_probability = 0.0

male_label = "male"
female_label = "female"


for i, probability in enumerate(
    probabilities
):

    label = model.config.id2label.get(
        i,
        f"LABEL_{i}"
    )

    probability_value = (
        probability.item()
    )

    print(
        f"Class {i}: "
        f"{label}: "
        f"{probability_value * 100:.2f}%"
    )

    # --------------------------------------------------------
    # Save probability according to the actual model label.
    # --------------------------------------------------------

    label_lower = str(
        label
    ).lower()

    if (
        "муж" in label_lower
        or "male" in label_lower
        or label_lower == "m"
    ):

        male_probability = (
            probability_value
        )

        male_label = str(
            label
        )

    elif (
        "жен" in label_lower
        or "female" in label_lower
        or label_lower == "f"
    ):

        female_probability = (
            probability_value
        )

        female_label = str(
            label
        )


# ============================================================
# FINAL GENDER PREDICTION
# ============================================================

prediction = torch.argmax(
    probabilities
).item()


raw_prediction_label = (
    model.config.id2label[
        prediction
    ]
)


prediction_text = str(
    raw_prediction_label
).lower()


if (
    "муж" in prediction_text
    or "male" in prediction_text
    or prediction_text == "m"
):

    overall_gender = "male"

elif (
    "жен" in prediction_text
    or "female" in prediction_text
    or prediction_text == "f"
):

    overall_gender = "female"

else:

    overall_gender = "unknown"


overall_confidence = float(
    probabilities[
        prediction
    ].item()
)


print()
print("=" * 70)
print("FINAL GENDER RESULT")
print("=" * 70)

print(
    f"Gender: "
    f"{overall_gender.upper()}"
)

print(
    f"Confidence: "
    f"{overall_confidence * 100:.2f}%"
)

print(
    f"Male probability: "
    f"{male_probability * 100:.2f}%"
)

print(
    f"Female probability: "
    f"{female_probability * 100:.2f}%"
)

print(
    f"Raw prediction: "
    f"{raw_prediction_label}"
)

print("=" * 70)


# ============================================================
# SAVE GENDER INFORMATION
# ============================================================

overall_gender_data = {

    "gender":
        overall_gender,

    "confidence":
        round(
            overall_confidence,
            6
        ),

    "male_probability":
        round(
            male_probability,
            6
        ),

    "female_probability":
        round(
            female_probability,
            6
        ),

    "raw_prediction":
        str(
            raw_prediction_label
        ),

    "model":
        MODEL_NAME,

    "analysis_duration_seconds":
        round(
            duration,
            3
        ),

    "decision_method":
        "raw_wav2vec2_first_10_seconds",
}


with open(

    OVERALL_GENDER_PATH,

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        overall_gender_data,

        file,

        ensure_ascii=False,

        indent=4,
    )


# ============================================================
# GENDER WINDOWS FILE
# ============================================================
#
# Your current working gender detector uses only one
# 10-second analysis.
#
# We save that information as one window.
# ============================================================

gender_window = {

    "window_number":
        1,

    "start":
        0.0,

    "end":
        round(
            duration,
            3
        ),

    "duration":
        round(
            duration,
            3
        ),

    "gender":
        overall_gender,

    "confidence":
        round(
            overall_confidence,
            6
        ),

    "male_probability":
        round(
            male_probability,
            6
        ),

    "female_probability":
        round(
            female_probability,
            6
        ),

    "raw_prediction":
        str(
            raw_prediction_label
        ),
}


with open(

    GENDER_WINDOWS_PATH,

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        [gender_window],

        file,

        ensure_ascii=False,

        indent=4,
    )


# ============================================================
# WHISPER SPEECH TO TEXT
# ============================================================

print()
print("=" * 70)
print("LOADING WHISPER")
print("=" * 70)

print(
    f"Whisper model: "
    f"{WHISPER_MODEL_NAME}"
)

print(
    "Device: CPU"
)

print(
    "FP16: False"
)

print(
    "Loading Whisper..."
)


whisper_model = whisper.load_model(

    WHISPER_MODEL_NAME,

    device="cpu",
)


print(
    "Whisper loaded successfully."
)

print()
print(
    "Starting speech-to-text..."
)

print(
    "This may take some time on CPU."
)


# ============================================================
# WHISPER TRANSCRIPTION
# ============================================================

whisper_result = whisper_model.transcribe(

    str(AUDIO_PATH),

    language=WHISPER_LANGUAGE,

    task="transcribe",

    fp16=False,

    verbose=False,

    temperature=0,

    condition_on_previous_text=True,
)


print()
print(
    "Speech-to-text completed."
)


# ============================================================
# COMPLETE TRANSCRIPT
# ============================================================

transcript_text = str(
    whisper_result.get(
        "text",
        ""
    )
).strip()


with open(

    TRANSCRIPT_PATH,

    "w",

    encoding="utf-8",

) as file:

    file.write(
        transcript_text
    )


# ============================================================
# WHISPER SEGMENTS
# ============================================================

whisper_segments = (
    whisper_result.get(
        "segments",
        []
    )
)


transcript_segments = []
speech_segments = []


for index, segment in enumerate(
    whisper_segments
):

    start_time = float(
        segment.get(
            "start",
            0
        )
    )

    end_time = float(
        segment.get(
            "end",
            0
        )
    )

    text = str(
        segment.get(
            "text",
            ""
        )
    ).strip()


    if not text:
        continue


    segment_data = {

        "id":
            index,

        "start":
            round(
                start_time,
                3
            ),

        "end":
            round(
                end_time,
                3
            ),

        "duration":
            round(
                end_time
                - start_time,
                3
            ),

        "text":
            text,

        # ----------------------------------------------------
        # IMPORTANT:
        # Every segment gets the SAME overall gender.
        # ----------------------------------------------------

        "gender":
            overall_gender,

        "gender_confidence":
            round(
                overall_confidence,
                6
            ),
    }


    transcript_segments.append(
        segment_data
    )

    speech_segments.append(
        segment_data
    )


# ============================================================
# SAVE TRANSCRIPT SEGMENTS
# ============================================================

with open(

    TRANSCRIPT_SEGMENTS_PATH,

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        transcript_segments,

        file,

        ensure_ascii=False,

        indent=4,
    )


# ============================================================
# SAVE SPEECH SEGMENTS
# ============================================================

with open(

    SPEECH_SEGMENTS_PATH,

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        speech_segments,

        file,

        ensure_ascii=False,

        indent=4,
    )


# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 70)
print("FILES SAVED")
print("=" * 70)

print(
    f"1. {TRANSCRIPT_PATH.name}"
)

print(
    f"2. {TRANSCRIPT_SEGMENTS_PATH.name}"
)

print(
    f"3. {SPEECH_SEGMENTS_PATH.name}"
)

print(
    f"4. {OVERALL_GENDER_PATH.name}"
)

print(
    f"5. {GENDER_WINDOWS_PATH.name}"
)

print()

print(
    f"Whisper segments: "
    f"{len(speech_segments)}"
)

print(
    f"Transcript characters: "
    f"{len(transcript_text)}"
)

print()

print(
    f"Final gender: "
    f"{overall_gender.upper()}"
)

print(
    f"Gender confidence: "
    f"{overall_confidence * 100:.2f}%"
)

print()

print("=" * 70)
print("MODULE 2 COMPLETED SUCCESSFULLY")
print("=" * 70)