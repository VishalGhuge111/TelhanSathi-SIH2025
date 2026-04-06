from flask import Blueprint, request, jsonify, session, current_app, send_from_directory
import os
import uuid
from datetime import datetime

sahayak_bp = Blueprint('sahayak', __name__)


@sahayak_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """Simple chat endpoint that returns a mocked Gemini-style response.
    Expects JSON: { input_text: string, voice_mode: bool }
    """
    data = request.get_json() or {}
    user_input = data.get('input_text', '').strip()
    voice_mode = data.get('voice_mode', False)

    # Fetch session context and analysis
    user_ctx = session.get('user_context', {})
    analysis = session.get('analysis')

    # Build a short persuasive reply using analysis if available
    if analysis:
        curr = analysis.get('current_profit_total', 0)
        oil = analysis.get('oilseed_profit_total', 0)
        recommended = analysis.get('oilseed_recommendation', 'mustard')
        diff = round((oil - curr), 2)
        bot_text = f"Namaste! A quick look: your current profit ≈ ₹{int(curr)}. Switching to {recommended} could give ~₹{int(oil)} (≈₹{int(diff)} more). Want details?"
        show_visual = 'profit_chart'
    else:
        bot_text = "Namaste! I can analyze your farm — tell me your crop and land size or open Onboarding to provide details."
        show_visual = None

    # Mock audio generation placeholder (no real TTS here)
    audio_url = None

    response = {
        'text': bot_text,
        'audio_url': audio_url,
        'show_visual': show_visual,
        'timestamp': datetime.utcnow().isoformat()
    }

    return jsonify(response)


@sahayak_bp.route('/api/audio_upload', methods=['POST'])
def api_audio_upload():
    """Accept audio blob upload and return mocked transcription.
    Saves the file under `static/audio/uploads` and returns a fake transcription.
    """
    f = request.files.get('audio')
    if not f:
        return jsonify({'error': 'no file uploaded'}), 400

    upload_dir = os.path.join(current_app.root_path, 'static', 'audio', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"upload_{uuid.uuid4().hex}.webm"
    path = os.path.join(upload_dir, filename)
    f.save(path)

    # In a real implementation, run STT (Whisper/OpenAI/Google) here.
    mocked_transcript = 'यह ऑडियो का टेक्स्ट ट्रांसक्रिप्शन है'  # placeholder Hindi text

    return jsonify({'transcript': mocked_transcript, 'file': f'/static/audio/uploads/{filename}'}), 200


@sahayak_bp.route('/static/audio/<path:filename>')
def serve_audio(filename):
    root = os.path.join(current_app.root_path, 'static', 'audio')
    return send_from_directory(root, filename)
