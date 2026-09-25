import os
from flask import Flask, jsonify, render_template, request
import json
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

from config import ConfigError, get_config
from document_processor import process_document
from rag import RAGEngine

try:
    config = get_config()
    rag_engine = RAGEngine(config)
except ConfigError:
    config = None
    rag_engine = None

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB
CHAT_HISTORY_DIR = Path("chat_history")
CHAT_HISTORY_DIR.mkdir(exist_ok=True)


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File is too large. Maximum size is 100 MB."}), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "The requested endpoint was not found."}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "An internal server error occurred."}), 500


def get_history_file(user_id):
    safe_user_id = secure_filename(str(user_id))

    if not safe_user_id:
        safe_user_id = "default_user"

    return CHAT_HISTORY_DIR / f"{safe_user_id}.json"


def load_chat_history(user_id):
    history_file = get_history_file(user_id)

    if not history_file.exists():
        return []

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def save_chat_history(user_id, history):
    history_file = get_history_file(user_id)

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def error_response(message, status=400):
    return jsonify({"error": message}), status


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if rag_engine is None:
        return error_response("Application configuration is missing. Check your .env file.", 500)

    if "file" not in request.files:
        return error_response("Please select a document.")

    file = request.files["file"]
    if not file or not file.filename:
        return error_response("Please select a document.")

    filename = secure_filename(file.filename)
    if not filename:
        return error_response("Invalid filename.")

    try:
        result = rag_engine.index_uploaded_file(file, filename)
        return jsonify(result)
    except ValueError as exc:
        return error_response(str(exc))
    except Exception:
        app.logger.exception("Document indexing failed")
        return error_response("Unable to process the document right now.", 500)



@app.route("/chat-history", methods=["GET"])
def get_chat_history():
    user_id = request.args.get("user_id", "default_user")

    history = load_chat_history(user_id)

    return jsonify({
        "history": history
    })


@app.route("/chat-history", methods=["POST"])
def create_chat():
    data = request.get_json(silent=True) or {}

    user_id = str(data.get("user_id", "default_user")).strip()

    if not user_id:
        user_id = "default_user"

    history = load_chat_history(user_id)

    chat_id = str(uuid.uuid4())

    chat = {
        "id": chat_id,
        "title": "New Chat",
        "messages": []
    }

    history.append(chat)

    save_chat_history(user_id, history)

    return jsonify(chat)


@app.route("/chat-history/<chat_id>", methods=["DELETE"])
def delete_chat_history(chat_id):
    user_id = request.args.get("user_id", "default_user")

    history = load_chat_history(user_id)

    updated_history = [
        chat for chat in history
        if chat.get("id") != chat_id
    ]

    save_chat_history(user_id, updated_history)

    return jsonify({
        "message": "Chat deleted.",
        "chat_id": chat_id
    })
@app.route("/documents", methods=["GET"])
def documents():
    if rag_engine is None:
        return error_response("Application configuration is missing. Check your .env file.", 500)
    try:
        return jsonify({"documents": rag_engine.list_documents()})
    except Exception:
        app.logger.exception("Document listing failed")
        return error_response("Unable to load documents right now.", 500)


@app.route("/documents/<document_id>", methods=["DELETE"])
def delete_document(document_id):
    if rag_engine is None:
        return error_response("Application configuration is missing. Check your .env file.", 500)
    try:
        return jsonify(rag_engine.delete_document(document_id))
    except ValueError as exc:
        return error_response(str(exc))
    except Exception:
        app.logger.exception("Document deletion failed")
        return error_response("Unable to delete the document right now.", 500)


@app.route("/chat", methods=["POST"])
def chat():
    if rag_engine is None:
        return error_response("Application configuration is missing. Check your .env file.", 500)

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return error_response("Please enter a question.")

    try:
        result = rag_engine.answer(question)
        return jsonify(result)
    except ValueError as exc:
        return error_response(str(exc))
    except Exception as exc:
        app.logger.exception("Chat failed")
        error_msg = str(exc)
        if "503" in error_msg or "high demand" in error_msg.lower() or "UNAVAILABLE" in error_msg:
            return error_response("The AI model is temporarily experiencing high traffic spikes. Please ask again in a few moments.", 503)
        return error_response(f"Unable to generate answer: {error_msg}", 500)


@app.route("/clear", methods=["POST"])
def clear_chat():
    # Chat history is maintained in the browser, so this endpoint intentionally
    # does not delete documents or vectors.
    return jsonify({"message": "Chat cleared."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
