import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..schemas import QuestionResponse, AttemptSubmission
from ..templates import generate_native_quiz
from ..config import CATSOOP_COURSES_DIR


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router() -> APIRouter:
    router = APIRouter()

    @router.get("/{course}/{week}/example_questions", response_model=list[QuestionResponse])
    async def get_all_questions(course: str, week: str, db: Session = Depends(get_db)):
        try:
            questions = db.query(models.Question).filter(
                models.Question.course == course,
                models.Question.week == week
            ).all()
            return [
                {
                    "id": q.id,
                    "text": q.question_text,
                    "qtype": q.question_type,
                    "options": q.options,
                    "correct_answers": q.correct_answers,
                    "username": q.username,
                    "course": q.course,
                    "week": q.week,
                    "created_at": q.created_at
                }
                for q in questions
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/{course}/{week}/example_questions")
    async def handle_question(course: str, week: str, request: Request):
        request_data = await request.json()
        correct_ans = request_data.get('correctAnswers') or request_data.get('correct_answers')

        if not all(k in request_data for k in ['username', 'text', 'type']) or correct_ans is None:
            raise HTTPException(status_code=400, detail="Missing required fields")

        db = SessionLocal()
        try:
            db_question = models.Question(
                question_text=request_data['text'],
                question_type=request_data['type'],
                options=request_data.get('options', []),
                correct_answers=correct_ans,
                username=request_data['username'],
                course=course,
                week=week,
                created_at=datetime.now().isoformat()
            )
            db.add(db_question)
            db.commit()
            db.refresh(db_question)
            hints = request_data.get('hints', [])
            if hints:
                for i, ht in enumerate(hints):
                    db.add(models.Hint(question_id=db_question.id, hint_number=i+1, hint_text=ht))
                db.commit()
            return {"status": "success", "question_id": db_question.id}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            db.close()

    @router.delete("/{course}/{week}/example_questions/{question_id}")
    async def delete_question(course: str, week: str, question_id: int, db: Session = Depends(get_db)):
        question = db.query(models.Question).filter(
            models.Question.id == question_id,
            models.Question.course == course,
            models.Question.week == week
        ).first()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        db.delete(question)
        db.commit()
        return {"status": "success", "message": "Deleted"}

    @router.post("/{course}/{week}/submit_attempt")
    async def submit_attempt(course: str, week: str, attempt_data: AttemptSubmission, db: Session = Depends(get_db)):
        try:
            db_attempt = models.Attempt(
                username=attempt_data.username,
                score=attempt_data.score,
                total=attempt_data.total,
                course=course,
                week=week,
                results=attempt_data.results,
                seconds_spent=attempt_data.metrics.secondsSpent,
                click_count=attempt_data.metrics.clickCount,
                hint_count=attempt_data.metrics.hintCount,
                submitted_at=datetime.now().isoformat(),
                attempt_session_id=attempt_data.attemptSessionId
            )
            db.add(db_attempt)
            db.commit()
            return {"status": "success", "message": "Attempt and metrics saved"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/admin/publish-quiz/{course}/{week}")
    async def publish_quiz(course: str, week: str, db: Session = Depends(get_db)):
        """Read SQLite questions, generate native .catsoop, write to courses dir."""
        questions = db.query(models.Question).filter(
            models.Question.course == course,
            models.Question.week == week
        ).all()
        if not questions:
            raise HTTPException(status_code=400, detail="No questions found for this course/week")

        content = generate_native_quiz(course, week, questions)
        quiz_path = os.path.join(CATSOOP_COURSES_DIR, course, week, "quiz.catsoop")
        os.makedirs(os.path.dirname(quiz_path), exist_ok=True)
        with open(quiz_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "path": quiz_path, "question_count": len(questions)}

    @router.get("/{course}/{week}/all_attempts")
    async def get_all_attempts(course: str, week: str, db: Session = Depends(get_db)):
        try:
            attempts = db.query(models.Attempt).filter(
                models.Attempt.course == course,
                models.Attempt.week == week
            ).order_by(models.Attempt.submitted_at.desc()).all()
            return {"attempts": [
                {
                    "id": a.id,
                    "username": a.username,
                    "course": a.course,
                    "week": a.week,
                    "score": a.score,
                    "total": a.total,
                    "results": a.results,
                    "seconds_spent": a.seconds_spent,
                    "click_count": a.click_count,
                    "hint_count": a.hint_count,
                    "submitted_at": a.submitted_at,
                }
                for a in attempts
            ]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
