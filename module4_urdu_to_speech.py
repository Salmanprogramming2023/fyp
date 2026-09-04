import os
import json
import asyncio

import numpy as np
import librosa
import torch

try:
    from transformers import (
        AutoFeatureExtractor,
        AutoModelForAudioClassification
    )
except ImportError:
    print("=" * 70)
    print("ERROR: 'transformers' package is not installed.")
    print("=" * 70)
    print()
    print("Run this command:")
    print()
    print("python -m pip install transformers")
    print()
    raise SystemExit(1)

try:
    import edge_tts
except ImportError:
    print("=" * 70)
    print("ERROR: 'edge-tts' package is not installed.")
    print("=" * 70)
    print()
    print("Run this command:")
    print()
    print("python -m pip install edge-tts")
    print()
    raise SystemExit(1)

# ============================================================
# MODULE 4
# SINGLE SPEAKER
# AUDIO GENDER DETECTION + URDU TTS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# INPUT
# ============================================================

ENGLISH_AUDIO = os.path.join(
    BASE_DIR,
    "english_audio.wav"
)

URDU_TEXT = os.path.join(
    BASE_DIR,
    "urdu_transcript.txt"
)


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_AUDIO = os.path.join(
    BASE_DIR,
    "urdu_audio.mp3"
)

INFO_FILE = os.path.join(
    BASE_DIR,
    "tts_info.json"
)


# ============================================================
# GENDER MODEL
# ============================================================

GENDER_MODEL = (
    "7wolf/wav2vec2-base-gender-classification"
)


# ============================================================
# URDU VOICES
# ============================================================

MALE_VOICE = "ur-PK-AsadNeural"

FEMALE_VOICE = "ur-PK-UzmaNeural"


# ============================================================
# SETTINGS
# ============================================================

SAMPLE_RATE = 16000

SAMPLE_SECONDS = 5.0

MAX_SAMPLES = 20

MIN_SAMPLE_SECONDS = 2.0

MIN_CONFIDENCE = 0.55


# ============================================================
# MANUAL FALLBACK
# ============================================================
#
# IMPORTANT:
#
# "auto" = use the audio classifier
#
# "male" = force male
#
# "female" = force female
#
# Do NOT use face appearance to infer gender.
#
# ============================================================

MANUAL_GENDER = "auto"


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 4 - SINGLE SPEAKER GENDER + URDU TTS")
print("=" * 70)

print()

print(
    "Gender model:"
)

print(
    GENDER_MODEL
)

print()

print(
    "Mode:"
)

print(
    "Single speaker / one gender / one voice"
)

print()

print(
    "Manual gender setting:"
)

print(
    MANUAL_GENDER
)


# ============================================================
# CHECK INPUT
# ============================================================

if not os.path.exists(
    ENGLISH_AUDIO
):

    print()
    print(
        "ERROR: english_audio.wav not found."
    )

    print(
        ENGLISH_AUDIO
    )

    raise SystemExit(1)


if not os.path.exists(
    URDU_TEXT
):

    print()
    print(
        "ERROR: urdu_transcript.txt not found."
    )

    print(
        URDU_TEXT
    )

    raise SystemExit(1)


# ============================================================
# LOAD AUDIO
# ============================================================

print()
print("=" * 70)
print("LOADING ENGLISH AUDIO")
print("=" * 70)


try:

    audio, sr = librosa.load(
        ENGLISH_AUDIO,
        sr=SAMPLE_RATE,
        mono=True
    )

except Exception as error:

    print()
    print(
        "ERROR loading audio:"
    )

    print(
        error
    )

    raise SystemExit(1)


duration = (
    len(audio)
    /
    sr
)


print()

print(
    "Duration:",
    round(
        duration,
        2
    ),
    "seconds"
)


# ============================================================
# CREATE SAMPLES
# ============================================================

print()
print("=" * 70)
print("CREATING VOICE SAMPLES")
print("=" * 70)


if duration <= SAMPLE_SECONDS:

    sample_starts = [
        0.0
    ]

else:

    possible_samples = int(
        duration
        /
        SAMPLE_SECONDS
    )


    sample_count = min(
        possible_samples,
        MAX_SAMPLES
    )


    sample_starts = np.linspace(
        0,
        max(
            0,
            duration - SAMPLE_SECONDS
        ),
        sample_count
    )


samples = []


for start in sample_starts:

    start = float(
        start
    )

    end = min(
        duration,
        start + SAMPLE_SECONDS
    )


    if (
        end - start
        >=
        MIN_SAMPLE_SECONDS
    ):

        samples.append(
            (
                start,
                end
            )
        )


print()

print(
    "Samples:",
    len(samples)
)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING GENDER CLASSIFIER")
print("=" * 70)


