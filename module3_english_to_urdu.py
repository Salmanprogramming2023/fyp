import os
from deep_translator import GoogleTranslator


# ============================================================
# ENGLISH → URDU TRANSLATION
# SINGLE-SPEAKER VIDEO
# NO SEGMENTS / NO GENDER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "english_transcript.txt"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "urdu_transcript.txt"
)

MAX_CHARS = 4000


# ============================================================
# CHECK INPUT
# ============================================================

if not os.path.exists(INPUT_FILE):

    print("ERROR: english_transcript.txt not found.")
    print(INPUT_FILE)

    raise SystemExit(1)


# ============================================================
# READ ENGLISH
# ============================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as file:

    english_text = file.read().strip()


if not english_text:

    print("ERROR: English transcript is empty.")

    raise SystemExit(1)


print("=" * 70)
print("ENGLISH → URDU TRANSLATION")
print("=" * 70)

print()
print(
    "English characters:",
    len(english_text)
)


# ============================================================
# CREATE TRANSLATOR
# ============================================================

translator = GoogleTranslator(
    source="en",
    target="ur"
)


# ============================================================
# SPLIT INTO SMALL CHUNKS
# ============================================================

def split_text(
    text,
    max_chars=4000
):

    words = text.split()

    chunks = []

    current = ""


    for word in words:

        if (
            len(current)
            +
            len(word)
            +
            1
            <= max_chars
        ):

            if current:

                current += " " + word

            else:

                current = word

        else:

            if current:

                chunks.append(
                    current
                )

            current = word


    if current:

        chunks.append(
            current
        )


    return chunks


chunks = split_text(
    english_text,
    MAX_CHARS
)


print()
print(
    "Translation chunks:",
    len(chunks)
)


# ============================================================
# TRANSLATE
# ============================================================

urdu_chunks = []


for index, chunk in enumerate(
    chunks,
    start=1
):

    print()
    print(
        f"Translating {index}/{len(chunks)}..."
    )


    translated = None


    # --------------------------------------------------------
    # Retry
    # --------------------------------------------------------

    for attempt in range(3):

        try:

            translated = translator.translate(
                chunk
            )

            if translated:

                translated = translated.strip()

                break

        except Exception as error:

            print(
                f"Attempt {attempt + 1}/3 failed."
            )

            if attempt == 2:

                print(error)


    # --------------------------------------------------------
    # Check translation
    # --------------------------------------------------------

    if not translated:

        print()
        print(
            "ERROR: Translation failed."
        )

        print()
        print(
            "Problem text:"
        )

        print(
            chunk
        )

        raise SystemExit(1)


    urdu_chunks.append(
        translated
    )


    print(
        "✓ Completed"
    )


# ============================================================
# JOIN
# ============================================================

urdu_text = "\n\n".join(
    urdu_chunks
)


# ============================================================
# SAVE
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        urdu_text
    )


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 70)
print("URDU TRANSLATION")
print("=" * 70)

print()
print(
    urdu_text
)


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("✓ TRANSLATION COMPLETE")
print("=" * 70)

print()
print(
    "Saved to:"
)

print(
    os.path.abspath(
        OUTPUT_FILE
    )
)