import os
import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import require_admin
from ..validation import safe_course, safe_week, safe_filename, ensure_within
from ..schemas import LiveFileResponse, LiveFileUpload
from ..config import LIVE_FILES_DIR

_ALLOWED_UPLOAD_MIME = {
    "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "text/plain", "text/markdown", "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/octet-stream",
}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router():
    router = APIRouter()

    @router.post("/admin/live-file", dependencies=[Depends(require_admin)])
    async def upload_live_file(payload: LiveFileUpload, db: Session = Depends(get_db)):
        course = safe_course(payload.course)
        week = safe_week(payload.week)
        fname = safe_filename(payload.filename or "upload")

        ctype = payload.content_type or "application/octet-stream"
        if ctype not in _ALLOWED_UPLOAD_MIME:
            raise HTTPException(status_code=415, detail=f"Unsupported content type: {ctype}")

        os.makedirs(LIVE_FILES_DIR, exist_ok=True)
        course_dir = os.path.join(LIVE_FILES_DIR, course)
        os.makedirs(course_dir, exist_ok=True)
        week_dir = os.path.join(course_dir, week)
        os.makedirs(week_dir, exist_ok=True)
        stored_path = os.path.join(week_dir, fname)
        ensure_within(LIVE_FILES_DIR, stored_path)

        try:
            raw = base64.b64decode(payload.data_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid file data: {str(e)}")
        if len(raw) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

        with open(stored_path, "wb") as out:
            out.write(raw)
        now = datetime.now().isoformat()
        existing = db.query(models.LiveFile).filter(
            models.LiveFile.course == course,
            models.LiveFile.week == week
        ).first()
        if existing:
            existing.filename = fname
            existing.stored_path = stored_path
            existing.content_type = ctype
            existing.uploaded_at = now
        else:
            db.add(models.LiveFile(
                course=course, week=week, filename=fname,
                stored_path=stored_path, content_type=ctype, uploaded_at=now,
            ))
        db.commit()
        return {"status": "success", "course": course, "week": week, "filename": fname}

    @router.get("/admin/live-file/{course}/{week}", response_model=LiveFileResponse | None,
                dependencies=[Depends(require_admin)])
    async def get_live_file(course: str, week: str, db: Session = Depends(get_db)):
        course = safe_course(course)
        week = safe_week(week)
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course, models.LiveFile.week == week
        ).first()
        if not record:
            return None
        return {
            "course": record.course, "week": record.week, "filename": record.filename,
            "content_type": record.content_type, "uploaded_at": record.uploaded_at,
        }

    @router.get("/live-file-info/{course}/{week}")
    async def get_live_file_info(course: str, week: str, db: Session = Depends(get_db)):
        course = safe_course(course)
        week = safe_week(week)
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course, models.LiveFile.week == week
        ).first()
        if not record:
            return None
        return {"filename": record.filename, "content_type": record.content_type}

    @router.get("/live-file/{course}/{week}")
    async def download_live_file(course: str, week: str, download: bool = Query(False),
                                 db: Session = Depends(get_db)):
        course = safe_course(course)
        week = safe_week(week)
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course, models.LiveFile.week == week
        ).first()
        if not record or not os.path.exists(record.stored_path):
            raise HTTPException(status_code=404, detail="Live file not found")
        ensure_within(LIVE_FILES_DIR, record.stored_path)
        disposition = "attachment" if download else "inline"
        return FileResponse(
            record.stored_path,
            media_type=record.content_type,
            headers={"Content-Disposition": f'{disposition}; filename="{safe_filename(record.filename)}"'},
        )

    @router.delete("/admin/live-file/{course}/{week}", dependencies=[Depends(require_admin)])
    async def delete_live_file(course: str, week: str, db: Session = Depends(get_db)):
        course = safe_course(course)
        week = safe_week(week)
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course,
            models.LiveFile.week == week
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="No live file for this course/week")
        try:
            if os.path.exists(record.stored_path):
                os.unlink(record.stored_path)
        except Exception:
            pass
        db.delete(record)
        db.commit()
        return {"status": "deleted"}

    return router
