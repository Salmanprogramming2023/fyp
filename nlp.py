import streamlit as st
import subprocess
import sys
import os


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="English → Urdu AI Video Dubbing",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENGLISH_DIR = os.path.join(
    BASE_DIR,
    "english"
)

SUPER_CODE = os.path.join(
    ENGLISH_DIR,
    "super_code.py"
)

INPUT_VIDEO = os.path.join(
    ENGLISH_DIR,
    "english_video.mp4"
)

OUTPUT_VIDEO = os.path.join(
    ENGLISH_DIR,
    "urdu_video.mp4"
)


# ============================================================
# UI
# ============================================================

st.title("🎬 English → Urdu AI Video Dubbing")

st.write(
    "Automatically convert an English video into an Urdu-dubbed video."
)

st.divider()


# ============================================================
# UPLOAD VIDEO
# ============================================================

uploaded_file = st.file_uploader(
    "Upload English Video",
    type=["mp4", "mkv", "avi", "mov"]
)


if uploaded_file is not None:

    st.success(
        f"Video selected: {uploaded_file.name}"
    )

    st.video(
        uploaded_file
    )

    st.divider()


    # ========================================================
    # START DUBBING
    # ========================================================

    if st.button(
        "🚀 Start Dubbing",
        type="primary"
    ):

        # ----------------------------------------------------
        # SAVE UPLOADED VIDEO
        # ----------------------------------------------------

        st.info(
            "Preparing video..."
        )

        with open(
            INPUT_VIDEO,
            "wb"
        ) as file:

            file.write(
                uploaded_file.getbuffer()
            )


        # ----------------------------------------------------
        # REMOVE OLD OUTPUT
        # ----------------------------------------------------

        if os.path.exists(
            OUTPUT_VIDEO
        ):

            os.remove(
                OUTPUT_VIDEO
            )


        # ----------------------------------------------------
        # RUN SUPER CODE
        # ----------------------------------------------------

        st.info(
            "🎬 Dubbing pipeline started..."
        )

        progress = st.progress(0)

        status = st.empty()


        status.write(
            "🔄 Running AI dubbing pipeline..."
        )

        progress.progress(10)


        try:

            result = subprocess.run(

                [
                    sys.executable,
                    SUPER_CODE
                ],

                cwd=ENGLISH_DIR,

                capture_output=True,

                text=True

            )


            # ------------------------------------------------
            # SHOW BACKEND OUTPUT
            # ------------------------------------------------

            with st.expander(
                "View processing log"
            ):

                st.code(
                    result.stdout
                )


            # ------------------------------------------------
            # CHECK ERROR
            # ------------------------------------------------

            if result.returncode != 0:

                progress.progress(100)

                st.error(
                    "❌ The dubbing pipeline failed."
                )

                if result.stderr:

                    st.code(
                        result.stderr
                    )

            else:

                progress.progress(100)

                status.write(
                    "✅ Dubbing completed!"
                )

                st.success(
                    "Urdu video created successfully."
                )


                # --------------------------------------------
                # CHECK OUTPUT
                # --------------------------------------------

                if os.path.exists(
                    OUTPUT_VIDEO
                ):

                    st.subheader(
                        "🎥 Urdu Dubbed Video"
                    )

                    st.video(
                        OUTPUT_VIDEO
                    )


                    # ----------------------------------------
                    # DOWNLOAD
                    # ----------------------------------------

                    with open(
                        OUTPUT_VIDEO,
                        "rb"
                    ) as video_file:

                        st.download_button(

                            label="⬇️ Download Urdu Video",

                            data=video_file,

                            file_name="urdu_video.mp4",

                            mime="video/mp4"

                        )

                else:

                    st.error(
                        "Pipeline completed, but urdu_video.mp4 was not found."
                    )