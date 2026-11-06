"""
Module 5: Build the dubbed Urdu audio track (NORMALIZED speed)
---------------------------------------------------------------
Input : output/segments_tts.json   (from module 4)
Output: output/urdu_dubbed_audio.wav   <- point module 6 at this file
        output/dub_schedule.json       (where every clip was placed, for checking)

Why the voice used to change speed
  Stretching every clip to exactly fill its slot slows short clips down and
  rushes long ones. Here the speed is kept natural:

  1. A clip is NEVER slowed down. If it is shorter than its slot, it plays at
     natural speed and silence fills the rest.
  2. A clip that does not fit may start up to LEAD_IN seconds early, if the
     pause before it is free.
  3. If it still does not fit, it is sped up slightly (at most
     MAX_EXTRA_SPEEDUP, e.g. 1.12 = 12%).
  4. If it STILL does not fit, it runs into the next pause and the following
     clips start a little later. Clips never overlap.

Needs ffmpeg on PATH (already required by module 4) and numpy.
"""
import json
import os
import subprocess
import wave

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_JSON = os.path.join(BASE_DIR, "output", "segments_tts.json")
OUTPUT_AUDIO = os.path.join(BASE_DIR, "output", "urdu_dubbed_audio.wav")
SCHEDULE_JSON = os.path.join(BASE_DIR, "output", "dub_schedule.json")
WORK_DIR = os.path.join(BASE_DIR, "output", "tts_final")

SAMPLE_RATE = 24000        # edge-tts native rate
LEAD_IN = 0.30             # seconds a clip may start before its original time
MIN_GAP = 0.12             # minimum silence between two clips (seconds)
MAX_EXTRA_SPEEDUP = 1.12   # largest extra speed-up for a clip that does not fit
TAIL = 0.50                # silence added after the last clip (seconds)


def prepare_clip(src, dst, factor):
    """Convert to mono/24 kHz wav, speeding up by `factor` (1.0 = untouched)."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-ar", str(SAMPLE_RATE), "-ac", "1"]
    if abs(factor - 1.0) > 0.005:
        cmd += ["-filter:a", f"atempo={factor:.4f}"]
    cmd.append(dst)
    subprocess.run(cmd, check=True)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == SAMPLE_RATE
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def run(input_json=INPUT_JSON, output_audio=OUTPUT_AUDIO):
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"{input_json} not found (run module 4 first)")
    with open(input_json, encoding="utf-8") as f:
        data = json.load(f)
    segments = data["segments"] if isinstance(data, dict) else data
    segments = sorted(segments, key=lambda s: s["start"])

    os.makedirs(WORK_DIR, exist_ok=True)

    placed = []      # (start_sample, samples)
    schedule = []
    cursor = 0.0     # earliest time the next clip may start

    print(f"[Module 5] Placing {len(segments)} clips (no slowing, gentle speed-up only) ...")
    for i, seg in enumerate(segments):
        dur = float(seg["tts_duration"])
        next_start = segments[i + 1]["start"] if i + 1 < len(segments) else None
        deadline = next_start - MIN_GAP if next_start is not None else None

        start = max(seg["start"], cursor)
        factor = 1.0

        if deadline is not None and start + dur > deadline:
            # 1) borrow the free pause before this clip
            early = max(cursor, seg["start"] - LEAD_IN)
            start = min(start, early)
            # 2) gentle speed-up, capped
            if start + dur > deadline:
                needed = dur / max(deadline - start, 0.1)
                factor = min(needed, MAX_EXTRA_SPEEDUP)

        clip_path = os.path.join(WORK_DIR, f"clip_{seg['id']:04d}.wav")
        prepare_clip(seg["audio_path"], clip_path, factor)
        samples = read_wav(clip_path)
        real_dur = len(samples) / SAMPLE_RATE

        placed.append((int(round(start * SAMPLE_RATE)), samples))
        schedule.append({
            "id": seg["id"],
            "original_start": round(seg["start"], 3),
            "placed_start": round(start, 3),
            "delay": round(start - seg["start"], 3),
            "speedup": round(factor, 3),
            "duration": round(real_dur, 3),
            "ends_before_next": deadline is None or start + real_dur <= deadline + 0.01,
        })
        cursor = start + real_dur + MIN_GAP

    total_samples = max(s + len(x) for s, x in placed) + int(TAIL * SAMPLE_RATE)
    mix = np.zeros(total_samples, dtype=np.int32)
    for start_sample, samples in placed:
        mix[start_sample:start_sample + len(samples)] += samples

    mix = np.clip(mix, -32768, 32767).astype(np.int16)
    os.makedirs(os.path.dirname(output_audio), exist_ok=True)
    with wave.open(output_audio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(mix.tobytes())

    with open(SCHEDULE_JSON, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)

    sped = [s["speedup"] for s in schedule if s["speedup"] > 1.005]
    late = [s["delay"] for s in schedule if s["delay"] > 0.05]
    print(f"[Module 5] Clips sped up: {len(sped)}"
          + (f" (max x{max(sped):.2f})" if sped else ""))
    print(f"[Module 5] Clips starting late: {len(late)}"
          + (f" (max {max(late):.2f}s)" if late else ""))
    print(f"[Module 5] Audio length: {total_samples / SAMPLE_RATE:.2f}s -> {output_audio}")
    return output_audio


if __name__ == "__main__":
    run()