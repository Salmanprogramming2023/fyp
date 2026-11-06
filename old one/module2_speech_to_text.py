import os
import json
import statistics

import numpy as np
import librosa
import whisper


# ============================================================
# MODULE 2
# SPEECH -> ENGLISH TEXT + TIMESTAMP + ADAPTIVE GENDER
#
# IMPORTANT:
# Gender is an acoustic estimate.
# It is NOT guaranteed biological gender identification.
#
# Main improvements:
#   1. Whisper word timestamps
#   2. Better sentence grouping
#   3. Robust pitch statistics
#   4. Conservative male/female thresholds
#   5. Confidence score
#   6. Recording-level gender consistency
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

AUDIO_FILE = os.path.join(
    BASE_DIR,
    "english_audio.wav"
)

TEXT_OUTPUT = os.path.join(
    BASE_DIR,
    "english_transcript.txt"
)

SEGMENT_OUTPUT = os.path.join(
    BASE_DIR,
    "speech_segments.json"
)


# ============================================================
# WHISPER
# ============================================================

MODEL_NAME = "small"

SAMPLE_RATE = 16000


# ============================================================
# SENTENCE GROUPING
# ============================================================

MAX_SENTENCE_SECONDS = 12.0

PAUSE_THRESHOLD = 0.80

# A tiny fragment is only glued to the previous sentence if the gap
# between them is at most this many seconds (keeps dubbing in sync).
MERGE_MAX_GAP = 0.50


# ============================================================
# PITCH ANALYSIS
# ============================================================

PITCH_MIN = 65.0

PITCH_MAX = 350.0

# More conservative than the old 155 / 175 thresholds.
#
# <= 145 strongly supports male
# >= 190 strongly supports female
# middle area becomes uncertain
#

MALE_STRONG_MAX = 145.0

FEMALE_STRONG_MIN = 190.0

MALE_PROBABLE_MAX = 155.0

FEMALE_PROBABLE_MIN = 180.0


# ============================================================
# CONFIDENCE SETTINGS
# ============================================================

MIN_VOICED_RATIO = 0.25

MIN_CONFIDENCE_FOR_GENDER = 0.55

STRONG_CONFIDENCE = 0.75

# If at least this many sentences clearly show the OPPOSITE gender of the
# recording-level result, the video has several speakers and every
# sentence keeps its own estimate. One lone contradiction is treated as
# a pitch-detection glitch and smoothed away.
MIN_OPPOSITE_SENTENCES = 2

# Last-resort split used only when nothing else decides the gender.
FALLBACK_PITCH_SPLIT = 165.0


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 2 - SPEECH -> TEXT + ADAPTIVE GENDER")
print("=" * 70)

print()

print("Audio:")
print(AUDIO_FILE)

print()

print("Transcript:")
print(TEXT_OUTPUT)

print()

print("Gender/timestamp data:")
print(SEGMENT_OUTPUT)


# ============================================================
# CHECK AUDIO
# ============================================================

if not os.path.exists(
    AUDIO_FILE
):

    print()
    print("ERROR: Audio file not found.")
    print(AUDIO_FILE)

    raise SystemExit(1)


# ============================================================
# LOAD AUDIO
# ============================================================

print()
print("=" * 70)
print("LOADING AUDIO")
print("=" * 70)


try:

    audio, sample_rate = librosa.load(
        AUDIO_FILE,
        sr=SAMPLE_RATE,
        mono=True
    )

except Exception as error:

    print()
    print("ERROR loading audio:")
    print(error)

    raise SystemExit(1)


audio = audio.astype(
    np.float32
)


audio_duration = (
    len(audio)
    /
    sample_rate
)


print()
print(
    "Sample rate:",
    sample_rate
)

print(
    "Duration:",
    round(
        audio_duration,
        2
    ),
    "seconds"
)


# ============================================================
# LOAD WHISPER
# ============================================================

print()
print("=" * 70)
print("LOADING WHISPER")
print("=" * 70)

print()

print(
    "Model:",
    MODEL_NAME
)

print(
    "Please wait..."
)


try:

    model = whisper.load_model(
        MODEL_NAME
    )

except Exception as error:

    print()
    print(
        "ERROR loading Whisper:"
    )

    print(error)

    raise SystemExit(1)


