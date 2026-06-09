"""
Hint management — storage moved from SQLite to JSON files in _hint_store/.
AI generation (RAG + Ollama) is retained here.
Engagement sampling (POST /{course}/{week}/engagement) is also here.
"""
import os
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import require_admin, require_user
from ..validation import safe_course, safe_week, safe_qname
from ..schemas import EngagementSampleCreate
from ..limiter import limiter
from ..services.rag_service import RAGService
from ..services.ollama_client import OllamaClient
from ..config import CATSOOP_COURSES_DIR
from .file_questions import parse_questions, quiz_file_path

DATA_ROOT = os.path.dirname(CATSOOP_COURSES_DIR)
HINT_STORE = os.path.join(DATA_ROOT, "_hint_store")


def _hint_path(course: str, week: str, csq_name: str) -> str:
    return os.path.join(HINT_STORE, course, week, f"{csq_name}.json")


def _load_hints(course: str, week: str, csq_name: str) -> list[dict]:
    path = _hint_path(course, week, csq_name)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _save_hints(course: str, week: str, csq_name: str, hints: list[dict]):
    hint_dir = os.path.join(HINT_STORE, course, week)
    os.makedirs(hint_dir, exist_ok=True)
    with open(os.path.join(hint_dir, f"{csq_name}.json"), "w") as f:
        json.dump(hints, f)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_question_context(course: str, week: str, csq_name: str) -> str:
    """Return full question text + answer choices for Ollama hint context."""
    questions = parse_questions(quiz_file_path(course, week))
    q = next((q for q in questions if q["csq_name"] == csq_name), None)
    if not q:
        return ""
    text = (q.get("question_text") or "").strip()
    options = q.get("options") or []
    if options:
        labels = "ABCDEFGHIJ"
        opts_str = "  ".join(f"{labels[i]}) {opt}" for i, opt in enumerate(options))
        return f"{text}\nOptions: {opts_str}"
    return text


