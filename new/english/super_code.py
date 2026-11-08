import subprocess
import sys
import os
import json


# ============================================================
# UTF-8 OUTPUT
# ============================================================

try:

    sys.stdout.reconfigure(
        encoding="utf-8"
    )

    sys.stderr.reconfigure(
        encoding="utf-8"
    )

except Exception:

    pass


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# FILE NAMES
# ============================================================

FINAL_VIDEO_NAME = (
    "final_urdu_video.mp4"
)

OUTPUT_INFO_FILE = os.path.join(
    BASE_DIR,
    "pipeline_output.json"
)


# ============================================================
# MODULES
# ============================================================

MODULES = [

    "module1_extract_audio.py",

    "module2_speech_to_text.py",

    "module3_english_to_urdu.py",

    "module4_urdu_to_speech.py",

    "module5_adjust_audio.py",

    "module6_create_video.py"

]


# ============================================================
# FIND FINAL VIDEO
# ============================================================

def find_final_video():

    # --------------------------------------------------------
    # 1. Check expected location first
    # --------------------------------------------------------

    expected = os.path.join(
        BASE_DIR,
        FINAL_VIDEO_NAME
    )


    if os.path.isfile(
        expected
    ):

        return os.path.abspath(
            expected
        )


    # --------------------------------------------------------
    # 2. Search all subfolders
    # --------------------------------------------------------

    matches = []


    for root, dirs, files in os.walk(
        BASE_DIR
    ):

        # Ignore virtual environments
        # and cache folders.

        dirs[:] = [
            d
            for d in dirs
            if d not in {
                ".venv",
                "venv",
                "__pycache__",
                "module5_temp",
                "module4_temp"
            }
        ]


        if FINAL_VIDEO_NAME in files:

            path = os.path.join(
                root,
                FINAL_VIDEO_NAME
            )


            if os.path.isfile(
                path
            ):

                matches.append(
                    path
                )


    if not matches:

        return None


    # --------------------------------------------------------
    # Use largest valid final video
    # --------------------------------------------------------

    matches.sort(
        key=lambda p: os.path.getsize(p),
        reverse=True
    )


    return os.path.abspath(
        matches[0]
    )


# ============================================================
# SAVE PIPELINE OUTPUT
# ============================================================

def save_output_info(
    final_video
):

    information = {

        "pipeline_directory":
            BASE_DIR,

        "final_video":
            final_video,

        "exists":
            bool(
                final_video
                and
                os.path.isfile(
                    final_video
                )
            )
    }


    if (
        final_video
        and
        os.path.isfile(
            final_video
        )
    ):

        information[
            "file_size_bytes"
        ] = os.path.getsize(
            final_video
        )

        information[
            "file_size_mb"
        ] = round(
            os.path.getsize(
                final_video
            )
            /
            (1024 * 1024),
            2
        )


    try:

        with open(
            OUTPUT_INFO_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                information,
                file,
                ensure_ascii=False,
                indent=4
            )

    except Exception as error:

        print()
        print(
            "WARNING: Could not save pipeline_output.json"
        )

        print(
            error
        )


# ============================================================
# RUN MODULE
# ============================================================

def run_module(
    module
):

    module_path = os.path.join(
        BASE_DIR,
        module
    )


    print()
    print("=" * 70)
    print(
        "RUNNING:",
        module
    )
    print("=" * 70)

    print()

    print(
        "Location:"
    )

    print(
        module_path
    )


    # --------------------------------------------------------
    # CHECK MODULE
    # --------------------------------------------------------

    if not os.path.isfile(
        module_path
    ):

        print()
        print(
            "❌ ERROR: Module not found:"
        )

        print(
            module_path
        )

        return False


    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    try:

        result = subprocess.run(

            [
                sys.executable,
                module_path
            ],

            cwd=BASE_DIR

        )

    except Exception as error:

        print()
        print(
            "❌ ERROR executing module:"
        )

        print(
            error
        )

        return False


    # --------------------------------------------------------
    # CHECK EXIT CODE
    # --------------------------------------------------------

    if result.returncode != 0:

        print()
        print("=" * 70)
        print(
            "❌ MODULE FAILED"
        )
        print("=" * 70)

        print()

        print(
            "Module:",
            module
        )

        print(
            "Exit code:",
            result.returncode
        )

        return False


    print()
    print("=" * 70)
    print(
        "✓ MODULE COMPLETED"
    )
    print("=" * 70)

    return True


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 70)
print(
    "       ENGLISH VIDEO → URDU VIDEO PIPELINE"
)
print("=" * 70)

print()

print(
    "Pipeline directory:"
)

print(
    BASE_DIR
)

print()

print(
    "Python:"
)

print(
    sys.executable
)


# ============================================================
# RUN MODULES
# ============================================================

for number, module in enumerate(
    MODULES,
    start=1
):

    print()
    print()
    print("=" * 70)

    print(
        f"STEP {number}/{len(MODULES)}"
    )

    print("=" * 70)


    success = run_module(
        module
    )


    if not success:

        print()
        print("=" * 70)
        print(
            "❌ PIPELINE STOPPED"
        )
        print("=" * 70)

        print()

        print(
            "Problem occurred in:"
        )

        print(
            module
        )

        # Save whatever output currently exists

        final_video = find_final_video()

        save_output_info(
            final_video
        )

        sys.exit(1)


# ============================================================
# VERIFY FINAL VIDEO
# ============================================================

print()
print("=" * 70)
print(
    "VERIFYING FINAL VIDEO"
)
print("=" * 70)


final_video = find_final_video()


if final_video is None:

    print()
    print(
        "❌ PIPELINE FINISHED BUT FINAL VIDEO WAS NOT FOUND"
    )

    print()

    print(
        "Expected filename:"
    )

    print(
        FINAL_VIDEO_NAME
    )

    print()

    print(
        "Searched inside:"
    )

    print(
        BASE_DIR
    )

    print()

    print(
        "This means Module 6 returned success,"
    )

    print(
        "but the final video file could not be located."
    )

    print()

    print(
        "PIPELINE STATUS: FAILED"
    )

    save_output_info(
        None
    )

    sys.exit(1)


# ============================================================
# VERIFY FILE SIZE
# ============================================================

file_size_bytes = os.path.getsize(
    final_video
)


file_size_mb = (
    file_size_bytes
    /
    (1024 * 1024)
)


if file_size_bytes <= 0:

    print()
    print(
        "❌ FINAL VIDEO FILE IS EMPTY"
    )

    save_output_info(
        None
    )

    sys.exit(1)


# ============================================================
# SAVE OUTPUT INFORMATION
# ============================================================

save_output_info(
    final_video
)


# ============================================================
# FINAL SUCCESS
# ============================================================

print()
print("=" * 70)
print(
    "✓ COMPLETE PIPELINE FINISHED"
)
print("=" * 70)

print()

print(
    "All modules completed successfully."
)

print()

print(
    "FINAL VIDEO FOUND:"
)

print(
    final_video
)

print()

print(
    f"File size: {file_size_mb:.2f} MB"
)

print()

print(
    "Pipeline output information:"
)

print(
    OUTPUT_INFO_FILE
)

print()

print(
    "Male voice:"
)

print(
    "ur-PK-AsadNeural"
)

print()

print(
    "Female voice:"
)

print(
    "ur-PK-UzmaNeural"
)

print()

print("=" * 70)
print(
    "✓ FINAL URDU VIDEO VERIFIED"
)
print("=" * 70)