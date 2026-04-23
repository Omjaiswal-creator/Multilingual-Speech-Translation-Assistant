import os
import logging
import whisper

logger = logging.getLogger(__name__)

# ------------------ LOAD MODEL ONCE ------------------
# This will download the model only the first time
# Options: tiny, base, small, medium, large
model = whisper.load_model("base")


# ------------------ MAIN FUNCTION ------------------
def speech_to_text(audio_path: str) -> str:
    """
    Convert audio file → text using Whisper

    FIXES:
    - Works in Flask (not Colab)
    - Uses absolute path (Windows fix)
    - Handles file errors safely
    """

    try:
        # 🔥 Convert to absolute path (IMPORTANT for Windows)
        audio_path = os.path.abspath(audio_path)

        logger.info(f"Processing file: {audio_path}")

        # ✅ Check if file exists
        if not os.path.exists(audio_path):
            return f"Error: File not found → {audio_path}"

        # ✅ Transcribe audio
        result = model.transcribe(audio_path)

        text = result.get("text", "").strip()

        # ✅ Check empty result
        if not text:
            return "Error: Could not extract speech from audio"

        return text

    except Exception as e:
        logger.error(f"Whisper Error: {str(e)}")
        return f"Error: {str(e)}"