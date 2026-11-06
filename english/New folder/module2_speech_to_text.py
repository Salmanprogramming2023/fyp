import json
import os

import librosa
import numpy as np
import whisper


# ============================================================
# MODULE 2
# SPEECH -> ENGLISH TEXT + TIMESTAMPS + SPEAKER GENDER
#
# INPUT :  english_audio.wav          (from Module 1)
# OUTPUT:  english_transcript.txt
#          speech_segments.json       (read by Module 3)
#
# How gender is detected
#
#   Pitch alone does not work when two voices overlap in pitch: the same
#   person's voice glides between ~180 Hz and ~300 Hz inside one question,
#   which looks like two different speakers. So this module now uses a
#   trained gender model that listens to the VOICE QUALITY (not only pitch):
#
#     1. the transcript is cut into sentences (punctuation / pauses)
#     2. every sentence is classified from ITS OWN audio only (a short
#        sentence is repeated up to 1.5 s, a long one is cut into 1.5 s
#        windows) by a pretrained model: P(male) / P(female)
#     3. every sentence gets ONE gender, so the dubbed voice never changes
#        in the middle of a sentence
#
#   GENDER_BACKEND = "pitch" keeps the old pitch-only method as a fallback
#   (no download needed, but unreliable when the voices overlap).
#
# Gender is an acoustic estimate, not a guarantee.
#
# Install for the model backend:  python -m pip install transformers
# (torch is already installed together with openai-whisper; the model,
#  about 1.2 GB, is downloaded once on the first run)
# ============================================================


# ============================================================
# FILES
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_FILE = os.path.join(BASE_DIR, "english_audio.wav")
TEXT_OUTPUT = os.path.join(BASE_DIR, "english_transcript.txt")
SEGMENT_OUTPUT = os.path.join(BASE_DIR, "speech_segments.json")


# ============================================================
# SETTINGS
# ============================================================

MODEL_NAME = "small"
SAMPLE_RATE = 16000

# Sentence building
MAX_SENTENCE_SECONDS = 12.0
PAUSE_THRESHOLD = 0.80
MERGE_MAX_GAP = 0.50          # tiny fragments are merged only across gaps up to this

# Pitch tracking
PITCH_MIN = 65.0
PITCH_MAX = 400.0
HOP_LENGTH = 256
MIN_VOICED_FRAMES = 3         # a word needs this many voiced frames to get a pitch

# Gender backend
GENDER_BACKEND = "model"      # "model" (recommended) or "pitch" (fallback)
# The first model that loads is used.
GENDER_MODELS = [
    "alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech",
    "prithivMLmods/Common-Voice-Gender-Detection",
]
# The pitch method is NOT reliable for videos where the voices overlap in pitch.
# If the gender model cannot be loaded, the script stops with an explanation
# instead of quietly producing wrong genders. Set True to accept pitch anyway.
ALLOW_PITCH_FALLBACK = False
ACTIVE_MODEL = ""
WINDOW_SECONDS = 1.5          # length of the audio clip given to the model
WINDOW_HOP = 0.75             # window step inside a long sentence
BATCH_SIZE = 8
SWITCH_PENALTY = 4.0          # inside a long sentence: higher = fewer speaker switches
MODEL_UNCERTAIN_BELOW = 0.60  # a sentence with lower average confidence is flagged uncertain
PITCH_UNCERTAIN_BELOW = 0.25

# One sentence = one voice. A sentence is only cut in two when BOTH halves are
# at least this long (a real change of speaker inside a long sentence).
MIN_TURN_SPLIT_SECONDS = 3.0

# Voice groups / gender (pitch backend)
GENDER_SPLIT_HZ = 170.0       # a voice group centred below this is male, above is female
MIN_VOICE_RATIO = 1.30        # two groups must differ by at least 30 % to count as two voices
MIN_GROUP_SHARE = 0.08        # each group needs at least 8 % of the words
MIN_TURN_SECONDS = 0.30       # shorter, weakly-measured switches are treated as pitch glitches