print()
print("✓ Whisper loaded.")


# ============================================================
# WHISPER TRANSCRIPTION
# ============================================================

print()
print("=" * 70)
print("TRANSCRIBING AUDIO")
print("=" * 70)

print()

print(
    "Using word timestamps..."
)


try:

    result = model.transcribe(

        # Pass the audio we already loaded (16 kHz float32) so Whisper
        # does not need ffmpeg on PATH to open the file again.
        audio,

        language="en",

        task="transcribe",

        fp16=False,

        verbose=False,

        # Avoid overly strong previous-text propagation.
        condition_on_previous_text=False,

        # Deterministic decoding.
        temperature=0,

        # Better decoding search.
        beam_size=5,

        # Quality controls.
        compression_ratio_threshold=2.4,

        logprob_threshold=-1.0,

        no_speech_threshold=0.6,

        # IMPORTANT.
        word_timestamps=True
    )

except Exception as error:

    print()
    print(
        "ERROR during Whisper transcription:"
    )

    print(error)

    raise SystemExit(1)


raw_segments = result.get(
    "segments",
    []
)


if not raw_segments:

    print()
    print(
        "ERROR: Whisper returned no segments."
    )

    raise SystemExit(1)


full_text = result.get(
    "text",
    ""
).strip()


print()
print(
    "Raw Whisper segments:",
    len(raw_segments)
)


# ============================================================
# COLLECT WORDS
# ============================================================

words = []


for segment in raw_segments:

    segment_words = segment.get(
        "words",
        []
    )


    if segment_words:

        for word in segment_words:

            text = str(
                word.get(
                    "word",
                    ""
                )
            ).strip()


            if not text:
                continue


            start = float(
                word.get(
                    "start",
                    segment.get(
                        "start",
                        0
                    )
                )
            )


            end = float(
                word.get(
                    "end",
                    segment.get(
                        "end",
                        start
                    )
                )
            )


            words.append(
                {
                    "word": text,
                    "start": start,
                    "end": end
                }
            )

    else:

        text = str(
            segment.get(
                "text",
                ""
            )
        ).strip()


        if not text:
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
                start
            )
        )


        words.append(
            {
                "word": text,
                "start": start,
                "end": end
            }
        )


if not words:

    print()
    print(
        "ERROR: No timestamped words found."
    )

    raise SystemExit(1)


print(
    "Timestamped words:",
    len(words)
)


# ============================================================
# SENTENCE GROUPING
# ============================================================

print()
print("=" * 70)
print("BUILDING SENTENCES")
print("=" * 70)


def finalize_sentence(
    target,
    current_words
):

    if not current_words:
        return


    text = " ".join(
        item["word"]
        for item in current_words
    ).strip()


    if not text:
        return


    target.append(
        {
            "start": round(
                current_words[0]["start"],
                3
            ),

            "end": round(
                current_words[-1]["end"],
                3
            ),

            "text": text
        }
    )


grouped = []

current_words = []


for word in words:

    if not current_words:

        current_words.append(
            word
        )

        continue


    previous = current_words[-1]

    pause = (
        word["start"]
        -
        previous["end"]
    )


    current_duration = (
        word["end"]
        -
        current_words[0]["start"]
    )


    previous_word = previous[
        "word"
    ]


    punctuation_end = (
        previous_word.endswith(
            (
                ".",
                "?",
                "!",
                "。",
                "？",
                "！"
            )
        )
    )


    # --------------------------------------------------------
    # Split rules
    # --------------------------------------------------------

    should_split = False


    # Strong punctuation boundary.

    if punctuation_end:

        should_split = True


    # Long pause.

    elif pause >= PAUSE_THRESHOLD:

        should_split = True


    # Prevent extremely long sentence blocks.

    elif current_duration >= MAX_SENTENCE_SECONDS:

        should_split = True


    # --------------------------------------------------------
    # Split
    # --------------------------------------------------------

    if should_split:

        finalize_sentence(
            grouped,
            current_words
        )

        current_words = [
            word
        ]

    else:

        current_words.append(
            word
        )


# Final sentence.

finalize_sentence(
    grouped,
    current_words
)


# ============================================================
# MERGE SMALL FRAGMENTS
# ============================================================