try:

    extractor = AutoFeatureExtractor.from_pretrained(
        GENDER_MODEL
    )

    gender_model = (
        AutoModelForAudioClassification.from_pretrained(
            GENDER_MODEL
        )
    )

except Exception as error:

    print()
    print(
        "ERROR loading gender model:"
    )

    print(
        error
    )

    raise SystemExit(1)


device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


gender_model.to(
    device
)

gender_model.eval()


print()

print(
    "Device:",
    device
)


# ============================================================
# LABELS
# ============================================================

id2label = {}

for key, value in (
    gender_model.config.id2label.items()
):

    try:

        id2label[
            int(key)
        ] = str(value)

    except Exception:

        pass


print()

print(
    "Model labels:"
)

print(
    id2label
)


# ============================================================
# NORMALIZE MODEL LABEL
# ============================================================
#
# THIS FIXES YOUR CURRENT PROBLEM:
#
# Мужской = Male
# Женский  = Female
# ============================================================

def normalize_gender(
    label
):

    label = str(
        label
    ).strip().lower()


    # English

    if "female" in label:
        return "female"

    if "woman" in label:
        return "female"

    if "male" in label:
        return "male"

    if "man" in label:
        return "male"


    # Russian

    if "женск" in label:
        return "female"

    if "жен" in label:
        return "female"

    if "мужск" in label:
        return "male"

    if "муж" in label:
        return "male"


    return "unknown"


# ============================================================
# CLASSIFY SAMPLE
# ============================================================

def classify_sample(
    sample_audio
):

    inputs = extractor(
        sample_audio,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
        padding=True
    )


    inputs = {
        key: value.to(device)
        for key, value
        in inputs.items()
    }


    with torch.no_grad():

        outputs = gender_model(
            **inputs
        )


    probabilities = torch.softmax(
        outputs.logits,
        dim=-1
    )[0]


    prediction_id = int(
        torch.argmax(
            probabilities
        ).item()
    )


    confidence = float(
        probabilities[
            prediction_id
        ].item()
    )


    raw_label = id2label.get(
        prediction_id,
        "unknown"
    )


    gender = normalize_gender(
        raw_label
    )


    male_probability = 0.0

    female_probability = 0.0


    for class_id, probability in enumerate(
        probabilities
    ):

        raw = id2label.get(
            class_id,
            "unknown"
        )


        normalized = normalize_gender(
            raw
        )


        value = float(
            probability.item()
        )


        if normalized == "male":

            male_probability += value


        elif normalized == "female":

            female_probability += value


    return {

        "gender":
            gender,

        "raw_label":
            raw_label,

        "confidence":
            confidence,

        "male_probability":
            male_probability,

        "female_probability":
            female_probability
    }


# ============================================================
# AUDIO CLASSIFICATION
# ============================================================

predictions = []


if MANUAL_GENDER == "auto":

    print()
    print("=" * 70)
    print("ANALYZING AUDIO")
    print("=" * 70)


    for number, (
        start,
        end
    ) in enumerate(
        samples,
        start=1
    ):

        start_sample = int(
            start * sr
        )

        end_sample = int(
            end * sr
        )


        sample_audio = audio[
            start_sample:end_sample
        ]


        peak = np.max(
            np.abs(sample_audio)
        )


        if peak > 0:

            sample_audio = (
                sample_audio / peak
            )


        print()
        print("-" * 70)

        print(
            f"Sample {number}/{len(samples)}"
        )

        print(
            f"Time: {start:.2f} -> {end:.2f}"
        )


        try:

            prediction = classify_sample(
                sample_audio
            )


        except Exception as error:

            print()
            print(
                "WARNING:"
            )

            print(
                error
            )

            continue


        print()

        print(
            "Raw model label:",
            prediction["raw_label"]
        )

        print(
            "Normalized gender:",
            prediction["gender"]
        )

        print(
            "Confidence:",
            round(
                prediction["confidence"],
                3
            )
        )

        print(
            "Male probability:",
            round(
                prediction["male_probability"],
                3
            )
        )

        print(
            "Female probability:",
            round(
                prediction["female_probability"],
                3
            )
        )


        predictions.append(
            prediction
        )


else:

    print()
    print(
        "Automatic classification skipped."
    )

    print(
        "Using manual gender:",
        MANUAL_GENDER
    )


# ============================================================
# GLOBAL DECISION
# ============================================================

if MANUAL_GENDER in (
    "male",
    "female"
):

    detected_gender = MANUAL_GENDER

    global_confidence = 1.0

    male_votes = 0

    female_votes = 0