# Two voice groups that are far apart but both above GENDER_SPLIT_HZ (for example
# an animated man at 200 Hz and a woman at 290 Hz) are read as man + woman.
# Set to False if your video has two speakers of the same gender.
ASSUME_MAN_AND_WOMAN = True
TWO_VOICE_GENDER_RATIO = 1.35
LOW_VOICE_MAX_HZ = 215.0

SENTENCE_END = (".", "?", "!", "。", "？", "！")


# ============================================================
# HELPERS
# ============================================================

def collect_words(raw_segments):

    words = []

    for segment in raw_segments:

        segment_words = segment.get("words") or []

        if not segment_words:

            text = str(segment.get("text", "")).strip()

            if text:

                start = float(segment.get("start", 0))
                end = float(segment.get("end", start))

                words.append({"word": text, "start": start, "end": end})

            continue

        for item in segment_words:

            text = str(item.get("word", "")).strip()

            if not text:
                continue

            start = float(item.get("start", segment.get("start", 0)))
            end = float(item.get("end", segment.get("end", start)))

            words.append({"word": text, "start": start, "end": end})

    return words


def measure_word_pitch(audio, words):
    """Track pitch once over the whole audio, then take the median per word."""

    peak = float(np.max(np.abs(audio)))

    if peak <= 0:
        for word in words:
            word["pitch"] = None
        return

    f0, voiced_flag, _ = librosa.pyin(
        audio / peak,
        fmin=PITCH_MIN,
        fmax=PITCH_MAX,
        sr=SAMPLE_RATE,
        frame_length=2048,
        hop_length=HOP_LENGTH
    )

    times = np.arange(len(f0)) * HOP_LENGTH / SAMPLE_RATE
    good = np.isfinite(f0) & np.asarray(voiced_flag, dtype=bool)

    for word in words:

        inside = good & (times >= word["start"]) & (times <= word["end"])
        values = f0[inside]

        word["pitch"] = (
            float(np.median(values))
            if len(values) >= MIN_VOICED_FRAMES
            else None
        )


def find_voice_groups(words):
    """Split the word pitches into a low and a high voice group.

    Returns a list of groups: {"center": Hz, "gender": ..., "share": ...}
    One group  -> one speaker (or several of the same kind).
    Two groups -> two clearly different voices.
    """

    pitches = np.array([w["pitch"] for w in words if w["pitch"]])

    if len(pitches) == 0:
        return []

    x = np.log(pitches)

    if len(pitches) >= 6:

        centers = np.array([np.percentile(x, 25), np.percentile(x, 75)])

        for _ in range(100):

            labels = np.argmin(np.abs(x[:, None] - centers[None, :]), axis=1)

            updated = np.array([
                x[labels == k].mean() if np.any(labels == k) else centers[k]
                for k in range(2)
            ])

            if np.allclose(updated, centers):
                break

            centers = updated

        low, high = np.exp(centers)
        shares = [float(np.mean(labels == 0)), float(np.mean(labels == 1))]

        if high / low >= MIN_VOICE_RATIO and min(shares) >= MIN_GROUP_SHARE:

            groups = [
                {
                    "center": float(c),
                    "share": s,
                    "gender": "male" if c < GENDER_SPLIT_HZ else "female"
                }
                for c, s in zip((low, high), shares)
            ]

            if (
                ASSUME_MAN_AND_WOMAN
                and groups[0]["gender"] == groups[1]["gender"]
                and high / low >= TWO_VOICE_GENDER_RATIO
                and low < LOW_VOICE_MAX_HZ
            ):

                groups[0]["gender"] = "male"
                groups[1]["gender"] = "female"

            return groups

    center = float(np.median(pitches))

    return [{
        "center": center,
        "share": 1.0,
        "gender": "male" if center < GENDER_SPLIT_HZ else "female"
    }]


