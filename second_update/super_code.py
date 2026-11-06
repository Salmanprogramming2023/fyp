import subprocess
import sys
import os


# ============================================================
# UTF-8
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
# RUN MODULE
# ============================================================

def run_module(module):

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


    if not os.path.exists(
        module_path
    ):

        print()
        print(
            "ERROR: Module not found:"
        )

        print(
            module_path
        )

        return False


    result = subprocess.run(
        [
            sys.executable,
            module_path
        ],
        cwd=BASE_DIR
    )


    if result.returncode != 0:

        print()
        print("=" * 70)
        print("❌ MODULE FAILED")
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
    print("✓ MODULE COMPLETED")
    print("=" * 70)

    return True


# ============================================================
# START
# ============================================================

print()
print("=" * 70)
print("ENGLISH VIDEO -> URDU VIDEO PIPELINE")
print("=" * 70)

print()
print(
    "Working directory:"
)

print(
    BASE_DIR
)


# ============================================================
# RUN
# ============================================================

for module in MODULES:

    success = run_module(
        module
    )


    if not success:

        print()
        print("=" * 70)
        print("❌ PIPELINE STOPPED")
        print("=" * 70)

        print()
        print(
            "Problem occurred in:"
        )

        print(
            module
        )

        sys.exit(1)


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("✓ COMPLETE PIPELINE FINISHED")
print("=" * 70)

print()

print(
    "Final video:"
)

print(
    os.path.join(
        BASE_DIR,
        "final_urdu_video.mp4"
    )
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
print(
    "✓ Male and female Urdu voices were selected"
)

print(
    "according to the gender information from Module 2."
)