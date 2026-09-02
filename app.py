import streamlit as st
import subprocess
import sys
import os
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

ENGLISH_DIR = PROJECT_DIR / "english"

SUPER_CODE = ENGLISH_DIR / "super_code.py"

INPUT_VIDEO = ENGLISH_DIR / "english_video.mp4"

OUTPUT_VIDEO = ENGLISH_DIR / "urdu_video.mp4"


# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI English to Urdu Video Dubbing",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# HEADER
# ============================================================

st.title("🎬 AI Video Dubbing")

st.subheader(
    "English → Urdu Automatic Video Dubbing"
)

st.write(
    "Upload an English video and automatically convert "
    "the English speech into Urdu speech."
)

st.divider()


# ============================================================
# CHECK BACKEND
# ============================================================

if not ENGLISH_DIR.exists():

    st.error(
        f"English backend folder not found:\n{ENGLISH_DIR}"
    )

    st.stop()


if not SUPER_CODE.exists():

    st.error(
        f"super_code.py not found:\n{SUPER_CODE}"
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Application")

    st.success("Backend found")

    st.write("### Pipeline")

    st.write("1. 🎵 Extract Audio")
    st.write("2. 🎤 Speech → Text")
    st.write("3. 🌐 English → Urdu")
    st.write("4. 🗣️ Urdu → Speech")
    st.write("5. 🎚️ Adjust Audio")
    st.write("6. 🎬 Create Video")


# ============================================================
# FILE UPLOAD
# ============================================================

st.header("📁 Upload English Video")

uploaded_video = st.file_uploader(
    "Choose an English video",
    type=[
        "mp4",
        "mkv",
        "avi",
        "mov",
        "webm"
    ]
)


# ============================================================
# WAIT FOR VIDEO
# ============================================================

if uploaded_video is None:

    st.info(
        "👆 Upload an English video to begin."
    )

    st.stop()


# ============================================================
# VIDEO INFORMATION
# ============================================================

st.success(
    f"Uploaded: {uploaded_video.name}"
)

col1, col2 = st.columns(2)


with col1:

    st.subheader("Original Video")

    st.video(uploaded_video)


with col2:

    st.subheader("File Information")

    file_size_mb = (
        len(uploaded_video.getbuffer())
        / (1024 * 1024)
    )

    st.write(
        f"**Filename:** {uploaded_video.name}"
    )

    st.write(
        f"**Size:** {file_size_mb:.2f} MB"
    )

    st.write(
        "**Target language:** Urdu 🇵🇰"
    )


st.divider()


# ============================================================
# START BUTTON
# ============================================================

start_dubbing = st.button(
    "🚀 Start Urdu Dubbing",
    type="primary",
    use_container_width=True
)


# ============================================================
# START DUBBING
# ============================================================

if start_dubbing:

    st.header("⚙️ Dubbing Process")

    progress = st.progress(0)

    status = st.empty()

    backend_log = []


    # ========================================================
    # SAVE INPUT VIDEO
    # ========================================================

    status.info(
        "📥 Saving uploaded video..."
    )

    try:

        with open(
            INPUT_VIDEO,
            "wb"
        ) as file:

            file.write(
                uploaded_video.getbuffer()
            )

    except Exception as error:

        st.error(
            "❌ Could not save uploaded video."
        )

        st.exception(error)

        st.stop()


    # ========================================================
    # VERIFY INPUT
    # ========================================================

    if not INPUT_VIDEO.exists():

        st.error(
            "❌ Input video was not created."
        )

        st.write(
            f"Expected location:\n{INPUT_VIDEO}"
        )

        st.stop()


    st.success(
        f"Input video saved:\n{INPUT_VIDEO}"
    )

    progress.progress(5)


    # ========================================================
    # REMOVE OLD OUTPUT
    # ========================================================

    if OUTPUT_VIDEO.exists():

        try:

            OUTPUT_VIDEO.unlink()

        except Exception as error:

            st.warning(
                "⚠️ Could not remove previous output video."
            )

            st.exception(error)


    # ========================================================
    # PREPARE UTF-8 ENVIRONMENT
    # ========================================================

    process_env = os.environ.copy()

    process_env["PYTHONIOENCODING"] = "utf-8"

    process_env["PYTHONUTF8"] = "1"


    # ========================================================
    # START BACKEND
    # ========================================================

    status.info(
        "🚀 Starting AI dubbing pipeline..."
    )

    progress.progress(10)


    try:

        process = subprocess.Popen(

            [
                sys.executable,
                str(SUPER_CODE)
            ],

            cwd=str(ENGLISH_DIR),

            stdout=subprocess.PIPE,

            stderr=subprocess.STDOUT,

            text=True,

            encoding="utf-8",

            errors="replace",

            bufsize=1,

            env=process_env
        )


        # ====================================================
        # READ BACKEND OUTPUT
        # ====================================================

        if process.stdout is not None:

            for line in process.stdout:

                line = line.rstrip()

                if not line:
                    continue

                backend_log.append(line)

                status.write(
                    f"⚙️ {line}"
                )


                # --------------------------------------------
                # PROGRESS
                # --------------------------------------------

                lower_line = line.lower()


                if "running: module1" in lower_line:

                    progress.progress(15)


                elif "running: module2" in lower_line:

                    progress.progress(30)


                elif "running: module3" in lower_line:

                    progress.progress(45)


                elif "running: module4" in lower_line:

                    progress.progress(60)


                elif "running: module5" in lower_line:

                    progress.progress(75)


                elif "running: module6" in lower_line:

                    progress.progress(90)


                elif "pipeline completed" in lower_line:

                    progress.progress(100)


        process.wait()


    except Exception as error:

        st.error(
            "❌ Could not start the backend pipeline."
        )

        st.exception(error)

        st.stop()


    # ========================================================
    # COMPLETE BACKEND LOG
    # ========================================================

    st.divider()

    st.subheader("🔍 Backend Log")

    complete_log = "\n".join(
        backend_log
    )

    with st.expander(
        "Show complete backend output",
        expanded=True
    ):

        st.code(
            complete_log,
            language="text"
        )


    # ========================================================
    # CHECK EXIT CODE
    # ========================================================

    if process.returncode != 0:

        st.error(
            "❌ The dubbing pipeline failed."
        )

        st.error(
            f"Backend exit code: {process.returncode}"
        )

        st.warning(
            "Check the Backend Log above for the actual error."
        )

        st.stop()


    # ========================================================
    # PIPELINE SUCCESS
    # ========================================================

    progress.progress(100)

    status.success(
        "🎉 All modules completed successfully!"
    )


    # ========================================================
    # CHECK OUTPUT VIDEO
    # ========================================================

    if not OUTPUT_VIDEO.exists():

        st.error(
            "❌ Pipeline completed, but the final "
            "Urdu video was not found."
        )

        st.write(
            f"Expected output:\n{OUTPUT_VIDEO}"
        )

        st.stop()


    # ========================================================
    # CHECK OUTPUT SIZE
    # ========================================================

    output_size_mb = (
        OUTPUT_VIDEO.stat().st_size
        / (1024 * 1024)
    )


    if output_size_mb <= 0:

        st.error(
            "❌ Output video is empty."
        )

        st.stop()


    # ========================================================
    # SUCCESS
    # ========================================================

    st.divider()

    st.success(
        "🎉 Urdu video created successfully!"
    )

    st.write(
        f"Output size: {output_size_mb:.2f} MB"
    )


    # ========================================================
    # SHOW FINAL VIDEO
    # ========================================================

    st.header("🎬 Urdu Dubbed Video")

    try:

        st.video(
            str(OUTPUT_VIDEO)
        )

    except Exception as error:

        st.warning(
            "Video was created, but preview failed."
        )

        st.exception(error)


    # ========================================================
    # DOWNLOAD
    # ========================================================

    try:

        with open(
            OUTPUT_VIDEO,
            "rb"
        ) as video_file:

            video_data = video_file.read()


        st.download_button(

            label="⬇️ Download Urdu Video",

            data=video_data,

            file_name="urdu_dubbed_video.mp4",

            mime="video/mp4",

            use_container_width=True
        )


    except Exception as error:

        st.error(
            "❌ Could not prepare video for download."
        )

        st.exception(error)


    # ========================================================
    # OUTPUT INFORMATION
    # ========================================================

    with st.expander(
        "📂 Output File Information"
    ):

        st.write(
            f"**Output:** `{OUTPUT_VIDEO}`"
        )

        st.write(
            f"**Size:** `{output_size_mb:.2f} MB`"
        )

        st.write(
            "**Format:** MP4"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "AI English → Urdu Video Dubbing System"
)