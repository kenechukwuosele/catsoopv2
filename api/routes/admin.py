import os
import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..schemas import LiveFileResponse, LiveFileUpload
from ..config import ADMIN_HTML_PATH, CATSOOP_COURSES_DIR, LIVE_FILES_DIR, SERVER_BASE_URL
from ..templates import generate_native_quiz, generate_problems_template, generate_lecture_template, generate_live_file_panel, generate_quiz_template


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router() -> APIRouter:
    router = APIRouter()

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_panel():
        with open(ADMIN_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        return html.replace("__API_BASE__", SERVER_BASE_URL)

    @router.post("/admin/live-file")
    async def upload_live_file(payload: LiveFileUpload, db: Session = Depends(get_db)):
        os.makedirs(LIVE_FILES_DIR, exist_ok=True)
        course_dir = os.path.join(LIVE_FILES_DIR, payload.course)
        os.makedirs(course_dir, exist_ok=True)
        week_dir = os.path.join(course_dir, payload.week)
        os.makedirs(week_dir, exist_ok=True)
        stored_path = os.path.join(week_dir, payload.filename or "upload")
        try:
            raw = base64.b64decode(payload.data_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid file data: {str(e)}")
        with open(stored_path, "wb") as out:
            out.write(raw)
        now = datetime.now().isoformat()
        existing = db.query(models.LiveFile).filter(
            models.LiveFile.course == payload.course,
            models.LiveFile.week == payload.week
        ).first()
        if existing:
            existing.filename = payload.filename or "upload"
            existing.stored_path = stored_path
            existing.content_type = payload.content_type or "application/octet-stream"
            existing.uploaded_at = now
        else:
            db.add(models.LiveFile(
                course=payload.course,
                week=payload.week,
                filename=payload.filename or "upload",
                stored_path=stored_path,
                content_type=payload.content_type or "application/octet-stream",
                uploaded_at=now
            ))
        db.commit()
        return {"status": "success", "course": payload.course, "week": payload.week, "filename": payload.filename}

    @router.get("/admin/live-file/{course}/{week}", response_model=LiveFileResponse | None)
    async def get_live_file(course: str, week: str, db: Session = Depends(get_db)):
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course,
            models.LiveFile.week == week
        ).first()
        if not record:
            return None
        return {
            "course": record.course,
            "week": record.week,
            "filename": record.filename,
            "content_type": record.content_type,
            "uploaded_at": record.uploaded_at
        }

    @router.get("/live-file/{course}/{week}")
    async def download_live_file(course: str, week: str, download: bool = Query(False), db: Session = Depends(get_db)):
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course,
            models.LiveFile.week == week
        ).first()
        if not record or not os.path.exists(record.stored_path):
            raise HTTPException(status_code=404, detail="Live file not found")
        if download:
            return FileResponse(
                record.stored_path,
                media_type=record.content_type,
                headers={"Content-Disposition": f"attachment; filename=\"{record.filename}\""}
            )
        return FileResponse(
            record.stored_path,
            media_type=record.content_type,
            headers={"Content-Disposition": f"inline; filename=\"{record.filename}\""}
        )

    @router.post("/admin/repair")
    async def repair_courses(db: Session = Depends(get_db)):
        """Scan all courses/weeks, regenerate quiz.catsoop, problem files,
        and example_questions.catsoop from DB."""
        if not os.path.exists(CATSOOP_COURSES_DIR):
            raise HTTPException(status_code=404, detail="Courses directory not found")
        report = {"courses": {}, "total_quiz_regenerated": 0, "total_quiz_placeholder": 0, "total_example_questions": 0}
        for course_id in os.listdir(CATSOOP_COURSES_DIR):
            course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
            if not os.path.isdir(course_path) or course_id.startswith("_"):
                continue
            report["courses"][course_id] = {"weeks": {}}
            for week_id in os.listdir(course_path):
                week_path = os.path.join(course_path, week_id)
                if not os.path.isdir(week_path) or week_id.startswith("_"):
                    continue
                week_report = {"quiz": False, "example_questions": False}

                # Read title from __INFO__.py
                title = week_id
                info_path = os.path.join(week_path, "__INFO__.py")
                if os.path.exists(info_path):
                    with open(info_path) as f:
                        for line in f:
                            if "cs_long_name" in line:
                                title = line.split("=")[-1].strip().strip('"').strip("'")

                # Regenerate example_questions.catsoop for every week
                example_path = os.path.join(week_path, "example_questions.catsoop")
                with open(example_path, "w", encoding="utf-8") as f:
                    f.write(generate_quiz_template(course_id, week_id))
                week_report["example_questions"] = True
                report["total_example_questions"] += 1

                # Regenerate quiz.catsoop from DB questions if they exist,
                # otherwise write a placeholder
                quiz_path = os.path.join(week_path, "quiz.catsoop")
                questions = db.query(models.Question).filter(
                    models.Question.course == course_id,
                    models.Question.week == week_id
                ).all()
                if questions:
                    with open(quiz_path, "w", encoding="utf-8") as f:
                        f.write(generate_native_quiz(course_id, week_id, questions))
                    week_report["quiz"] = True
                    report["total_quiz_regenerated"] += 1
                else:
                    with open(quiz_path, "w") as f:
                        f.write(f'''<python>
cs_content_header = "{title} Quiz"
cs_show_due = True
</python>

<p>No questions published yet. The instructor will publish the quiz soon.</p>
''')
                    report["total_quiz_placeholder"] += 1

                report["courses"][course_id]["weeks"][week_id] = week_report

        return report

    return router
