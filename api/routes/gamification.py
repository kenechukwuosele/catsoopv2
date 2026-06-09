import os
import math
import json
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import List

from ..database import SessionLocal
from .. import models
from ..auth import require_user, require_admin
from ..validation import safe_course, safe_week
from ..config import CATSOOP_COURSES_DIR
from .file_questions import _read_all_cslog
from ..services.gamification import award_xp, update_streak_only, BADGE_META
from ..limiter import limiter

DATA_ROOT = os.path.dirname(CATSOOP_COURSES_DIR)
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class QuizCompleteRequest(BaseModel):
    username: str | None = None  # ignored — identity comes from the token


class EnrollFaceRequest(BaseModel):
    descriptor: List[float]


class VerifyFaceRequest(BaseModel):
    descriptor: List[float]


def _get_percent_from_cslog(course: str, username: str, week: str) -> float:
    log_base = os.path.join(DATA_ROOT, "_logs", "_courses")
    user_dir = os.path.join(log_base, course, username)
    entries: list = []
    for sub in [os.path.join(week, "quiz"), week]:
        path = os.path.join(user_dir, sub, "problemactions.log")
        entries = _read_all_cslog(path)
        if entries:
            break

    q_scores: dict = {}
    q_times: dict = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("action") != "submit":
            continue
        ts = entry.get("timestamp", "")
        for name, raw in (entry.get("scores") or {}).items():
            try:
                score = float(raw or 0)
            except Exception:
                score = 0.0
            if name not in q_times or ts > q_times[name]:
                q_scores[name] = score
                q_times[name] = ts

    if not q_scores:
        return 0.0
    return sum(q_scores.values()) / len(q_scores)


