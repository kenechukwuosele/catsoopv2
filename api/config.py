import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATSOOP_COURSES_DIR = os.environ.get(
    "CATSOOP_COURSES_DIR",
    os.path.join(PROJECT_ROOT, "courses")
)
ADMIN_HTML_PATH = os.path.join(os.path.dirname(__file__), "admin.html")
LIVE_FILES_DIR = os.environ.get(
    "LIVE_FILES_DIR",
    os.path.join(PROJECT_ROOT, "_live_files")
)

# RAG / Vector Store
VECTOR_STORE_DIR = os.environ.get(
    "VECTOR_STORE_DIR",
    os.path.join(PROJECT_ROOT, "_vectors")
)
EMBED_MODEL_NAME = os.environ.get(
    "EMBED_MODEL_NAME",
    "all-MiniLM-L6-v2"
)
OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)
OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "phi3:mini"
)

SERVER_PORT = os.environ.get("CU_QUIZ_PORT", "8000")
SERVER_BASE_URL = os.environ.get(
    "CU_QUIZ_BASE_URL",
    f"http://localhost:{SERVER_PORT}"
)