cleaned = []


for item in grouped:

    text = item[
        "text"
    ].strip()


    duration = (
        item["end"]
        -
        item["start"]
    )


    word_count = len(
        text.split()
    )


    gap_to_previous = (
        item["start"]
        -
        cleaned[-1]["end"]
        if cleaned
        else 0.0
    )


    tiny_fragment = (
        word_count <= 3
        and
        duration <= 1.3
        and
        gap_to_previous <= MERGE_MAX_GAP
    )


    if (
        tiny_fragment
        and
        cleaned
    ):

        cleaned[-1]["text"] = (
            cleaned[-1]["text"]
            +
            " "
            +
            text
        )

        cleaned[-1]["end"] = (
            item["end"]
        )

    else:

        cleaned.append(
            item
        )


print()
print(
    "Final grouped sentences:",
    len(cleaned)
)


# ============================================================
# PITCH HELPERS
# ============================================================

def robust_pitch_values(
    segment_audio
):

    if len(segment_audio) < int(
        sample_rate * 0.25
    ):

        return None, None, 0.0


    # --------------------------------------------------------
    # Normalize only for analysis.
    # --------------------------------------------------------

    peak = float(
        np.max(
            np.abs(
                segment_audio
            )
        )
    )


    if peak <= 0:

        return None, None, 0.0


    segment_audio = (
        segment_audio
        /
        peak
    )


    # --------------------------------------------------------
    # pyin
    # --------------------------------------------------------

    try:

        f0, voiced_flag, voiced_probs = (
            librosa.pyin(

                segment_audio,

                fmin=PITCH_MIN,

                fmax=PITCH_MAX,

                sr=sample_rate,

                frame_length=2048,

                hop_length=256
            )
        )

    except Exception:

        return None, None, 0.0


    # --------------------------------------------------------
    # Keep finite values.
    # --------------------------------------------------------

    valid = f0[
        np.isfinite(f0)
    ]


    valid = valid[
        (valid >= PITCH_MIN)
        &
        (valid <= PITCH_MAX)
    ]


    if len(valid) < 3:

        return None, None, 0.0


    # --------------------------------------------------------
    # Remove extreme outliers.
    # Use middle 10%-90% range.
    # --------------------------------------------------------

    low = np.percentile(
        valid,
        10
    )

    high = np.percentile(
        valid,
        90
    )


    trimmed = valid[
        (valid >= low)
        &
        (valid <= high)
    ]


    if len(trimmed) < 3:

        trimmed = valid


    median_pitch = float(
        np.median(
            trimmed
        )
    )


    mean_pitch = float(
        np.mean(
            trimmed
        )
    )


    voiced_ratio = float(
        np.mean(
            voiced_flag
        )
    )


    return (
        median_pitch,
        mean_pitch,
        voiced_ratio
    )


# ============================================================
# PITCH -> GENDER
# ============================================================

def classify_gender(
    median_pitch,
    mean_pitch,
    voiced_ratio
):

    if (
        median_pitch is None
        or
        mean_pitch is None
    ):

        return (
            "unknown",
            0.0
        )


    if voiced_ratio < MIN_VOICED_RATIO:

        return (
            "unknown",
            0.0
        )


    # ========================================================
    # STRONG MALE
    # ========================================================

    if median_pitch <= MALE_STRONG_MAX:

        distance = (
            MALE_STRONG_MAX
            -
            median_pitch
        )


        confidence = min(
            0.55
            +
            distance / 100.0,
            1.0
        )


        confidence *= (
            0.7
            +
            0.3 * voiced_ratio
        )


        return (
            "male",
            round(
                confidence,
                3
            )
        )


    # ========================================================
    # STRONG FEMALE
    # ========================================================

    if median_pitch >= FEMALE_STRONG_MIN:

        distance = (
            median_pitch
            -
            FEMALE_STRONG_MIN
        )


        confidence = min(
            0.55
            +
            distance / 100.0,
            1.0
        )


        confidence *= (
            0.7
            +
            0.3 * voiced_ratio
        )


        return (
            "female",
            round(
                confidence,
                3
            )
        )


    # ========================================================
    # PROBABLE MALE
    # ========================================================

    if median_pitch <= MALE_PROBABLE_MAX:

        confidence = (
            0.50
            +
            (
                MALE_PROBABLE_MAX
                -
                median_pitch
            )
            /
            100.0
        )


        confidence *= (
            0.7
            +
            0.3 * voiced_ratio
        )


        if confidence >= MIN_CONFIDENCE_FOR_GENDER:

            return (
                "male",
                round(
                    confidence,
                    3
                )
            )


    # ========================================================
    # PROBABLE FEMALE
    # ========================================================

    if median_pitch >= FEMALE_PROBABLE_MIN:

        confidence = (
            0.50
            +
            (
                median_pitch
                -
                FEMALE_PROBABLE_MIN
            )
            /
            100.0
        )


        confidence *= (
            0.7
            +
            0.3 * voiced_ratio
        )


        if confidence >= MIN_CONFIDENCE_FOR_GENDER:

            return (
                "female",
                round(
                    confidence,
                    3
                )
            )


    # ========================================================
    # AMBIGUOUS
    # ========================================================

    return (
        "unknown",
        0.0
    )


