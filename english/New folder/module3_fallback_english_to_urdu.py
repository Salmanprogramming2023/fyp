import os
import json
import sys
import re


# ============================================================
# MODULE 3 FALLBACK
# ENGLISH → URDU
# NLLB TRANSLATION
# ============================================================
#
# This module is executed ONLY when Module 3 fails.
#
# INPUT:
#     speech_segments.json
#
# OUTPUT:
#     urdu_transcript.txt
#     urdu_segments.json
#
# MODEL:
#     facebook/nllb-200-distilled-600M
#
# English:
#     eng_Latn
#
# Urdu:
#     urd_Arab
#
# ============================================================


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# FILES
# ============================================================

INPUT_FILE = os.path.join(
    BASE_DIR,
    "speech_segments.json"
)


OUTPUT_TEXT = os.path.join(
    BASE_DIR,
    "urdu_transcript.txt"
)


OUTPUT_SEGMENTS = os.path.join(
    BASE_DIR,
    "urdu_segments.json"
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = (
    "facebook/nllb-200-distilled-600M"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("       MODULE 3 FALLBACK - ENGLISH → URDU")
print("=" * 70)

print()

print(
    "Primary Module 3 failed."
)

print()

print(
    "Fallback translator:"
)

print(
    MODEL_NAME
)

print()

print(
    "English:",
    "eng_Latn"
)

print(
    "Urdu:",
    "urd_Arab"
)


# ============================================================
# CHECK INPUT
# ============================================================

if not os.path.exists(
    INPUT_FILE
):

    print()
    print(
        "ERROR: speech_segments.json was not found."
    )

    print(
        INPUT_FILE
    )

    raise SystemExit(1)


# ============================================================
# IMPORT TRANSFORMERS
# ============================================================

print()
print("=" * 70)
print("LOADING NLLB")
print("=" * 70)


try:

    import torch

    from transformers import (
        AutoTokenizer,
        AutoModelForSeq2SeqLM
    )

except Exception as error:

    print()
    print(
        "ERROR: Required NLLB packages are not installed."
    )

    print()

    print(
        "Install them with:"
    )

    print()

    print(
        "pip install torch transformers sentencepiece"
    )

    print()

    print(
        "Original error:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# LOAD DATA
# ============================================================

try:

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

except Exception as error:

    print()
    print(
        "ERROR reading speech_segments.json:"
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
        "ERROR: No speech segments found."
    )

    raise SystemExit(1)


print()
print(
    "Segments:",
    len(segments)
)


# ============================================================
# DEVICE
# ============================================================

if torch.cuda.is_available():

    device = torch.device(
        "cuda"
    )

    print()
    print(
        "Device: CUDA GPU"
    )

else:

    device = torch.device(
        "cpu"
    )

    print()
    print(
        "Device: CPU"
    )

    print(
        "NLLB may take some time on CPU."
    )


# ============================================================
# LOAD TOKENIZER
# ============================================================

print()
print(
    "Loading tokenizer..."
)


try:

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        src_lang="eng_Latn"
    )

except Exception as error:

    print()
    print(
        "ERROR loading tokenizer:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print(
    "Loading NLLB model..."
)

print(
    "First run may download the model."
)

print(
    "This can take some time."
)


try:

    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME
    )

    model.to(
        device
    )

    model.eval()

except Exception as error:

    print()
    print(
        "ERROR loading NLLB model:"
    )

    print(error)

    raise SystemExit(1)


print()
print(
    "✓ NLLB model loaded."
)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(
    text
):

    text = str(
        text
    ).strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# TRANSLATE ONE SENTENCE
# ============================================================

def translate_sentence(
    text
):

    text = clean_text(
        text
    )

    if not text:

        return ""


    try:

        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )


        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }


        with torch.no_grad():

            generated_tokens = (
                model.generate(
                    **inputs,

                    forced_bos_token_id=
                        tokenizer.convert_tokens_to_ids(
                            "urd_Arab"
                        ),

                    max_length=512,

                    num_beams=4,

                    early_stopping=True
                )
            )


        translated = tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True
        )[0]


        return clean_text(
            translated
        )


    except Exception as error:

        print()
        print(
            "Translation error:"
        )

        print(error)

        return ""


