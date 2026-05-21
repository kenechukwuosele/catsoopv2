# ============================================================
# CU Quiz App — FastAPI Entry Point
# ============================================================
# All routes are split into modules under api/routes/
# Schemas in api/schemas.py
# Templates in api/templates.py
# WebSocket in api/websocket.py
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from . import models
from .database import engine
from .websocket import get_router as get_ws_router
from .routes.questions import get_router as get_questions_router
from .routes.admin import get_router as get_admin_router
from .routes.courses import get_router as get_courses_router
from .routes.hints import get_router as get_hints_router
from .routes.rag import get_router as get_rag_router

# Create DB tables on startup
models.Base.metadata.create_all(bind=engine)


def ensure_schema():
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        if "attempts" in tables:
            cols = [c["name"] for c in inspector.get_columns("attempts")]
            if "attempt_session_id" not in cols:
                conn.execute(text("ALTER TABLE attempts ADD COLUMN attempt_session_id TEXT"))
        if "engagement_samples" not in tables:
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


ensure_schema()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(get_ws_router())
app.include_router(get_questions_router())
app.include_router(get_admin_router())
app.include_router(get_courses_router())
app.include_router(get_hints_router())
app.include_router(get_rag_router())