def get_router() -> APIRouter:
    router = APIRouter()

    # --- Engagement analytics (admin) ---

    @router.get("/admin/engagement/{course}/{week}", dependencies=[Depends(require_admin)])
    def get_engagement_summary(course: str, week: str, db: Session = Depends(get_db)):
        from collections import defaultdict
        course = safe_course(course); week = safe_week(week)
        rows = db.query(models.EngagementSample).filter_by(course=course, week=week).all()
        by_user: dict = defaultdict(list)
        for r in rows:
            by_user[r.username].append(r)
        students = []
        for username, samples in sorted(by_user.items()):
            sessions = len({s.attempt_session_id for s in samples})
            avg_eng = round(sum(s.engagement_score or 0 for s in samples) / len(samples), 1)
            face_pct = round(100 * sum(1 for s in samples if s.face_present) / len(samples), 1)
            last_seen = max(s.timestamp for s in samples)
            all_states = {"focused", "confused", "struggling", "disengaged", "distracted"}
            affect: dict = {s: 0 for s in all_states}
            affect["unknown"] = 0
            smile_vals = [s.smile_score for s in samples if s.smile_score is not None]
            ear_vals = [s.eye_aspect_ratio for s in samples if s.eye_aspect_ratio is not None]
            for s in samples:
                k = s.affect_state if s.affect_state in all_states else "unknown"
                affect[k] += 1
            students.append({
                "username": username, "sessions": sessions, "samples": len(samples),
                "avg_engagement": avg_eng, "face_pct": face_pct,
                "last_seen": last_seen, "affect": affect,
                "avg_smile": round(sum(smile_vals) / len(smile_vals), 2) if smile_vals else None,
                "avg_ear": round(sum(ear_vals) / len(ear_vals), 3) if ear_vals else None,
            })
        avg_all = round(sum(s["avg_engagement"] for s in students) / len(students), 1) if students else 0
        face_all = round(sum(s["face_pct"] for s in students) / len(students), 1) if students else 0
        return {"course": course, "week": week, "total_samples": len(rows),
                "total_students": len(students), "avg_engagement": avg_all,
                "avg_face_pct": face_all, "students": students}

    # --- Engagement samples (unchanged — still writes to SQLite) ---

    @router.post("/{course}/{week}/engagement")
    async def log_engagement(course: str, week: str, payload: EngagementSampleCreate,
                             db: Session = Depends(get_db),
                             user: dict = Depends(require_user)):
        course = safe_course(course); week = safe_week(week)
        if payload.username and payload.username != user["username"]:
            raise HTTPException(status_code=403, detail="Cannot log engagement for another user")
        try:
            sample = models.EngagementSample(
                attempt_id=None,
                attempt_session_id=payload.attemptSessionId,
                username=user["username"],
                course=course,
                week=week,
                timestamp=payload.timestamp,
                face_present=1 if payload.facePresent else 0,
                gaze_centered=1 if payload.gazeCentered else 0,
                head_pose=payload.headPose,
                inactivity_seconds=payload.inactivitySeconds,
                engagement_score=payload.engagementScore,
                focus_state=payload.focusState,
                click_count=payload.clickCount,
                typing_count=payload.typingCount,
                eye_aspect_ratio=payload.eyeAspectRatio,
                mouth_open_ratio=payload.mouthOpenRatio,
                smile_score=payload.smileScore,
                head_yaw=payload.headYaw,
                head_pitch=payload.headPitch,
                head_roll=payload.headRoll,
                affect_state=payload.affectState,
            )
            db.add(sample)
            db.commit()
            return {"status": "success"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    # --- Hint CRUD (file-based) ---

    # Stats route must be registered BEFORE the generic {csq_name} routes to avoid shadowing.
    @router.get("/admin/hints/stats/{course}/{week}", dependencies=[Depends(require_admin)])
    async def hint_stats(course: str, week: str):
        course = safe_course(course); week = safe_week(week)
        hint_dir = os.path.join(HINT_STORE, course, week)
        if not os.path.isdir(hint_dir):
            return {"questions_with_hints": 0, "total_hints": 0}
        questions_with_hints = 0
        total_hints = 0
        for fname in os.listdir(hint_dir):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(hint_dir, fname)) as f:
                hints = json.load(f)
            if hints:
                questions_with_hints += 1
                total_hints += len(hints)
        return {"questions_with_hints": questions_with_hints, "total_hints": total_hints}

    # --- AI hint generation (RAG + Ollama) ---
    # All named POST routes MUST be registered before the generic POST /{csq_name} route.

    @router.post("/admin/hints/generate-all/{course}/{week}", dependencies=[Depends(require_admin)])
    async def generate_all_hints(course: str, week: str):
        course = safe_course(course); week = safe_week(week)
        questions = parse_questions(quiz_file_path(course, week))
        rag = RAGService.get_instance()
        ollama = OllamaClient()
        system = "You are a helpful tutor generating progressive hints. Respond with ONLY the hint text."
        generated, skipped, errors = 0, 0, []
        for q in questions:
            csq_name = q.get("csq_name", "")
            if not csq_name:
                continue
            if _load_hints(course, week, csq_name):
                skipped += 1
                continue
            question_text = _build_question_context(course, week, csq_name) or q.get("question_text", "")
            if not question_text:
                skipped += 1
                continue
            try:
                hints = []
                for level in range(1, 4):
                    similar_qa = rag.retrieve_similar(question_text, "qa_hints", n=3)
                    content_chunks = rag.retrieve_similar(question_text, "course_content", n=5)
                    prompt = rag.build_prompt(question_text, level, similar_qa, content_chunks)
                    hint = await ollama.generate(prompt, system=system)
                    if hint:
                        hints.append(hint)
                if hints:
                    _save_hints(course, week, csq_name, [
                        {"number": i + 1, "text": h} for i, h in enumerate(hints)
                    ])
                    generated += 1
                else:
                    errors.append({"csq_name": csq_name, "error": "no output from model"})
            except Exception as e:
                errors.append({"csq_name": csq_name, "error": str(e)})
        return {"generated": generated, "skipped": skipped, "errors": errors}

    @router.post("/admin/hints/generate/{course}/{week}/{csq_name}", dependencies=[Depends(require_admin)])
    @limiter.limit("30/minute")
    async def generate_hints(request: Request, course: str, week: str, csq_name: str, body: dict):
        course = safe_course(course); week = safe_week(week); csq_name = safe_qname(csq_name)
        question_text = _build_question_context(course, week, csq_name) or body.get("question_text", "")
        existing = _load_hints(course, week, csq_name)
        if existing:
            return {"hints": [h["text"] for h in existing]}
        try:
            rag = RAGService.get_instance()
            ollama = OllamaClient()
            hints = []
            for level in range(1, 4):
                similar_qa = rag.retrieve_similar(question_text, "qa_hints", n=3)
                content_chunks = rag.retrieve_similar(question_text, "course_content", n=5)
                prompt = rag.build_prompt(question_text, level, similar_qa, content_chunks)
                system = "You are a helpful tutor generating progressive hints. Respond with ONLY the hint text."
                hint = await ollama.generate(prompt, system=system)
                if hint:
                    hints.append(hint)
            if not hints:
                hints = [
                    "Review the relevant lecture material.",
                    "Try breaking the problem into smaller steps.",
                    "Check your assumptions about the core concept.",
                ]
            _save_hints(course, week, csq_name, [
                {"number": i + 1, "text": h} for i, h in enumerate(hints)
            ])
            return {"hints": hints}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hint generation failed: {e}")

    @router.post("/admin/hints/generate-single/{course}/{week}/{csq_name}", dependencies=[Depends(require_admin)])
    @limiter.limit("30/minute")
    async def generate_single_hint(request: Request, course: str, week: str, csq_name: str, body: dict):
        course = safe_course(course); week = safe_week(week); csq_name = safe_qname(csq_name)
        question_text = _build_question_context(course, week, csq_name) or body.get("question_text", "")
        hint_number = int(body.get("hint_number", 1))
        try:
            rag = RAGService.get_instance()
            ollama = OllamaClient()
            similar_qa = rag.retrieve_similar(question_text, "qa_hints", n=3)
            content_chunks = rag.retrieve_similar(question_text, "course_content", n=5)
            prompt = rag.build_prompt(question_text, hint_number, similar_qa, content_chunks)
            hint = await ollama.generate(prompt, system="You are a helpful tutor. Respond with ONLY the hint text.")
            if not hint:
                fallbacks = {
                    1: "Think about what concept this question is testing.",
                    2: "Review the relevant formulas in your notes.",
                    3: "Try working backwards from the answer format.",
                    4: "Consider the relationship between the given values.",
                    5: "Break down the problem: identify knowns, unknowns, and the connecting principle.",
                }
                hint = fallbacks.get(hint_number, fallbacks[1])
            return {"hint": hint}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hint generation failed: {e}")

    # Generic CRUD routes — must come AFTER all named routes above.
    # Read-only hints endpoint — student-facing (quiz JS fetches it). Auth required.
    @router.get("/admin/hints/{course}/{week}/{csq_name}")
    async def get_hints(course: str, week: str, csq_name: str, _user: dict = Depends(require_user)):
        course = safe_course(course); week = safe_week(week); csq_name = safe_qname(csq_name)
        return {"hints": _load_hints(course, week, csq_name)}

    @router.post("/admin/hints/{course}/{week}/{csq_name}", dependencies=[Depends(require_admin)])
    async def save_hints(course: str, week: str, csq_name: str, body: dict):
        course = safe_course(course); week = safe_week(week); csq_name = safe_qname(csq_name)
        hints_raw = body.get("hints", []) or []
        hints = [
            {"number": i + 1, "text": str(h)}
            for i, h in enumerate(hints_raw)
            if str(h).strip()
        ]
        _save_hints(course, week, csq_name, hints)
        return {"status": "success", "saved": len(hints)}

    @router.delete("/admin/hints/{course}/{week}/{csq_name}", dependencies=[Depends(require_admin)])
    async def delete_hints(course: str, week: str, csq_name: str):
        course = safe_course(course); week = safe_week(week); csq_name = safe_qname(csq_name)
        path = _hint_path(course, week, csq_name)
        if os.path.exists(path):
            os.remove(path)
        return {"status": "success"}

    return router