# ============================================================
# ANALYZE EACH SENTENCE
# ============================================================

print()
print("=" * 70)
print("ANALYZING VOICE + GENDER")
print("=" * 70)


analysis_results = []


for number, item in enumerate(
    cleaned,
    start=1
):

    start = float(
        item["start"]
    )

    end = float(
        item["end"]
    )


    start_sample = max(
        0,
        int(
            start * sample_rate
        )
    )


    end_sample = min(
        len(audio),
        int(
            end * sample_rate
        )
    )


    segment_audio = audio[
        start_sample:end_sample
    ]


    (
        median_pitch,
        mean_pitch,
        voiced_ratio
    ) = robust_pitch_values(
        segment_audio
    )


    (
        gender,
        confidence
    ) = classify_gender(
        median_pitch,
        mean_pitch,
        voiced_ratio
    )


    analysis_results.append(
        {
            "start":
                start,

            "end":
                end,

            "text":
                item["text"],

            "raw_gender":
                gender,

            "raw_confidence":
                confidence,

            "median_pitch":
                (
                    round(
                        median_pitch,
                        2
                    )
                    if median_pitch is not None
                    else 0.0
                ),

            "mean_pitch":
                (
                    round(
                        mean_pitch,
                        2
                    )
                    if mean_pitch is not None
                    else 0.0
                ),

            "voiced_ratio":
                round(
                    voiced_ratio,
                    3
                )
        }
    )


    print()
    print("-" * 70)

    print(
        f"Sentence {number}/{len(cleaned)}"
    )

    print(
        f"Time: {start:.3f} -> {end:.3f}"
    )

    print(
        "Median pitch:",
        (
            round(
                median_pitch,
                2
            )
            if median_pitch is not None
            else 0.0
        ),
        "Hz"
    )

    print(
        "Gender estimate:",
        gender
    )

    print(
        "Confidence:",
        confidence
    )

    print(
        "English:",
        item["text"]
    )


# ============================================================
# RECORDING-LEVEL PROFILE
# ============================================================
#
# This prevents one unusual sentence from changing the
# overall result.
#
# We use the stronger sentence estimates first.
# ============================================================

male_confident = [
    x
    for x in analysis_results
    if (
        x["raw_gender"] == "male"
        and
        x["raw_confidence"] >= STRONG_CONFIDENCE
    )
]


female_confident = [
    x
    for x in analysis_results
    if (
        x["raw_gender"] == "female"
        and
        x["raw_confidence"] >= STRONG_CONFIDENCE
    )
]


male_pitches = [
    x["median_pitch"]
    for x in male_confident
    if x["median_pitch"] > 0
]


female_pitches = [
    x["median_pitch"]
    for x in female_confident
    if x["median_pitch"] > 0
]


all_pitches = [
    x["median_pitch"]
    for x in analysis_results
    if x["median_pitch"] > 0
]


# ============================================================
# DETERMINE RECORDING PROFILE
# ============================================================

recording_gender = "unknown"

recording_confidence = 0.0