else:

    male_votes = 0

    female_votes = 0

    male_probability_total = 0.0

    female_probability_total = 0.0


    for prediction in predictions:

        if (
            prediction["confidence"]
            >=
            MIN_CONFIDENCE
        ):

            if prediction["gender"] == "male":

                male_votes += 1

            elif prediction["gender"] == "female":

                female_votes += 1


        male_probability_total += (
            prediction[
                "male_probability"
            ]
        )


        female_probability_total += (
            prediction[
                "female_probability"
            ]
        )


    count = max(
        1,
        len(predictions)
    )


    average_male_probability = (
        male_probability_total
        /
        count
    )


    average_female_probability = (
        female_probability_total
        /
        count
    )


    # --------------------------------------------------------
    # Global decision
    # --------------------------------------------------------

    if male_votes > female_votes:

        detected_gender = "male"

    elif female_votes > male_votes:

        detected_gender = "female"

    else:

        if (
            average_female_probability
            >
            average_male_probability
        ):

            detected_gender = "female"

        else:

            detected_gender = "male"


    vote_total = (
        male_votes
        +
        female_votes
    )


    if vote_total > 0:

        vote_confidence = (
            max(
                male_votes,
                female_votes
            )
            /
            vote_total
        )

    else:

        vote_confidence = 0.0


    probability_difference = abs(
        average_male_probability
        -
        average_female_probability
    )


    global_confidence = round(
        (
            vote_confidence
            *
            0.5
        )
        +
        (
            probability_difference
            *
            0.5
        ),
        3
    )


# ============================================================
# SELECT TTS VOICE
# ============================================================

if detected_gender == "female":

    selected_voice = FEMALE_VOICE

else:

    selected_voice = MALE_VOICE


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 70)
print("FINAL GLOBAL GENDER")
print("=" * 70)

print()

print(
    "Detected gender:",
    detected_gender.upper()
)

print()

print(
    "Confidence:",
    global_confidence
)

print()

print(
    "Selected Urdu voice:"
)

print(
    selected_voice
)


# ============================================================
# READ URDU TRANSCRIPT
# ============================================================

print()
print("=" * 70)
print("LOADING URDU TRANSCRIPT")
print("=" * 70)


with open(
    URDU_TEXT,
    "r",
    encoding="utf-8"
) as file:

    urdu_text = file.read().strip()


if not urdu_text:

    print(
        "ERROR: Urdu transcript is empty."
    )

    raise SystemExit(1)


# ============================================================
# REMOVE OLD AUDIO
# ============================================================

if os.path.exists(
    OUTPUT_AUDIO
):

    try:

        os.remove(
            OUTPUT_AUDIO
        )

    except Exception:

        pass


# ============================================================
# GENERATE URDU AUDIO
# ============================================================

print()
print("=" * 70)
print("GENERATING URDU AUDIO")
print("=" * 70)

print()

print(
    "Voice:",
    selected_voice
)


async def generate_audio():

    communicator = edge_tts.Communicate(

        text=urdu_text,

        voice=selected_voice,

        rate="+0%",

        volume="+0%",

        pitch="+0Hz"
    )


    await communicator.save(
        OUTPUT_AUDIO
    )


try:

    asyncio.run(
        generate_audio()
    )

except Exception as error:

    print()
    print(
        "ERROR generating Urdu audio:"
    )

    print(
        error
    )

    raise SystemExit(1)


# ============================================================
# CHECK OUTPUT
# ============================================================

if not os.path.exists(
    OUTPUT_AUDIO
):

    print()
    print(
        "ERROR: Urdu audio was not created."
    )

    raise SystemExit(1)


file_size = os.path.getsize(
    OUTPUT_AUDIO
)


# ============================================================
# SAVE INFO
# ============================================================

info = {

    "project_type":
        "single_speaker",

    "gender_model":
        GENDER_MODEL,

    "detected_gender":
        detected_gender,

    "confidence":
        global_confidence,

    "male_votes":
        male_votes,

    "female_votes":
        female_votes,

    "selected_voice":
        selected_voice,

    "audio_file":
        OUTPUT_AUDIO,

    "file_size_bytes":
        file_size,

    "sample_count":
        len(
            predictions
        )
}


with open(
    INFO_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        info,
        file,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("✓ MODULE 4 COMPLETE")
print("=" * 70)

print()

print(
    "Detected gender:",
    detected_gender.upper()
)

print(
    "Confidence:",
    global_confidence
)

print()

print(
    "Selected Urdu voice:"
)

print(
    selected_voice
)

print()

print(
    "Urdu audio:"
)

print(
    OUTPUT_AUDIO
)

print()

print(
    "Information:"
)

print(
    INFO_FILE
)

print()

print(
    "✓ ONE GENDER"
)

print(
    "✓ ONE VOICE"
)

print(
    "✓ ENTIRE VIDEO"
)

print("=" * 70)