def label_words(words, groups):
    """Give every word a gender and a confidence (0..1)."""

    for word in words:

        pitch = word["pitch"]

        if pitch is None or not groups:

            word["gender"] = None
            word["confidence"] = 0.0

            continue

        if len(groups) == 1:

            word["gender"] = groups[0]["gender"]
            word["confidence"] = 1.0

            continue

        distances = [abs(np.log(pitch) - np.log(g["center"])) for g in groups]
        own = int(np.argmin(distances))
        other = 1 - own

        word["gender"] = groups[own]["gender"]
        word["confidence"] = float(
            (distances[other] - distances[own])
            / (distances[other] + distances[own] + 1e-9)
        )

    # Words without a measurable pitch (whispered, very short, noisy) copy a
    # neighbour: the previous word inside a sentence, but the NEXT measured
    # word when the previous word ended a sentence (a new sentence usually
    # means a new speaker).
    known = [i for i, w in enumerate(words) if w["gender"]]

    if not known:

        for word in words:
            word["gender"] = "male"

        return

    for i, word in enumerate(words):

        if word["gender"]:
            continue

        previous_ended = i > 0 and words[i - 1]["word"].endswith(SENTENCE_END)

        if i > 0 and not previous_ended:

            word["gender"] = words[i - 1]["gender"]

        else:

            later = [j for j in known if j > i]

            if later:
                word["gender"] = words[later[0]]["gender"]
            elif i > 0:
                word["gender"] = words[i - 1]["gender"]
            else:
                word["gender"] = words[known[0]]["gender"]


def remove_pitch_glitches(words):
    """A very short, weakly-measured switch between two words of the
    same gender is a tracking error, not a new speaker."""

    changed = True

    while changed:

        changed = False

        runs = []

        for i, word in enumerate(words):

            if runs and runs[-1]["gender"] == word["gender"]:
                runs[-1]["end"] = i
            else:
                runs.append({"gender": word["gender"], "start": i, "end": i})

        for k in range(1, len(runs) - 1):

            run = runs[k]

            if runs[k - 1]["gender"] != runs[k + 1]["gender"]:
                continue

            members = words[run["start"]: run["end"] + 1]
            duration = members[-1]["end"] - members[0]["start"]
            confidence = float(np.mean([m["confidence"] for m in members]))

            if duration < MIN_TURN_SECONDS and confidence < 0.5:

                for m in members:
                    m["gender"] = runs[k - 1]["gender"]

                changed = True

                break


def load_gender_model():

    global ACTIVE_MODEL

    import torch
    from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

    problems = []

    for name in GENDER_MODELS:

        try:

            extractor = AutoFeatureExtractor.from_pretrained(name)
            model = AutoModelForAudioClassification.from_pretrained(name)

            male_ids, female_ids = [], []

            for index, label in model.config.id2label.items():

                text = str(label).lower()

                if text.startswith("female") or text in ("f", "woman"):
                    female_ids.append(int(index))
                elif text.startswith("male") or text in ("m", "man"):
                    male_ids.append(int(index))

            if not male_ids or not female_ids:

                raise RuntimeError(
                    "cannot tell which output is male/female: "
                    f"{model.config.id2label}"
                )

            model.eval()

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)

            ACTIVE_MODEL = name

            return torch, extractor, model, device, male_ids, female_ids

        except Exception as error:

            problems.append(f"{name}: {type(error).__name__}: {error}")

    raise RuntimeError("\n".join(problems))


def smooth_windows(p_male):
    """Viterbi smoothing: pick the male/female path that fits the model
    probabilities but pays SWITCH_PENALTY for every change of speaker."""

    p = np.clip(np.asarray(p_male, dtype=float), 1e-3, 1 - 1e-3)
    logp = np.log(np.stack([p, 1 - p], axis=1))      # column 0 = male, 1 = female

    n = len(logp)
    score = np.zeros((n, 2))
    back = np.zeros((n, 2), dtype=int)
    score[0] = logp[0]

    for i in range(1, n):

        for s in (0, 1):

            stay = score[i - 1][s]
            switch = score[i - 1][1 - s] - SWITCH_PENALTY

            if stay >= switch:
                score[i][s] = stay + logp[i][s]
                back[i][s] = s
            else:
                score[i][s] = switch + logp[i][s]
                back[i][s] = 1 - s

    path = [int(np.argmax(score[-1]))]

    for i in range(n - 1, 0, -1):
        path.append(int(back[i][path[-1]]))

    return path[::-1]


