# ============================================================
# CU Quiz App — FastAPI Entry Point
# ============================================================
# Questions  → file-based (quiz.catsoop) via routes/file_questions.py
# Hints      → JSON files in _hint_store/ via routes/hints.py
# Grades     → CatSooP cslog via routes/file_questions.py
# Engagement → SQLite (engagement_samples table) via routes/hints.py
# Courses    → filesystem scaffolding via routes/courses.py
# ============================================================

import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from . import models
from .database import engine
from .websocket import get_router as get_ws_router
from .routes.file_questions import get_router as get_file_questions_router
from .routes.admin import get_router as get_admin_router
from .routes.live_files import get_router as get_live_files_router
from .routes.face_enrollments import get_router as get_face_enrollments_router
from .routes.repair import get_router as get_repair_router
from .routes.courses import get_router as get_courses_router
from .routes.hints import get_router as get_hints_router
from .routes.rag import get_router as get_rag_router
from .routes.gamification import get_router as get_gamification_router
from .routes.lecturer import get_router as get_lecturer_router
from .config import CATSOOP_COURSES_DIR

DATA_ROOT = os.path.dirname(CATSOOP_COURSES_DIR)
HINT_STORE = os.path.join(DATA_ROOT, "_hint_store")

# Create DB tables (only engagement_samples, live_files, content_chunks remain)
models.Base.metadata.create_all(bind=engine)


def ensure_schema():
    """Add any missing columns to existing tables."""
    with engine.begin() as conn:
        inspector = inspect(conn)
        if "engagement_samples" not in inspector.get_table_names():
            models.EngagementSample.__table__.create(bind=conn)
        else:
            cols = [c["name"] for c in inspector.get_columns("engagement_samples")]
            for col, coltype in [
                ("eye_aspect_ratio", "FLOAT"),
                ("mouth_open_ratio", "FLOAT"),
                ("smile_score", "FLOAT"),
                ("head_yaw", "FLOAT"),
                ("head_pitch", "FLOAT"),
                ("head_roll", "FLOAT"),
                ("affect_state", "TEXT"),
            ]:
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE engagement_samples ADD COLUMN {col} {coltype}"))


def migrate_hints_to_json():
    """
    One-time migration: copy any hints still in the old SQLite table to JSON files.
    Safe to run repeatedly — skips if the hints table no longer exists.
    """
    from sqlalchemy import text as sa_text
    try:
        with engine.connect() as conn:
            tables = inspect(conn).get_table_names()
            if "hints" not in tables or "questions" not in tables:
                return
            rows = conn.execute(sa_text(
                "SELECT q.course, q.week, q.id, h.hint_number, h.hint_text "
                "FROM hints h JOIN questions q ON h.question_id = q.id "
                "ORDER BY q.course, q.week, q.id, h.hint_number"
            )).fetchall()
    except Exception:
        return

    # Group by (course, week, question_id)
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for row in rows:
        course, week, qid, num, text = row
        grouped[(course, week, qid)].append({"number": num, "text": text})

    for (course, week, qid), hints in grouped.items():
        csq_name = f"q_{qid}"
        hint_dir = os.path.join(HINT_STORE, course, week)
        hint_file = os.path.join(hint_dir, f"{csq_name}.json")
        if os.path.exists(hint_file):
            continue  # already migrated
        os.makedirs(hint_dir, exist_ok=True)
        with open(hint_file, "w") as f:
            json.dump(hints, f)


ensure_schema()
migrate_hints_to_json()

app = FastAPI()

# Rate limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Always include the server's own origin so admin.html fetch() calls don't hit CORS
_server_origin = os.environ.get("CU_QUIZ_BASE_URL", f"http://localhost:{os.environ.get('CU_QUIZ_PORT', '8000')}")
_allowed_origins = list({o.strip() for o in os.environ.get("CU_QUIZ_ALLOWED_ORIGINS", "http://localhost:7667").split(",") if o.strip()} | {_server_origin})
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_models_dir = os.path.join(os.path.dirname(__file__), "static", "models")
app.mount("/static/models", StaticFiles(directory=_models_dir), name="face_models")

_admin_static_dir = os.path.join(os.path.dirname(__file__), "static", "admin")
app.mount("/static/admin", StaticFiles(directory=_admin_static_dir), name="admin_static")

app.include_router(get_ws_router())
app.include_router(get_file_questions_router())
app.include_router(get_admin_router())
app.include_router(get_live_files_router())
app.include_router(get_face_enrollments_router())
app.include_router(get_repair_router())
app.include_router(get_courses_router())
app.include_router(get_hints_router())
app.include_router(get_rag_router())
app.include_router(get_gamification_router())
app.include_router(get_lecturer_router())
