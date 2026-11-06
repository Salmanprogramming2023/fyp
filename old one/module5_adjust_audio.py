
import os
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


# ============================================================
# MODULE 5
# URDU AUDIO TIMING + VOLUME NORMALIZATION
#
# IMPORTANT:
# Module 5 does not detect gender.
# Module 5 does not generate speech.
# Module 5 uses the audio files created by Module 4.
#
# Every segment keeps its own male/female voice.
# ============================================================


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# INPUT MANIFEST
# ============================================================

MANIFEST_FILE = (
    BASE_DIR /
    "tts_segments.json"
)


# ============================================================
# OUTPUT FILE
# ============================================================

OUTPUT_FILE = (
    BASE_DIR /
    "synchronized_urdu_audio.wav"
)


# ============================================================
# TEMPORARY DIRECTORY
# ============================================================

TEMP_DIR = (
    BASE_DIR /
    "module5_temp_audio"
)


# ============================================================
# AUDIO SETTINGS
# ============================================================

SAMPLE_RATE = 48000
CHANNELS = 2

# Target loudness.
# -16 LUFS is suitable for normal video speech.
TARGET_LUFS = -16

# True means every segment will be fitted into its original
# Whisper timestamp duration.
FIT_AUDIO_TO_SEGMENT = True


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("MODULE 5 - URDU AUDIO TIMING + VOLUME NORMALIZATION")
print("=" * 70)

print()
print("Running file:")
print(Path(__file__).resolve())

print()
print("Manifest:")
print(MANIFEST_FILE)

print()
print("Output:")
print(OUTPUT_FILE)

print()
print("Gender detection: DISABLED")
print("Voice generation: DISABLED")
print("Voice source: Module 4 audio files")
print("Target loudness:", TARGET_LUFS, "LUFS")


# ============================================================
# CHECK FFMPEG
# ============================================================

def check_ffmpeg():

    try:

        result = subprocess.run(
            [
                "ffmpeg",
                "-version"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:

            raise RuntimeError(
                "FFmpeg is not working correctly."
            )

    except FileNotFoundError:

        print()
        print("ERROR: FFmpeg was not found.")

        print()
        print("Install FFmpeg and add it to PATH.")

        raise SystemExit(1)


# ============================================================
# RUN FFMPEG
# ============================================================

def run_ffmpeg(command):

    print()
    print("Running FFmpeg command:")

    print(
        " ".join(
            str(part)
            for part in command
        )
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        print()
        print("FFmpeg ERROR:")
        print(result.stderr)

        raise RuntimeError(
            "FFmpeg command failed."
        )

    return result


# ============================================================
# GET AUDIO DURATION
# ============================================================

def get_audio_duration(audio_file):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_file)
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"Could not read audio duration: {audio_file}"
        )

    try:

        duration = float(
            result.stdout.strip()
        )

    except ValueError:

        raise RuntimeError(
            f"Invalid audio duration: {audio_file}"
        )

    return max(
        0.0,
        duration
    )


# ============================================================
# NORMALIZE AND FIT ONE SEGMENT
# ============================================================

def process_segment_audio(
    input_file,
    output_file,
    target_duration
):

    actual_duration = get_audio_duration(
        input_file
    )

    if actual_duration <= 0:

        raise RuntimeError(
            f"Audio duration is zero: {input_file}"
        )

    if target_duration <= 0:

        raise RuntimeError(
            f"Target duration is invalid: {target_duration}"
        )

    # --------------------------------------------------------
    # SPEED CALCULATION
    # --------------------------------------------------------

    # If generated audio is longer than the original segment,
    # speed up the audio.
    #
    # If generated audio is shorter than the original segment,
    # slow down the audio.
    #
    # atempo supports values from 0.5 to 2.0.
    # For larger differences, multiple filters are used.
    # --------------------------------------------------------

    speed_ratio = (
        actual_duration /
        target_duration
    )

    atempo_filters = []

    remaining_ratio = speed_ratio

    while remaining_ratio > 2.0:

        atempo_filters.append(
            "atempo=2.0"
        )

        remaining_ratio /= 2.0

    while remaining_ratio < 0.5:

        atempo_filters.append(
            "atempo=0.5"
        )

        remaining_ratio /= 0.5

    atempo_filters.append(
        f"atempo={remaining_ratio:.6f}"
    )

    # --------------------------------------------------------
    # FILTER CHAIN
    # --------------------------------------------------------

    filters = []

    # Normalize volume.
    #
    # loudnorm makes loud and quiet segments more consistent.
    filters.append(
        (
            "loudnorm="
            f"I={TARGET_LUFS}:"
            "LRA=7:"
            "TP=-1.5"
        )
    )

    # Adjust speed.
    if FIT_AUDIO_TO_SEGMENT:

        filters.extend(
            atempo_filters
        )

    # Ensure stereo 48 kHz WAV.
    filters.append(
        "aresample=48000"
    )

    filters.append(
        "aformat="
        "sample_fmts=s16:"
        "sample_rates=48000:"
        "channel_layouts=stereo"
    )

    filter_chain = ",".join(
        filters
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        str(input_file),

        "-af",
        filter_chain,

        "-ar",
        str(SAMPLE_RATE),

        "-ac",
        str(CHANNELS),

        "-c:a",
        "pcm_s16le",

        str(output_file)
    ]

    run_ffmpeg(
        command
    )

    # --------------------------------------------------------
    # FINAL EXACT DURATION
    # --------------------------------------------------------
    #
    # The audio may be a few milliseconds different after
    # atempo processing. We trim or pad it exactly.
    # --------------------------------------------------------

    exact_duration_file = (
        output_file.parent /
        f"{output_file.stem}_exact.wav"
    )

    command_exact = [
        "ffmpeg",
        "-y",

        "-i",
        str(output_file),

        "-af",
        (
            "apad,"
            f"atrim=duration={target_duration:.6f},"
            "asetpts=N/SR/TB"
        ),

        "-ar",
        str(SAMPLE_RATE),

        "-ac",
        str(CHANNELS),

        "-c:a",
        "pcm_s16le",

        str(exact_duration_file)
    ]

    run_ffmpeg(
        command_exact
    )

    os.replace(
        exact_duration_file,
        output_file
    )


# ============================================================
# CREATE SILENCE
# ============================================================

def create_silence(
    output_file,
    duration
):

    if duration <= 0:

        return

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        (
            "anullsrc="
            "channel_layout=stereo:"
            "sample_rate=48000"
        ),

        "-t",
        f"{duration:.6f}",

        "-ar",
        str(SAMPLE_RATE),

        "-ac",
        str(CHANNELS),

        "-c:a",
        "pcm_s16le",

        str(output_file)
    ]

    run_ffmpeg(
        command
    )


