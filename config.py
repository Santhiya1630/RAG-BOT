import os
from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    pass


def _required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is missing in .env.")
    return value


def get_config():
    gemini_key = _required("GEMINI_API_KEY")
    flask_secret = _required("FLASK_SECRET_KEY")
    qdrant_url = _required("QDRANT_URL")
    qdrant_api_key = _required("QDRANT_API_KEY")

    qdrant_port = os.getenv("QDRANT_PORT")
    if not qdrant_port and "cloud.qdrant.io" in qdrant_url.lower():
        qdrant_port = 443
    elif qdrant_port:
        qdrant_port = int(qdrant_port)
    else:
        qdrant_port = None

    return {
        "gemini_api_key": gemini_key,
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
        "qdrant_url": qdrant_url,
        "qdrant_port": qdrant_port,
        "qdrant_api_key": qdrant_api_key,
        "qdrant_timeout": int(os.getenv("QDRANT_TIMEOUT", "60")),
        "qdrant_collection": os.getenv("QDRANT_COLLECTION", "rag_documents").strip(),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "gemini-embedding-001").strip(),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "800")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "100")),
        "top_k": int(os.getenv("TOP_K", "5")),
        "flask_secret_key": flask_secret,
    }
