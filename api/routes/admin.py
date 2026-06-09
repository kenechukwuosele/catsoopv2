import os
import json
import base64
import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import require_admin, require_user, verify_admin_password, mint_token, ADMIN_PASSWORD
from ..validation import safe_course, safe_week, safe_filename, ensure_within
from ..schemas import LiveFileResponse, LiveFileUpload
from ..config import ADMIN_HTML_PATH, CATSOOP_COURSES_DIR, LIVE_FILES_DIR, SERVER_BASE_URL
from ..templates import generate_native_quiz, generate_problems_template, generate_lecture_template, generate_live_file_panel, generate_quiz_template, generate_gradebook_template


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
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AdminLoginRequest(BaseModel):
    username: str = ""
    password: str


def _read_catsoop_logininfo(username: str) -> dict:
    """Read CatSooP _logininfo for a user from its binary log file."""
    import struct, pickle, lzma
    log_path = os.path.join(os.path.dirname(CATSOOP_COURSES_DIR), "_logs", "_logininfo", f"{username}.log")
    if not os.path.exists(log_path):
        return {}
    try:
        with open(log_path, "rb") as f:
            data = f.read()
        pos, last = 0, {}
        while pos + 8 <= len(data):
            length = struct.unpack("<Q", data[pos:pos+8])[0]
            if pos + 8 + length + 8 > len(data):
                break
            entry_data = data[pos+8:pos+8+length]
            pos = pos + 8 + length + 8
            try:
                try:
                    last = pickle.loads(lzma.decompress(entry_data))
                except Exception:
                    last = pickle.loads(entry_data)
            except Exception:
                pass
        return last
    except Exception:
        return {}


def _verify_catsoop_instructor(username: str, password: str) -> dict | None:
    """Verify plaintext password against CatSooP _logininfo for an Instructor-role user."""
    import hashlib
    info = _read_catsoop_logininfo(username)
    if not info or not info.get("confirmed", False) or info.get("role", "") != "Instructor":
        return None
    client_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        (password + username).encode("utf-8"),
        100000, dklen=32,
    ).hex()
    stored_hash = info.get("password_hash")
    stored_salt = info.get("password_salt")
    if not stored_hash or stored_salt is None:
        return None
    computed = hashlib.pbkdf2_hmac(
        "sha512",
        client_hash.encode("utf-8"),
        stored_salt if isinstance(stored_salt, bytes) else stored_salt.encode("utf-8"),
        500000,
    )
    return info if computed == stored_hash else None