# ============================================================
# CONCATENATE WAV FILES
# ============================================================

def concatenate_audio(
    files,
    output_file
):

    concat_list = (
        TEMP_DIR /
        "concat_list.txt"
    )

    with open(
        concat_list,
        "w",
        encoding="utf-8"
    ) as file:

        for audio_file in files:

            safe_path = (
                str(audio_file)
                .replace(
                    "'",
                    "'\\''"
                )
            )

            file.write(
                f"file '{safe_path}'\n"
            )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_list),

        "-ar",
        str(SAMPLE_RATE),

        "-ac",
        str(CHANNELS),

        "-c:a",
        "pcm_s16le",

        str(output_file)
    ]

    run_ffmpeg(
        command
    )


# ============================================================
# MAIN
# ============================================================

def main():

    check_ffmpeg()

    # --------------------------------------------------------
    # CHECK MANIFEST
    # --------------------------------------------------------

    if not MANIFEST_FILE.exists():

        print()
        print("ERROR: tts_segments.json not found.")
        print(MANIFEST_FILE)

        print()
        print(
            "Run Module 4 first."
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # LOAD MANIFEST
    # --------------------------------------------------------

    with open(
        MANIFEST_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        manifest = json.load(
            file
        )

    segments = manifest.get(
        "segments",
        []
    )

    if not segments:

        print()
        print("ERROR: No segments found in manifest.")

        raise SystemExit(1)

    print()
    print(
        "Total segments:",
        len(segments)
    )

    # --------------------------------------------------------
    # CLEAN TEMP DIRECTORY
    # --------------------------------------------------------

    if TEMP_DIR.exists():

        print()
        print(
            "Removing old temporary audio..."
        )

        shutil.rmtree(
            TEMP_DIR
        )

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # CREATE PROCESSED FILE LIST
    # --------------------------------------------------------

    processed_files = []

    previous_end = 0.0

    male_count = 0
    female_count = 0
    unknown_count = 0

    # --------------------------------------------------------
    # PROCESS EACH SEGMENT
    # --------------------------------------------------------

    for index, segment in enumerate(
        segments,
        start=1
    ):

        segment_id = segment.get(
            "id",
            index
        )

        gender = str(
            segment.get(
                "gender",
                "unknown"
            )
        ).strip().lower()

        voice = str(
            segment.get(
                "voice",
                "unknown"
            )
        ).strip()

        start = float(
            segment.get(
                "start",
                0.0
            )
        )

        end = float(
            segment.get(
                "end",
                start
            )
        )

        target_duration = max(
            0.0,
            end - start
        )

        audio_file_value = segment.get(
            "audio_file",
            ""
        )

        if not audio_file_value:

            print()
            print(
                f"ERROR: No audio_file for segment {segment_id}"
            )

            raise SystemExit(1)

        input_audio = Path(
            audio_file_value
        )

        # If the manifest contains a relative path,
        # resolve it relative to the project directory.
        if not input_audio.is_absolute():

            input_audio = (
                BASE_DIR /
                input_audio
            )

        if not input_audio.exists():

            print()
            print(
                f"ERROR: Audio file missing for segment {segment_id}"
            )

            print(
                input_audio
            )

            raise SystemExit(1)

        if target_duration <= 0:

            print()
            print(
                f"Skipping segment {segment_id}: invalid duration."
            )

            continue

        # ----------------------------------------------------
        # PRESERVE SILENCE BETWEEN SEGMENTS
        # ----------------------------------------------------

        gap_duration = max(
            0.0,
            start - previous_end
        )

        if gap_duration > 0:

            silence_file = (
                TEMP_DIR /
                f"silence_before_{index:04d}.wav"
            )

            print()
            print(
                f"Gap before segment {segment_id}: "
                f"{gap_duration:.3f} seconds"
            )

            create_silence(
                silence_file,
                gap_duration
            )

            processed_files.append(
                silence_file
            )

        # ----------------------------------------------------
        # PROCESS SEGMENT
        # ----------------------------------------------------

        processed_file = (
            TEMP_DIR /
            f"processed_segment_{index:04d}.wav"
        )

        print()
        print("-" * 70)

        print(
            f"Segment {index}/{len(segments)}"
        )

        print(
            "Segment ID:",
            segment_id
        )

        print(
            "Gender from Module 4:",
            gender
        )

        print(
            "Voice from Module 4:",
            voice
        )

        print(
            "Input audio:",
            input_audio
        )

        print(
            "Original timing:",
            f"{start:.3f}",
            "->",
            f"{end:.3f}"
        )

        print(
            "Target duration:",
            f"{target_duration:.3f}",
            "seconds"
        )

        process_segment_audio(
            input_audio,
            processed_file,
            target_duration
        )

        processed_files.append(
            processed_file
        )

        # ----------------------------------------------------
        # COUNT GENDER
        # ----------------------------------------------------

        if gender == "male":

            male_count += 1

        elif gender == "female":

            female_count += 1

        else:

            unknown_count += 1

        previous_end = end

        print(
            "✓ Segment normalized and synchronized"
        )

    # --------------------------------------------------------
    # CONCATENATE ALL AUDIO
    # --------------------------------------------------------

    if not processed_files:

        print()
        print(
            "ERROR: No processed audio files created."
        )

        raise SystemExit(1)

    print()
    print("=" * 70)
    print("COMBINING NORMALIZED SEGMENTS")
    print("=" * 70)

    concatenate_audio(
        processed_files,
        OUTPUT_FILE
    )

    # --------------------------------------------------------
    # CLEAN TEMPORARY DIRECTORY
    # --------------------------------------------------------

    print()
    print(
        "Removing temporary files..."
    )

    shutil.rmtree(
        TEMP_DIR,
        ignore_errors=True
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("✓ MODULE 5 COMPLETE")
    print("=" * 70)

    print()
    print(
        "Total segments:",
        len(segments)
    )

    print(
        "Male segments:",
        male_count
    )

    print(
        "Female segments:",
        female_count
    )

    print(
        "Unknown segments:",
        unknown_count
    )

    print()
    print(
        "Volume normalization:",
        "Enabled"
    )

    print(
        "Speed synchronization:",
        "Enabled"
    )

    print(
        "Target loudness:",
        TARGET_LUFS,
        "LUFS"
    )

    print()
    print(
        "Output audio:"
    )

    print(
        OUTPUT_FILE
    )

    print()
    print("=" * 70)
    print("✓ READY FOR MODULE 6")
    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()