def model_sentence_genders(audio, sentences):
    """Give every word a gender, classifying each SENTENCE from its own audio only.

    Working per sentence matters: in a fast conversation the turns are often
    shorter than the 1.5 s window, and a window laid over the whole recording
    mixes a short line with the voices around it.
    """

    torch, extractor, model, device, male_ids, female_ids = load_gender_model()

    window = int(WINDOW_SECONDS * SAMPLE_RATE)

    def cut(t0):

        a = max(int(t0 * SAMPLE_RATE), 0)
        clip = audio[a: a + window]

        if len(clip) < window:
            clip = np.pad(clip, (0, window - len(clip)))

        return clip.astype(np.float32)

    jobs = []     # (sentence index, window centre time, audio clip)

    for index, words in enumerate(sentences):

        first, last = words[0]["start"], words[-1]["end"]

        if last - first <= WINDOW_SECONDS:

            # short sentence: repeat ITS OWN audio up to the window length
            piece = audio[int(first * SAMPLE_RATE): int(last * SAMPLE_RATE)]

            if len(piece) < 400:
                continue

            jobs.append((index, (first + last) / 2, np.resize(piece, window).astype(np.float32)))

        else:

            starts = list(np.arange(first, last - WINDOW_SECONDS, WINDOW_HOP))
            starts.append(last - WINDOW_SECONDS)

            for t0 in starts:
                jobs.append((index, t0 + WINDOW_SECONDS / 2, cut(t0)))

    if not jobs:
        raise RuntimeError("No speech to classify.")

    print(f"Classifying {len(jobs)} clips with {ACTIVE_MODEL} on {device} ...")

    p_male = []

    for i in range(0, len(jobs), BATCH_SIZE):

        inputs = extractor(
            [job[2] for job in jobs[i: i + BATCH_SIZE]],
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt",
            padding=True
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = model(**inputs).logits

        probs = torch.softmax(logits, dim=-1).cpu().numpy()

        for row in probs:

            male = float(row[male_ids].sum())
            female = float(row[female_ids].sum())

            p_male.append(male / (male + female + 1e-9))

        print(f"  {min(i + BATCH_SIZE, len(jobs))}/{len(jobs)}")

    per_sentence = {}

    for (index, centre, _), p in zip(jobs, p_male):
        per_sentence.setdefault(index, []).append((centre, p))

    for index, words in enumerate(sentences):

        if index not in per_sentence:

            for word in words:
                word["gender"] = "male"
                word["confidence"] = 0.0
                word["pitch"] = None
                word["measured"] = False

            continue

        entries = sorted(per_sentence[index])
        centres = np.array([c for c, _ in entries])
        probs = [p for _, p in entries]

        path = smooth_windows(probs)

        for word in words:

            middle = (word["start"] + word["end"]) / 2
            k = int(np.argmin(np.abs(centres - middle)))

            gender = "male" if path[k] == 0 else "female"

            word["gender"] = gender
            word["confidence"] = float(probs[k] if gender == "male" else 1 - probs[k])
            word["pitch"] = None
            word["measured"] = True


def split_long_turns(sentence_words):
    """Give a sentence ONE gender. Only if it really contains two long stretches
    of different speakers (each >= MIN_TURN_SPLIT_SECONDS) is it cut in two;
    shorter stretches are absorbed by the neighbouring voice."""

    runs = []

    for word in sentence_words:

        if runs and runs[-1][0] == word["gender"]:
            runs[-1][1].append(word)
        else:
            runs.append([word["gender"], [word]])

    def length(run):
        return run[1][-1]["end"] - run[1][0]["start"]

    while len(runs) > 1:

        shortest = min(range(len(runs)), key=lambda k: length(runs[k]))

        if length(runs[shortest]) >= MIN_TURN_SPLIT_SECONDS:
            break

        if shortest == 0:
            neighbour = 1
        elif shortest == len(runs) - 1:
            neighbour = shortest - 1
        else:
            neighbour = (
                shortest - 1
                if length(runs[shortest - 1]) >= length(runs[shortest + 1])
                else shortest + 1
            )

        if neighbour < shortest:
            runs[neighbour][1].extend(runs[shortest][1])
        else:
            runs[neighbour][1][:0] = runs[shortest][1]

        del runs[shortest]

        k = 0

        while k < len(runs) - 1:

            if runs[k][0] == runs[k + 1][0]:
                runs[k][1].extend(runs[k + 1][1])
                del runs[k + 1]
            else:
                k += 1

    parts = []

    for gender, members in runs:

        for word in members:
            word["gender"] = gender

        parts.append(members)

    return parts


def build_sentence(current_words, uncertain_below):

    text = " ".join(w["word"] for w in current_words).strip()

    weights = {"male": 0.0, "female": 0.0}
    measured = 0
    pitches = []
    confidences = []

    for w in current_words:

        weight = max(w["end"] - w["start"], 0.05)
        weights[w["gender"]] += weight

        if w.get("measured"):
            measured += 1
            confidences.append(w["confidence"])

        if w["pitch"] is not None:
            pitches.append(w["pitch"])

    gender = "female" if weights["female"] > weights["male"] else "male"
    measured_share = measured / len(current_words)
    confidence = float(np.mean(confidences)) if confidences else 0.0

    return {
        "start": round(current_words[0]["start"], 3),
        "end": round(current_words[-1]["end"], 3),
        "text": text,
        "gender": gender,
        "confidence": round(confidence, 3),
        "pitch": round(float(np.median(pitches)), 1) if pitches else None,
        "gender_uncertain": bool(measured_share < 0.3 or confidence < uncertain_below)
    }


def split_into_sentences(words):
    """Group the words into sentences (punctuation, pauses, maximum length)."""

    sentences = []
    current = []

    for word in words:

        if current:

            previous = current[-1]

            pause = word["start"] - previous["end"]
            duration = word["end"] - current[0]["start"]

            if (
                previous["word"].endswith(SENTENCE_END)
                or pause >= PAUSE_THRESHOLD
                or duration >= MAX_SENTENCE_SECONDS
            ):

                sentences.append(current)
                current = []

        current.append(word)

    if current:
        sentences.append(current)

    return sentences


def finalize_sentences(sentences, uncertain_below):
    """One voice per sentence (see split_long_turns), then tidy tiny fragments."""

    grouped = []

    for sentence in sentences:

        for part in split_long_turns(sentence):
            grouped.append(build_sentence(part, uncertain_below))

    # Merge tiny fragments into the previous sentence - but only when the
    # same person is speaking and there is no real gap.
    cleaned = []

    for item in grouped:

        duration = item["end"] - item["start"]
        word_count = len(item["text"].split())

        if cleaned:

            previous = cleaned[-1]

            mergeable = (
                word_count <= 3
                and duration <= 1.3
                and item["start"] - previous["end"] <= MERGE_MAX_GAP
                and item["gender"] == previous["gender"]
            )

            if mergeable:

                previous["text"] += " " + item["text"]
                previous["end"] = item["end"]

                continue

        cleaned.append(item)

    return cleaned


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MODULE 2 - SPEECH TO TEXT + GENDER (word level)")
    print("=" * 70)

    if not os.path.exists(AUDIO_FILE):

        print()
        print("ERROR: Audio file not found.")
        print(AUDIO_FILE)

        return 1

    audio, _ = librosa.load(AUDIO_FILE, sr=SAMPLE_RATE, mono=True)
    audio = audio.astype(np.float32)

    print()
    print(f"Audio: {len(audio) / SAMPLE_RATE:.1f} seconds")
    print(f"Loading Whisper model '{MODEL_NAME}' ...")

    model = whisper.load_model(MODEL_NAME)

    print("Transcribing (word timestamps) ...")

    result = model.transcribe(
        # the audio we already loaded, so Whisper does not need ffmpeg here
        audio,
        language="en",
        task="transcribe",
        fp16=False,
        verbose=False,
        condition_on_previous_text=False,
        temperature=0,
        beam_size=5,
        compression_ratio_threshold=2.4,
        logprob_threshold=-1.0,
        no_speech_threshold=0.6,
        word_timestamps=True
    )

    words = collect_words(result.get("segments", []))

    if not words:

        print()
        print("ERROR: No timestamped words found.")

        return 1

    print("Words:", len(words))

    sentence_words = split_into_sentences(words)

    print("Sentences:", len(sentence_words))

    backend = GENDER_BACKEND
    groups = []

    if backend == "model":

        try:

            model_sentence_genders(audio, sentence_words)

        except Exception as error:

            print()
            print("=" * 70)
            print("THE GENDER MODEL COULD NOT BE LOADED")
            print("=" * 70)
            print(error)
            print()
            print("Things to check:")
            print("  1. python -m pip install transformers")
            print("  2. internet access for the first run (the model is downloaded)")
            print("  3. run the one-line test from the instructions and read its error")

            if not ALLOW_PITCH_FALLBACK:

                print()
                print("Stopping, because the pitch method gives wrong genders when the")
                print("voices overlap in pitch. (Set ALLOW_PITCH_FALLBACK = True to use it anyway.)")

                return 1

            print()
            print("WARNING: using the pitch method (less reliable).")

            backend = "pitch"

    if backend == "pitch":

        print("Measuring pitch of every word (this can take a minute) ...")

        measure_word_pitch(audio, words)

        for word in words:
            word["measured"] = word["pitch"] is not None

        groups = find_voice_groups(words)

        print()
        print("Voice groups found:")

        for g in groups:
            print(f"  {g['gender']:6s} voice around {g['center']:.0f} Hz "
                  f"({g['share'] * 100:.0f}% of words)")

        label_words(words, groups)

        if len(groups) == 2 and len({g["gender"] for g in groups}) == 2:
            remove_pitch_glitches(words)

    print()
    print("Gender method used:", f"trained model ({ACTIVE_MODEL})" if backend == "model" else "PITCH (fallback)")

    uncertain_below = (
        MODEL_UNCERTAIN_BELOW if backend == "model" else PITCH_UNCERTAIN_BELOW
    )

    segments_raw = finalize_sentences(sentence_words, uncertain_below)

    final_segments = []

    for index, item in enumerate(segments_raw, start=1):

        final_segments.append({
            "id": index,
            "start": item["start"],
            "end": item["end"],
            "duration": round(item["end"] - item["start"], 3),
            "text": item["text"],
            "text_en": item["text"],
            "gender": item["gender"],
            "gender_uncertain": item["gender_uncertain"],
            "confidence": item["confidence"],
            "pitch": item["pitch"]
        })

    print()
    print("=" * 70)
    print("SEGMENTS")
    print("=" * 70)

    for s in final_segments:
        mark = "?" if s["gender_uncertain"] else " "
        print(f"#{s['id']:03d} [{s['start']:7.2f}-{s['end']:7.2f}] "
              f"{s['gender']:6s} {s['confidence']:.2f}{mark} {s['text'][:60]}")

    with open(TEXT_OUTPUT, "w", encoding="utf-8") as file:
        file.write("\n".join(s["text"] for s in final_segments))

    all_pitches = [w["pitch"] for w in words if w["pitch"]]
    male_count = sum(1 for s in final_segments if s["gender"] == "male")
    female_count = len(final_segments) - male_count

    genders_in_words = {w["gender"] for w in words}

    recording_gender = (
        next(iter(genders_in_words)) if len(genders_in_words) == 1 else "mixed"
    )

    output = {
        "audio": "english_audio.wav",
        "language": "en",
        "model": MODEL_NAME,
        "gender_method": (
            f"Trained model {ACTIVE_MODEL} on each sentence's own audio, one gender per sentence"
            if backend == "model"
            else "Word-level pitch, adaptive voice groups, one gender per sentence"
        ),
        "gender_backend": backend,
        "recording_gender": recording_gender,
        "multi_speaker_detected": recording_gender == "mixed",
        "voice_groups": [
            {
                "gender": g["gender"],
                "center_hz": round(g["center"], 1),
                "share_of_words": round(g["share"], 3)
            }
            for g in groups
        ],
        "global_median_pitch": round(float(np.median(all_pitches)), 2) if all_pitches else 0.0,
        "segment_count": len(final_segments),
        "segments": final_segments
    }

    with open(SEGMENT_OUTPUT, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=4)

    print()
    print("=" * 70)
    print("MODULE 2 COMPLETE")
    print("=" * 70)
    print("Segments:", len(final_segments))
    print("Male segments:", male_count)
    print("Female segments:", female_count)
    print("Recording:", recording_gender)
    print("Saved:", SEGMENT_OUTPUT)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())