if all_pitches:

    global_median_pitch = float(
        np.median(
            all_pitches
        )
    )


    male_score = 0.0

    female_score = 0.0


    # --------------------------------------------------------
    # Count confident evidence.
    # --------------------------------------------------------

    if male_confident:

        male_score += min(
            len(male_confident) / max(
                1,
                len(analysis_results)
            ),
            1.0
        )


    if female_confident:

        female_score += min(
            len(female_confident) / max(
                1,
                len(analysis_results)
            ),
            1.0
        )


    # --------------------------------------------------------
    # Strong global pitch evidence.
    # --------------------------------------------------------

    if global_median_pitch <= 145:

        male_score += 0.8


    elif global_median_pitch >= 190:

        female_score += 0.8


    elif global_median_pitch <= 155:

        male_score += 0.35


    elif global_median_pitch >= 180:

        female_score += 0.35


    # --------------------------------------------------------
    # Decide only when evidence clearly differs.
    # --------------------------------------------------------

    if (
        male_score > female_score
        and
        male_score >= 0.70
    ):

        recording_gender = "male"

        recording_confidence = min(
            1.0,
            male_score
        )


    elif (
        female_score > male_score
        and
        female_score >= 0.70
    ):

        recording_gender = "female"

        recording_confidence = min(
            1.0,
            female_score
        )


    else:

        recording_gender = "unknown"

        recording_confidence = 0.0


else:

    global_median_pitch = 0.0


# ============================================================
# DISPLAY RECORDING PROFILE
# ============================================================

print()
print("=" * 70)
print("RECORDING-LEVEL VOICE PROFILE")
print("=" * 70)

print()

print(
    "Global median pitch:",
    round(
        global_median_pitch,
        2
    ),
    "Hz"
)

print(
    "Confident male estimates:",
    len(male_confident)
)

print(
    "Confident female estimates:",
    len(female_confident)
)

print(
    "Recording gender:",
    recording_gender
)

print(
    "Recording confidence:",
    round(
        recording_confidence,
        3
    )
)


# ============================================================
# FINAL GENDER ASSIGNMENT
# ============================================================
#
# For single-speaker recordings:
# use recording-level profile to stabilize individual
# sentences.
#
# For mixed/uncertain recordings:
# retain sentence-level estimates.
# ============================================================

final_segments = []


# Sentences that clearly disagree with the recording-level result.
# (Typical voices are ~120 Hz male / ~200 Hz female, which score below
#  STRONG_CONFIDENCE, so the plain sentence-level estimate is used here.)
if recording_gender == "male":
    opposite_gender = "female"
elif recording_gender == "female":
    opposite_gender = "male"
else:
    opposite_gender = None


opposite_sentences = [
    x
    for x in analysis_results
    if (
        opposite_gender is not None
        and
        x["raw_gender"] == opposite_gender
        and
        x["raw_confidence"] >= MIN_CONFIDENCE_FOR_GENDER
    )
]


multi_speaker_detected = (
    len(opposite_sentences)
    >=
    MIN_OPPOSITE_SENTENCES
)


single_profile = (
    recording_gender in ("male", "female")
    and
    not multi_speaker_detected
)


print()
print(
    "Multiple speakers detected:",
    multi_speaker_detected
)


for item in analysis_results:

    sentence_gender = item[
        "raw_gender"
    ]

    sentence_confidence = item[
        "raw_confidence"
    ]


    if single_profile:

        # ----------------------------------------------------
        # Strong contradiction:
        #
        # If a single sentence says the opposite gender,
        # do not automatically switch. Mark it unknown unless
        # it has exceptionally strong evidence.
        # ----------------------------------------------------

        opposite = (
            sentence_gender !=
            recording_gender
            and
            sentence_gender in (
                "male",
                "female"
            )
        )


        if opposite:

            if sentence_confidence >= 0.90:

                # Keep strong sentence evidence.
                final_gender = sentence_gender

            else:

                final_gender = (
                    recording_gender
                )

        else:

            final_gender = (
                recording_gender
            )


        final_confidence = max(
            sentence_confidence,
            recording_confidence * 0.8
        )


    else:

        final_gender = sentence_gender

        final_confidence = sentence_confidence


    # --------------------------------------------------------
    # Final minimum confidence.
    # --------------------------------------------------------

    if (
        final_gender in (
            "male",
            "female"
        )
        and
        final_confidence < MIN_CONFIDENCE_FOR_GENDER
    ):

        final_gender = "unknown"


    final_segments.append(
        {
            "id":
                len(final_segments) + 1,

            "start":
                round(
                    item["start"],
                    3
                ),

            "end":
                round(
                    item["end"],
                    3
                ),

            "duration":
                round(
                    item["end"]
                    -
                    item["start"],
                    3
                ),

            "text":
                item["text"],

            "text_en":
                item["text"],

            "gender":
                final_gender,

            "pitch":
                item["median_pitch"],

            "mean_pitch":
                item["mean_pitch"],

            "voiced_ratio":
                item["voiced_ratio"],

            "confidence":
                round(
                    min(
                        final_confidence,
                        1.0
                    ),
                    3
                )
        }
    )


