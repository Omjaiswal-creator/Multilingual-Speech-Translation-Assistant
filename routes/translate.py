"""
Translation blueprint — /translate (POST)
Handles:
- Text translation
- Audio → Text → Translation (Whisper)
- In-memory history storage
"""

import os
import time
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from services.history_store import add_entry
from models.groq_translator import groq_translate
from models.translator import translate_text
from models.speech_to_text import speech_to_text

logger = logging.getLogger(__name__)

translate_bp = Blueprint("translate", __name__)

# ✅ Supported audio formats
ALLOWED_AUDIO = {"mp3", "wav", "m4a", "ogg", "flac", "webm"}


# ------------------ VALIDATION ------------------
def _allowed_audio(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AUDIO


# ------------------ SAVE AUDIO ------------------
def _save_audio(audio_file, upload_folder: str):
    """
    Save uploaded audio file safely and return absolute path
    """

    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(audio_file.filename)
    unique_name = f"{int(time.time())}_{filename}"

    # ✅ Absolute path fix (IMPORTANT)
    save_path = os.path.abspath(os.path.join(upload_folder, unique_name))

    audio_file.save(save_path)

    # ✅ Verify file exists
    if not os.path.exists(save_path):
        raise FileNotFoundError(f"File not saved correctly: {save_path}")

    logger.info(f"Audio saved at: {save_path}")

    return unique_name, save_path


# ------------------ MAIN ROUTE ------------------
@translate_bp.route("/translate", methods=["POST"])
@login_required
def translate():

    text = request.form.get("text", "").strip()
    source_lang = request.form.get("source_lang", "en")
    target_lang = request.form.get("target_lang", "hi")
    model_choice = request.form.get("model_choice", "huggingface")

    audio_filename = None
    extracted_text = None

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    # ==========================================================
    # 🎤 SPEECH MODEL FLOW
    # ==========================================================
    if model_choice == "speech":

        audio_file = request.files.get("audio")

        # ❌ No file
        if not audio_file or audio_file.filename == "":
            flash("Please upload an audio file.", "error")
            return redirect(url_for("main.translate_page"))

        # ❌ Invalid format
        if not _allowed_audio(audio_file.filename):
            flash("Invalid format. Allowed: mp3, wav, m4a, ogg, flac, webm", "error")
            return redirect(url_for("main.translate_page"))

        try:
            # ✅ Save file
            audio_filename, save_path = _save_audio(audio_file, upload_folder)

            # 🔍 Debug logs
            logger.info(f"Processing audio file: {save_path}")
            logger.info(f"File exists: {os.path.exists(save_path)}")

            # ❌ Safety check
            if not os.path.exists(save_path):
                flash("Uploaded file not found. Try again.", "error")
                return redirect(url_for("main.translate_page"))

            # 🎤 Speech → Text
            extracted_text = speech_to_text(save_path)

            # ❌ Whisper failed
            if not extracted_text or "Error:" in extracted_text:
                flash(f"Speech recognition failed: {extracted_text}", "error")
                return redirect(url_for("main.translate_page"))

            # ❌ Empty speech
            if extracted_text.strip() == "":
                flash("No speech detected in audio.", "error")
                return redirect(url_for("main.translate_page"))

            # 🌍 Translate extracted text
            translated_text = translate_text(extracted_text, source_lang, target_lang)

            # Use extracted text as original
            text = extracted_text

        except Exception as e:
            logger.error(f"Speech processing error: {e}")
            flash(f"Error processing audio: {str(e)}", "error")
            return redirect(url_for("main.translate_page"))

    # ==========================================================
    # 📝 TEXT / GROQ MODEL FLOW
    # ==========================================================
    else:

        audio_file = request.files.get("audio")

        # Optional audio save (no processing)
        if audio_file and audio_file.filename:
            if _allowed_audio(audio_file.filename):
                audio_filename, _ = _save_audio(audio_file, upload_folder)

        if not text:
            flash("Please enter text.", "error")
            return redirect(url_for("main.translate_page"))

        try:
            if model_choice == "groq":
                translated_text = groq_translate(text, source_lang, target_lang)
            else:
                translated_text = translate_text(text, source_lang, target_lang)

        except Exception as e:
            logger.error(f"Translation error: {e}")
            translated_text = f"Translation error: {str(e)}"

    # ==========================================================
    # 💾 SAVE HISTORY (IN MEMORY)
    # ==========================================================
    add_entry(
        user_email=current_user.email,
        original_text=text,
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=target_lang,
        model_used=model_choice,
        audio_filename=audio_filename,
    )

    # ==========================================================
    # 📤 RESULT PAGE
    # ==========================================================
    return render_template(
        "result.html",
        original_text=text,
        translated_text=translated_text,
        extracted_text=extracted_text,
        model_used=model_choice,
        source_lang=source_lang,
        target_lang=target_lang,
        audio_filename=audio_filename,
    )


# ── /process alias — delegates to the same handler ───────────────────────────
# Allows both <form action="/process"> and <form action="/translate"> to work.
@translate_bp.route("/process", methods=["POST"])
@login_required
def process():
    """Thin alias — /process POSTs are handled identically to /translate."""
    return translate()
