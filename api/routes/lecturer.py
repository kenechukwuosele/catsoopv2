import os
import json
import time
import hashlib
import secrets
import struct
import pickle

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import SECRET, TOKEN_TTL_SECONDS, decode_token, _extract_token
from ..validation import safe_course
from ..config import CATSOOP_COURSES_DIR

DATA_ROOT = os.path.dirname(CATSOOP_COURSES_DIR)
LOGIN_INFO_DIR = os.path.join(DATA_ROOT, "_logs", "_logininfo")
COURSES_LOG_DIR = os.path.join(DATA_ROOT, "_logs", "_courses")
LECTURER_HTML_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "lecturer.html")
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _verify_lecturer_password(stored_hash: str, password: str) -> bool:
    try:
        salt, h = stored_hash.split(":", 1)
        computed = hashlib.sha256((salt + password).encode()).hexdigest()
        return computed == h
    except Exception:
        return False


def _mint_lecturer_token(username: str, courses: list) -> str:
    if not SECRET:
        raise RuntimeError("CU_QUIZ_SECRET not set")
    payload = {
        "sub": username,
        "is_admin": True,   # grants access to all admin API endpoints
        "is_lecturer": True, # frontend uses this to hide the Lecturers management tab
        "courses": courses,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _require_admin_or_lecturer(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    claims = decode_token(token)
    if not claims.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin or lecturer access required")
    # Lecturers have is_admin=True AND is_lecturer=True with a courses list.
    # Pure system admin tokens have is_lecturer absent — courses=None means unrestricted.
    if claims.get("is_lecturer"):
        return {"username": claims["sub"], "is_admin": True, "courses": claims.get("courses", [])}
    return {"username": claims["sub"], "is_admin": True, "courses": None}


def _read_last_logininfo(username: str) -> dict:
    """Return last pickled entry from a CatSooP _logininfo cslog file."""
    path = os.path.join(LOGIN_INFO_DIR, f"{username}.log")
    if not os.path.exists(path):
        return {}
    last: dict = {}
    try:
        with open(path, "rb") as f:
            data = f.read()
        pos = 0
        while pos + 16 <= len(data):
            length = struct.unpack("<Q", data[pos: pos + 8])[0]
            if pos + 8 + length + 8 > len(data):
                break
            entry_data = data[pos + 8: pos + 8 + length]
            try:
                obj = pickle.loads(entry_data)
                if isinstance(obj, dict):
                    last = obj
            except Exception:
                pass
            pos += 8 + length + 8
    except Exception:
        pass
    return last


def _append_logininfo(username: str, entry: dict) -> None:
    """Append a new pickled entry to a CatSooP _logininfo cslog file."""
    path = os.path.join(LOGIN_INFO_DIR, f"{username}.log")
    os.makedirs(LOGIN_INFO_DIR, exist_ok=True)
    data = pickle.dumps(entry)
    n = struct.pack("<Q", len(data))
    with open(path, "ab") as f:
        f.write(n + data + n)


def _reset_student_password(username: str, new_password: str) -> None:
    existing = _read_last_logininfo(username)
    if not existing:
        raise HTTPException(status_code=404, detail="Student account not found in CatSooP")
    new_salt = secrets.token_bytes(128)
    new_hash = hashlib.pbkdf2_hmac("sha512", new_password.encode(), new_salt, 500_000)
    updated = dict(existing)
    updated["password_salt"] = new_salt
    updated["password_hash"] = new_hash
    _append_logininfo(username, updated)


def _list_students_in_course(course: str) -> list:
    course_dir = os.path.join(COURSES_LOG_DIR, course)
    if not os.path.isdir(course_dir):
        return []
    students = []
    for username in sorted(os.listdir(course_dir)):
        user_dir = os.path.join(course_dir, username)
        if os.path.isdir(user_dir):
            try:
                mtime = os.path.getmtime(user_dir)
                students.append({"username": username, "last_active": int(mtime)})
            except Exception:
                students.append({"username": username, "last_active": None})
    return students


def get_router() -> APIRouter:
    router = APIRouter()

    class LecturerLoginRequest(BaseModel):
        username: str
        password: str

    class ResetPasswordRequest(BaseModel):
        course: str
        new_password: str

    @router.get("/lecturer")
    def lecturer_redirect():
        return RedirectResponse(url="/admin", status_code=302)

    @router.post("/lecturer/login")
    def lecturer_login(body: LecturerLoginRequest, db: Session = Depends(get_db)):
        lec = db.query(models.Lecturer).filter_by(username=body.username.strip()).first()
        if not lec or not _verify_lecturer_password(lec.password_hash, body.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        courses = json.loads(lec.courses or "[]")
        token = _mint_lecturer_token(lec.username, courses)
        return {"token": token, "username": lec.username, "name": lec.name, "courses": courses}

    @router.get("/lecturer/students")
    def list_students(
        course: str = Query(...),
        user: dict = Depends(_require_admin_or_lecturer),
    ):
        course = safe_course(course)
        if user["courses"] is not None and course not in user["courses"]:
            raise HTTPException(status_code=403, detail="Not assigned to this course")
        students = _list_students_in_course(course)
        return {"course": course, "students": students}

    @router.post("/lecturer/students/{username}/reset-password")
    def reset_student_password(
        username: str,
        body: ResetPasswordRequest,
        user: dict = Depends(_require_admin_or_lecturer),
    ):
        course = safe_course(body.course)
        if user["courses"] is not None and course not in user["courses"]:
            raise HTTPException(status_code=403, detail="Not assigned to this course")
        if not body.new_password or len(body.new_password) < 6:
            raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
        _reset_student_password(username, body.new_password)
        return {"status": "ok", "username": username}

    return router