# ============================================================
# RESOLVE "unknown" GENDERS
# ============================================================
#
# Modules 3 and 4 need a definite male/female value to choose the
# translation grammar and the TTS voice. A sentence that stayed
# "unknown" takes the gender of the nearest confident sentence in
# time. It is flagged with "gender_uncertain": true so you can see
# which ones were filled in.
# ============================================================

if recording_gender in ("male", "female"):

    fallback_gender = recording_gender

elif global_median_pitch >= FALLBACK_PITCH_SPLIT:

    fallback_gender = "female"

else:

    fallback_gender = "male"


known_indexes = [
    index
    for index, seg in enumerate(final_segments)
    if seg["gender"] in ("male", "female")
]


for seg in final_segments:

    if seg["gender"] in ("male", "female"):

        seg["gender_uncertain"] = False

        continue


    seg["gender_uncertain"] = True

    if known_indexes:

        nearest = min(
            known_indexes,
            key=lambda j: abs(
                final_segments[j]["start"]
                -
                seg["start"]
            )
        )

        seg["gender"] = final_segments[nearest]["gender"]

    else:

        seg["gender"] = fallback_gender


# ============================================================
# SAVE TRANSCRIPT
# ============================================================

english_text = "\n".join(
    item["text"]
    for item in final_segments
)


with open(
    TEXT_OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        english_text
    )


# ============================================================
# SAVE JSON
# ============================================================

output = {

    "audio":
        "english_audio.wav",

    "language":
        "en",

    "model":
        MODEL_NAME,

    "gender_method":
        (
            "Acoustic pitch analysis with "
            "recording-level stabilization"
        ),

    "recording_gender":
        recording_gender,

    "recording_confidence":
        round(
            recording_confidence,
            3
        ),

    "multi_speaker_detected":
        multi_speaker_detected,

    "global_median_pitch":
        round(
            global_median_pitch,
            2
        ),

    "segment_count":
        len(
            final_segments
        ),

    "segments":
        final_segments
}


with open(
    SEGMENT_OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output,
        file,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# SUMMARY
# ============================================================

male_count = sum(
    1
    for item in final_segments
    if item["gender"] == "male"
)


female_count = sum(
    1
    for item in final_segments
    if item["gender"] == "female"
)


unknown_count = sum(
    1
    for item in final_segments
    if item["gender_uncertain"]
)


print()
print("=" * 70)
print("FINAL GENDER SUMMARY")
print("=" * 70)

print()

print(
    "Male segments:",
    male_count
)

print(
    "Female segments:",
    female_count
)

print(
    "Uncertain (filled from nearest confident sentence):",
    unknown_count
)

print()

print(
    "Recording-level gender:",
    recording_gender
)

print(
    "Recording-level confidence:",
    round(
        recording_confidence,
        3
    )
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("✓ MODULE 2 COMPLETE")
print("=" * 70)

print()

print(
    "English transcript:"
)

print(
    os.path.abspath(
        TEXT_OUTPUT
    )
)

print()

print(
    "Speech + gender information:"
)

print(
    os.path.abspath(
        SEGMENT_OUTPUT
    )
)

print()

print(
    "Whisper raw segments:",
    len(raw_segments)
)

print(
    "Final grouped sentences:",
    len(final_segments)
)

print()

print(
    "Gender is an acoustic estimate."
)

print(
    "It should not be treated as biological certainty."
)

print()

print("=" * 70)
print("✓ READY FOR MODULE 3")
print("=" * 70)