# ============================================================
# TRANSLATE SEGMENTS
# ============================================================

print()
print("=" * 70)
print("TRANSLATING WITH NLLB")
print("=" * 70)


urdu_segments = []


for number, segment in enumerate(
    segments,
    start=1
):

    english_text = clean_text(
        segment.get(
            "text",
            ""
        )
    )


    if not english_text:

        print()
        print(
            f"WARNING: Segment {number} is empty."
        )

        continue


    start = float(
        segment.get(
            "start",
            0
        )
    )


    end = float(
        segment.get(
            "end",
            0
        )
    )


    duration = float(
        segment.get(
            "duration",
            end - start
        )
    )


    gender = segment.get(
        "gender",
        "unknown"
    )


    pitch = segment.get(
        "pitch",
        0
    )


    confidence = segment.get(
        "confidence",
        0
    )


    print()
    print("-" * 70)

    print(
        f"Segment {number}/{len(segments)}"
    )

    print(
        f"Time: {start:.3f} → {end:.3f}"
    )

    print(
        "Gender:",
        gender
    )

    print(
        "English:",
        english_text
    )


    translated = translate_sentence(
        english_text
    )


    if not translated:

        print()
        print(
            "ERROR: NLLB could not translate this sentence."
        )

        print(
            english_text
        )

        raise SystemExit(1)


    print(
        "Urdu:",
        translated
    )


    # --------------------------------------------------------
    # Preserve Module 2 information.
    # --------------------------------------------------------

    urdu_segments.append(
        {
            "id":
                len(
                    urdu_segments
                ) + 1,

            "start":
                round(
                    start,
                    3
                ),

            "end":
                round(
                    end,
                    3
                ),

            "duration":
                round(
                    duration,
                    3
                ),

            "text":
                english_text,

            "urdu":
                translated,

            "gender":
                gender,

            "pitch":
                pitch,

            "confidence":
                confidence
        }
    )


# ============================================================
# CHECK RESULT
# ============================================================

if not urdu_segments:

    print()
    print(
        "ERROR: No translations were generated."
    )

    raise SystemExit(1)


# ============================================================
# SAVE URDU TEXT
# ============================================================

urdu_text = "\n\n".join(
    item["urdu"]
    for item in urdu_segments
)


try:

    with open(
        OUTPUT_TEXT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            urdu_text
        )

except Exception as error:

    print()
    print(
        "ERROR saving urdu_transcript.txt:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# SAVE SEGMENTS
# ============================================================

output_data = {

    "source":
        "speech_segments.json",

    "language":
        "ur",

    "source_language":
        "en",

    "translator":
        MODEL_NAME,

    "fallback":
        True,

    "segment_count":
        len(
            urdu_segments
        ),

    "segments":
        urdu_segments
}


try:

    with open(
        OUTPUT_SEGMENTS,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=4
        )

except Exception as error:

    print()
    print(
        "ERROR saving urdu_segments.json:"
    )

    print(error)

    raise SystemExit(1)


# ============================================================
# SUCCESS
# ============================================================

print()
print("=" * 70)
print("✓ MODULE 3 FALLBACK COMPLETE")
print("=" * 70)

print()

print(
    "Translated segments:",
    len(
        urdu_segments
    )
)

print()

print(
    "Urdu transcript:"
)

print(
    OUTPUT_TEXT
)

print()

print(
    "Urdu segment information:"
)

print(
    OUTPUT_SEGMENTS
)

print()

print(
    "Fallback translation completed successfully."
)

print()

print("=" * 70)