def get_router() -> APIRouter:
    router = APIRouter()

    # --- Auth ---

    @router.post("/admin/login")
    def admin_login(body: AdminLoginRequest, db: Session = Depends(get_db)):
        # System admin check (username omitted or blank)
        if not body.username or body.username.strip() in ("", "__admin__", "admin"):
            if verify_admin_password(body.password):
                token = mint_token(username="__admin__", is_admin=True)
                return {"token": token, "role": "admin", "username": "__admin__", "name": "Admin", "courses": []}
        # Lecturer DB check
        from .lecturer import _verify_lecturer_password, _mint_lecturer_token
        uname = body.username.strip()
        lec = db.query(models.Lecturer).filter_by(username=uname).first()
        if lec and _verify_lecturer_password(lec.password_hash, body.password):
            courses = json.loads(lec.courses or "[]")
            token = _mint_lecturer_token(lec.username, courses)
            return {"token": token, "role": "lecturer", "username": lec.username, "name": lec.name, "courses": courses}
        # CatSooP Instructor check (registered via CatSooP login page with "Instructor" role)
        cs_info = _verify_catsoop_instructor(uname, body.password)
        if cs_info:
            token = mint_token(username=uname, is_admin=True)
            return {
                "token": token, "role": "instructor", "username": uname,
                "name": cs_info.get("name", uname), "courses": [],
            }
        raise HTTPException(status_code=401, detail="Invalid credentials")

    @router.get("/admin/auto-token")
    def admin_auto_token():
        """Issue an admin token with no credentials.
        Only works when CU_QUIZ_ADMIN_PASSWORD is unset (network-trust mode).
        Set CU_QUIZ_ADMIN_PASSWORD to require a password and disable this."""
        if ADMIN_PASSWORD:
            raise HTTPException(status_code=403, detail="Password auth required")
        return {"token": mint_token(username="__admin__", is_admin=True), "role": "admin",
                "username": "__admin__", "name": "Admin", "courses": []}

    # GET /admin serves the HTML shell — login is now handled client-side.
    @router.get("/admin", response_class=HTMLResponse)
    async def admin_panel():
        with open(ADMIN_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        html = html.replace("__API_BASE__", SERVER_BASE_URL)
        return html

    # --- Live files (admin) ---

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

    # Student-accessible download (still validates path)
    @router.get("/live-file/{course}/{week}")
    async def download_live_file(course: str, week: str, download: bool = Query(False),
                                 db: Session = Depends(get_db), _user: dict = Depends(require_user)):
        course = safe_course(course)
        week = safe_week(week)
        record = db.query(models.LiveFile).filter(
            models.LiveFile.course == course, models.LiveFile.week == week
        ).first()
        if not record or not os.path.exists(record.stored_path):
            raise HTTPException(status_code=404, detail="Live file not found")
        # Defense in depth: confirm stored_path is still inside LIVE_FILES_DIR
        ensure_within(LIVE_FILES_DIR, record.stored_path)
        disposition = "attachment" if download else "inline"
        return FileResponse(
            record.stored_path,
            media_type=record.content_type,
            headers={"Content-Disposition": f'{disposition}; filename="{safe_filename(record.filename)}"'},
        )

    # --- Repair (admin) ---

    @router.post("/admin/repair", dependencies=[Depends(require_admin)])
    async def repair_courses():
        from ..routes.file_questions import parse_questions, quiz_file_path, _read_time_limit

        if not os.path.exists(CATSOOP_COURSES_DIR):
            raise HTTPException(status_code=404, detail="Courses directory not found")
        report = {"courses": {}, "total_example_questions": 0, "total_quiz_regenerated": 0}
        for course_id in os.listdir(CATSOOP_COURSES_DIR):
            course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
            if not os.path.isdir(course_path) or course_id.startswith("_"):
                continue
            report["courses"][course_id] = {"weeks": {}}
            for week_id in os.listdir(course_path):
                week_path = os.path.join(course_path, week_id)
                if not os.path.isdir(week_path) or week_id.startswith("_"):
                    continue
                week_report = {"example_questions": False, "quiz_regenerated": False, "quiz_questions": 0}

                example_path = os.path.join(week_path, "example_questions.catsoop")
                with open(example_path, "w", encoding="utf-8") as f:
                    f.write(generate_quiz_template(course_id, week_id))
                week_report["example_questions"] = True
                report["total_example_questions"] += 1

                qpath = quiz_file_path(course_id, week_id)
                if os.path.exists(qpath):
                    questions = parse_questions(qpath)
                    time_limit = _read_time_limit(week_path)
                    with open(qpath, "w", encoding="utf-8") as f:
                        f.write(generate_native_quiz(course_id, week_id, questions, time_limit))
                    week_report["quiz_questions"] = len(questions)
                    week_report["quiz_regenerated"] = True
                    report["total_quiz_regenerated"] += 1

                report["courses"][course_id]["weeks"][week_id] = week_report

        from ..templates import generate_leaderboard_widget, LEADERBOARD_SENTINEL
        leaderboards_updated = 0
        for course_id in os.listdir(CATSOOP_COURSES_DIR):
            course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
            if not os.path.isdir(course_path) or course_id.startswith("_"):
                continue
            cc_path = os.path.join(course_path, "content.catsoop")
            if not os.path.exists(cc_path):
                continue
            with open(cc_path, "r", encoding="utf-8") as f:
                cc = f.read()
            if LEADERBOARD_SENTINEL in cc:
                cc = cc[:cc.index(LEADERBOARD_SENTINEL)] + generate_leaderboard_widget(course_id)
            else:
                cc += generate_leaderboard_widget(course_id)
            with open(cc_path, "w", encoding="utf-8") as f:
                f.write(cc)
            leaderboards_updated += 1
        report["leaderboards_updated"] = leaderboards_updated

        gradebooks_updated = 0
        for course_id in os.listdir(CATSOOP_COURSES_DIR):
            course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
            if not os.path.isdir(course_path) or course_id.startswith("_"):
                continue
            gb_path = os.path.join(course_path, "gradebook.catsoop")
            with open(gb_path, "w", encoding="utf-8") as f:
                f.write(generate_gradebook_template(course_id))
            gradebooks_updated += 1
        report["gradebooks_updated"] = gradebooks_updated

        return report

    @router.get("/admin/face-enrollments", dependencies=[Depends(require_admin)])
    def list_face_enrollments(db: Session = Depends(get_db)):
        rows = db.query(models.FaceEnrollment).order_by(models.FaceEnrollment.enrolled_at.desc()).all()
        return {"enrollments": [{"username": r.username, "enrolled_at": r.enrolled_at} for r in rows]}

    @router.delete("/admin/face-enrollments/{username}", dependencies=[Depends(require_admin)])
    def delete_face_enrollment(username: str, db: Session = Depends(get_db)):
        deleted = db.query(models.FaceEnrollment).filter_by(username=username).delete()
        db.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail="Not found")
        return {"status": "deleted"}

    # ── Lecturer management ──────────────────────────────────────────────────

    class LecturerCreate(BaseModel):
        username: str
        name: str
        email: str = ""
        password: str
        courses: list = []

    def _hash_password(pw: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + pw).encode()).hexdigest()
        return f"{salt}:{h}"

    @router.get("/admin/lecturers", dependencies=[Depends(require_admin)])
    def list_lecturers(db: Session = Depends(get_db)):
        rows = db.query(models.Lecturer).order_by(models.Lecturer.registered_at.desc()).all()
        return {"lecturers": [
            {"username": r.username, "name": r.name, "email": r.email or "",
             "courses": json.loads(r.courses or "[]"),
             "registered_at": r.registered_at}
            for r in rows
        ]}

    @router.post("/admin/lecturers", dependencies=[Depends(require_admin)])
    def create_lecturer(body: LecturerCreate, db: Session = Depends(get_db)):
        from ..validation import safe_course as _sc
        username = body.username.strip()
        if not username or len(username) > 64:
            raise HTTPException(status_code=422, detail="Invalid username")
        if db.query(models.Lecturer).filter_by(username=username).first():
            raise HTTPException(status_code=409, detail="Username already registered")
        validated_courses = []
        for c in body.courses:
            try: validated_courses.append(_sc(c))
            except Exception: pass
        db.add(models.Lecturer(
            username=username,
            name=body.name.strip()[:200],
            email=body.email.strip()[:200],
            password_hash=_hash_password(body.password),
            courses=json.dumps(validated_courses),
            registered_at=datetime.utcnow().isoformat(),
        ))
        db.commit()
        return {"status": "registered", "username": username}

    @router.delete("/admin/lecturers/{username}", dependencies=[Depends(require_admin)])
    def delete_lecturer(username: str, db: Session = Depends(get_db)):
        deleted = db.query(models.Lecturer).filter_by(username=username).delete()
        db.commit()
        if not deleted:
            raise HTTPException(status_code=404, detail="Not found")
        return {"status": "deleted"}

    @router.post("/admin/sync-instructors", dependencies=[Depends(require_admin)])
    def sync_catsoop_instructors(db: Session = Depends(get_db)):
        logininfo_dir = os.path.join(os.path.dirname(CATSOOP_COURSES_DIR), "_logs", "_logininfo")
        if not os.path.exists(logininfo_dir):
            return {"synced": 0, "already_exist": 0, "total_found": 0, "synced_usernames": []}
        synced, already_exist, total_found = [], [], []
        for fname in sorted(os.listdir(logininfo_dir)):
            if not fname.endswith(".log"):
                continue
            username = fname[:-4]
            info = _read_catsoop_logininfo(username)
            if not info or not info.get("confirmed", False) or info.get("role", "") != "Instructor":
                continue
            total_found.append(username)
            if db.query(models.Lecturer).filter_by(username=username).first():
                already_exist.append(username)
                continue
            db.add(models.Lecturer(
                username=username,
                name=info.get("name", username),
                email=info.get("email", "") or "",
                password_hash="catsoop:not_a_real_hash",
                courses="[]",
                registered_at=datetime.utcnow().isoformat(),
            ))
            synced.append(username)
        db.commit()
        return {
            "synced": len(synced),
            "already_exist": len(already_exist),
            "total_found": len(total_found),
            "synced_usernames": synced,
        }

    return router