def _euclidean_distance(a: list, b: list) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def get_router() -> APIRouter:
    router = APIRouter()

    # ------------------------------------------------------------------
    # Public lecturer check (used by gradebook template)
    # ------------------------------------------------------------------

    @router.get("/{course}/is-lecturer")
    def check_is_lecturer(course: str, username: str, db: Session = Depends(get_db)):
        course = safe_course(course)
        admins = {u.strip() for u in os.environ.get("CU_QUIZ_ADMINS", "").split(",") if u.strip()}
        if username in admins:
            return {"is_lecturer": True}
        lec = db.query(models.Lecturer).filter_by(username=username).first()
        if lec:
            import json as _j
            courses = _j.loads(lec.courses or "[]")
            if course in courses:
                return {"is_lecturer": True}
        return {"is_lecturer": False}

    # ------------------------------------------------------------------
    # Quiz completion — gamification trigger
    # ------------------------------------------------------------------

    @router.post("/{course}/{week}/quiz-complete")
    @limiter.limit("5/minute")
    async def quiz_complete(request: Request, course: str, week: str, body: QuizCompleteRequest,
                            db: Session = Depends(get_db),
                            user: dict = Depends(require_user)):
        course = safe_course(course); week = safe_week(week)
        username = user["username"]

        # Insert dedup row first; unique constraint rejects duplicates
        event = models.ProcessedQuizEvent(
            username=username, course=course, week=week,
            processed_at=datetime.utcnow().isoformat(), xp_awarded=0
        )
        db.add(event)
        try:
            db.flush()
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info("quiz-complete: duplicate for %s %s/%s", username, course, week)
            streak_result = update_streak_only(db, username, course)
            return {"status": "already_processed", **streak_result}

        # Wait for CatSooP to flush the submission to cslog
        await asyncio.sleep(1.5)
        percent_correct = _get_percent_from_cslog(course, username, week)

        if percent_correct == 0.0:
            # One retry — cslog write can be slow
            await asyncio.sleep(1.0)
            percent_correct = _get_percent_from_cslog(course, username, week)

        logger.info("quiz-complete: %s %s/%s → %.1f%%", username, course, week, percent_correct * 100)

        result = award_xp(db, username, course, percent_correct)

        db.query(models.ProcessedQuizEvent).filter_by(
            username=username, course=course, week=week
        ).update({"xp_awarded": result["xp_awarded"]})
        db.commit()

        return {"status": "ok", **result}

    # ------------------------------------------------------------------
    # Leaderboard & stats
    # ------------------------------------------------------------------

    @router.get("/{course}/leaderboard")
    def leaderboard(course: str, db: Session = Depends(get_db)):
        course = safe_course(course)
        profiles = (
            db.query(models.StudentProfile)
            .filter_by(course=course)
            .order_by(models.StudentProfile.xp.desc())
            .all()
        )
        rows = []
        for rank, p in enumerate(profiles, 1):
            badge_count = db.query(models.Badge).filter_by(username=p.username, course=course).count()
            rows.append({
                "rank": rank,
                "username": p.username,
                "xp": p.xp,
                "streak": p.streak,
                "badges": badge_count,
            })
        return {"leaderboard": rows}

    @router.get("/{course}/my-stats")
    def my_stats(course: str, username: str, db: Session = Depends(get_db)):
        course = safe_course(course)
        profile = db.query(models.StudentProfile).filter_by(username=username, course=course).first()
        if not profile:
            return {"username": username, "course": course, "xp": 0, "streak": 0, "rank": None, "badges": []}

        rank = (
            db.query(models.StudentProfile)
            .filter(models.StudentProfile.course == course, models.StudentProfile.xp > profile.xp)
            .count()
        ) + 1

        badges = db.query(models.Badge).filter_by(username=username, course=course).all()
        badge_list = [
            {
                "type": b.badge_type,
                "label": BADGE_META.get(b.badge_type, {}).get("label", b.badge_type),
                "icon": BADGE_META.get(b.badge_type, {}).get("icon", "🏅"),
                "earned_at": b.earned_at,
            }
            for b in badges
        ]

        return {
            "username": username,
            "course": course,
            "xp": profile.xp,
            "streak": profile.streak,
            "rank": rank,
            "badges": badge_list,
        }

    # ------------------------------------------------------------------
    # Face authentication
    # ------------------------------------------------------------------

    @router.get("/{course}/face-status")
    def face_status(course: str, username: str, db: Session = Depends(get_db),
                    user: dict = Depends(require_user)):
        course = safe_course(course)
        if not user["is_admin"] and username != user["username"]:
            raise HTTPException(status_code=403, detail="Cannot query another user's face status")
        enrolled = db.query(models.FaceEnrollment).filter_by(username=username).first() is not None
        return {"enrolled": enrolled}

    @router.post("/{course}/enroll-face")
    def enroll_face(course: str, body: EnrollFaceRequest, db: Session = Depends(get_db),
                    user: dict = Depends(require_user)):
        course = safe_course(course)
        if len(body.descriptor) != 128:
            raise HTTPException(status_code=400, detail="128-dim descriptor required")
        username = user["username"]

        existing = db.query(models.FaceEnrollment).filter_by(username=username).first()
        if existing:
            raise HTTPException(status_code=409, detail="Already enrolled. Ask your instructor to reset your face ID.")
        db.add(models.FaceEnrollment(
            username=username,
            descriptor=json.dumps(body.descriptor),
            enrolled_at=datetime.utcnow().isoformat(),
        ))
        db.commit()
        return {"status": "enrolled"}

    @router.post("/{course}/verify-face")
    @limiter.limit("10/minute")
    def verify_face(request: Request, course: str, body: VerifyFaceRequest, db: Session = Depends(get_db),
                    user: dict = Depends(require_user)):
        course = safe_course(course)
        if len(body.descriptor) != 128:
            raise HTTPException(status_code=400, detail="128-dim descriptor required")
        username = user["username"]
        enrollment = db.query(models.FaceEnrollment).filter_by(username=username).first()
        if not enrollment:
            return {"verified": False, "distance": None, "reason": "not_enrolled"}

        stored = json.loads(enrollment.descriptor)
        distance = _euclidean_distance(body.descriptor, stored)
        verified = distance < 0.4
        return {"verified": verified, "distance": round(distance, 4)}

    return router
