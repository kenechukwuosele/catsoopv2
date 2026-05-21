from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..schemas import HintCreate, HintGenerate, BulkImportRequest, EngagementSampleCreate
from ..services.rag_service import RAGService
from ..services.ollama_client import OllamaClient


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router() -> APIRouter:
    router = APIRouter()

    # --- Engagement samples ---
    @router.post("/{course}/{week}/engagement")
    async def log_engagement(course: str, week: str, payload: EngagementSampleCreate, db: Session = Depends(get_db)):
        try:
            sample = models.EngagementSample(
                attempt_id=None,
                attempt_session_id=payload.attemptSessionId,
                username=payload.username,
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

    # --- Questions with hints ---
    @router.get("/admin/questions/{course}/{week}/with-hints")
    async def get_questions_with_hints(course: str, week: str, db: Session = Depends(get_db)):
        try:
            questions = db.query(models.Question).filter(
                models.Question.course == course,
                models.Question.week == week
            ).all()
            result = []
            for q in questions:
                hints = db.query(models.Hint).filter(
                    models.Hint.question_id == q.id
                ).order_by(models.Hint.hint_number).all()
                result.append({
                    "id": q.id,
                    "text": q.question_text,
                    "qtype": q.question_type,
                    "options": q.options,
                    "correct_answers": q.correct_answers,
                    "username": q.username,
                    "course": q.course,
                    "week": q.week,
                    "created_at": q.created_at,
                    "hints": [{"number": h.hint_number, "text": h.hint_text} for h in hints]
                })
            return {"questions": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/admin/questions-with-hints")
    async def bulk_import_questions(data: BulkImportRequest, db: Session = Depends(get_db)):
        try:
            for q in data.questions:
                db_question = models.Question(
                    question_text=q.text,
                    question_type=q.type,
                    options=q.options,
                    correct_answers=q.correct_answers,
                    username="import",
                    course=data.course,
                    week=data.week,
                    created_at=datetime.now().isoformat()
                )
                db.add(db_question)
                db.flush()
                if q.hints:
                    for i, hint_text in enumerate(q.hints):
                        db.add(models.Hint(
                            question_id=db_question.id,
                            hint_number=i + 1,
                            hint_text=hint_text
                        ))
            db.commit()
            return {"status": "success", "imported": len(data.questions)}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/admin/questions/{course}/{week}")
    async def delete_all_questions(course: str, week: str, db: Session = Depends(get_db)):
        try:
            questions = db.query(models.Question).filter(
                models.Question.course == course,
                models.Question.week == week
            ).all()
            q_ids = [q.id for q in questions]
            db.query(models.Hint).filter(models.Hint.question_id.in_(q_ids)).delete(synchronize_session=False)
            for q in questions:
                db.delete(q)
            db.commit()
            return {"status": "success", "deleted": len(questions)}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    # --- Hint CRUD ---
    @router.post("/admin/hints")
    async def save_hints(hint_data: HintCreate, db: Session = Depends(get_db)):
        db.query(models.Hint).filter(models.Hint.question_id == hint_data.question_id).delete()
        for i, ht in enumerate(hint_data.hints):
            db.add(models.Hint(question_id=hint_data.question_id, hint_number=i+1, hint_text=ht))
        db.commit()
        return {"status": "success"}

    @router.get("/admin/hints/stats")
    async def get_hint_stats(db: Session = Depends(get_db)):
        questions_with_hints = db.query(models.Hint.question_id).distinct().count()
        total_hints = db.query(models.Hint).count()
        attempts = db.query(models.Attempt).all()
        total_hint_usage = sum(a.hint_count or 0 for a in attempts)
        avg_hints = total_hint_usage / len(attempts) if attempts else 0
        low_score_with_hints = sum(
            1 for a in attempts
            if (a.hint_count or 0) > 0 and (a.score / a.total if a.total > 0 else 0) < 0.5
        )
        return {
            "questions_with_hints": questions_with_hints,
            "total_hints": total_hints,
            "avg_hints_per_attempt": round(avg_hints, 1),
            "low_score_with_hints": low_score_with_hints
        }

    @router.post("/admin/hints/generate")
    async def generate_hints(data: HintGenerate, db: Session = Depends(get_db)):
        existing = db.query(models.Hint).filter(models.Hint.question_id == data.question_id).all()
        if existing:
            return {"hints": [h.hint_text for h in sorted(existing, key=lambda x: x.hint_number)]}
        try:
            rag = RAGService.get_instance()
            ollama = OllamaClient()
            hints = []
            for level in range(1, 4):
                similar_qa = rag.retrieve_similar(data.question_text, "qa_hints", n=3)
                content_chunks = rag.retrieve_similar(data.question_text, "course_content", n=5)
                prompt = rag.build_prompt(data.question_text, level, similar_qa, content_chunks)
                system = "You are a helpful tutor generating progressive hints. Respond with ONLY the hint text."
                hint = await ollama.generate(prompt, system=system)
                if hint:
                    hints.append(hint)
                    db.add(models.Hint(question_id=data.question_id, hint_number=level, hint_text=hint))
            if not hints:
                hints = ["Review the relevant lecture material.", "Try breaking the problem into smaller steps.", "Check your assumptions about the core concept."]
                for i, ht in enumerate(hints):
                    db.add(models.Hint(question_id=data.question_id, hint_number=i+1, hint_text=ht))
            db.commit()
            return {"hints": hints}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"RAG hint generation failed: {str(e)}")

    @router.post("/admin/hints/generate-single")
    async def generate_single_hint(data: dict, db: Session = Depends(get_db)):
        question_id = data.get("question_id")
        question_text = data.get("question_text", "")
        hint_number = data.get("hint_number", 1)
        if not question_id:
            raise HTTPException(status_code=400, detail="question_id required")
        try:
            rag = RAGService.get_instance()
            ollama = OllamaClient()
            similar_qa = rag.retrieve_similar(question_text, "qa_hints", n=3)
            content_chunks = rag.retrieve_similar(question_text, "course_content", n=5)
            prompt = rag.build_prompt(question_text, hint_number, similar_qa, content_chunks)
            system = "You are a helpful tutor. Respond with ONLY the hint text, no markdown or JSON."
            hint = await ollama.generate(prompt, system=system)
            if not hint:
                hint_levels = {1: "Think about what concept this question is testing.", 2: "Review the relevant formulas in your notes.", 3: "Try working backwards from the answer format.", 4: "Consider the relationship between the given values.", 5: "Break down the problem: identify knowns, unknowns, and the connecting principle."}
                hint = hint_levels.get(hint_number, hint_levels[1])
            return {"hint": hint}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG hint generation failed: {str(e)}")

    @router.get("/admin/hints/{question_id}")
    async def get_hints(question_id: int, db: Session = Depends(get_db)):
        hints = db.query(models.Hint).filter(
            models.Hint.question_id == question_id
        ).order_by(models.Hint.hint_number).all()
        return {"hints": [{"number": h.hint_number, "text": h.hint_text} for h in hints]}

    @router.delete("/admin/hints/{question_id}")
    async def delete_hints(question_id: int, db: Session = Depends(get_db)):
        db.query(models.Hint).filter(models.Hint.question_id == question_id).delete()
        db.commit()
        return {"status": "success", "message": "Hints deleted"}

    return router
