import os
import json
import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import require_admin, verify_admin_password, mint_token, ADMIN_PASSWORD
from ..config import ADMIN_HTML_PATH, CATSOOP_COURSES_DIR, SERVER_BASE_URL


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
    data_root = os.path.dirname(CATSOOP_COURSES_DIR)
    path = os.path.join(data_root, "_logs", "_logininfo", f"{username}.log")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            raw = f.read()
        pos, result = 0, {}
        while pos < len(raw):
            if pos + 8 > len(raw):
                break
            length = struct.unpack("<Q", raw[pos:pos+8])[0]
            pos += 8
            chunk = raw[pos:pos+length]
            pos += length + 8  # skip trailing length too
            try:
                obj = pickle.loads(lzma.decompress(chunk))
            except Exception:
                try:
                    obj = pickle.loads(chunk)
                except Exception:
                    continue
            if isinstance(obj, dict):
                result.update(obj)
        return result
    except Exception:
        return {}


def _verify_catsoop_instructor(username: str, password: str) -> bool:
    """Verify a CatSooP instructor's password."""
    import hashlib as _hl
    info = _read_catsoop_logininfo(username)
    if not info:
        return False
    if not info.get("confirmed", False):
        return False
    if info.get("role", "") != "Instructor":
        return False
    stored_hash = info.get("password_hash", "")
    salt = info.get("password_salt", "")
    if not stored_hash or not salt:
        return False
    try:
        # CatSooP client: PBKDF2-SHA256(pass, pass+username, 100000, 32)
        client_hash = _hl.pbkdf2_hmac(
            "sha256",
            password.encode(),
            (password + username).encode(),
            100000,
            dklen=32,
        ).hex()
        # CatSooP server: PBKDF2-SHA512(client_hash, salt, 500000)
        server_hash = _hl.pbkdf2_hmac(
            "sha512",
            client_hash.encode(),
            salt.encode(),
            500000,
        ).hex()
        return server_hash == stored_hash
    except Exception:
        return False


def get_router():
    router = APIRouter()

    # ── Authentication ───────────────────────────────────────────────────────

    @router.post("/admin/login")
    async def admin_login(body: AdminLoginRequest, db: Session = Depends(get_db)):
        uname = (body.username or "").strip()
        pw = body.password

        # 1. System admin
        if (not uname or uname == "admin") and ADMIN_PASSWORD and verify_admin_password(pw):
            token = mint_token("admin", True)
            return {"token": token, "role": "admin", "username": "admin", "name": "Admin"}

        # 2. FastAPI lecturer
        if uname:
            lec = db.query(models.Lecturer).filter_by(username=uname).first()
            if lec and lec.password_hash and lec.password_hash != "catsoop:not_a_real_hash":
                parts = lec.password_hash.split(":", 1)
                if len(parts) == 2:
                    salt, h = parts
                    expected = hashlib.sha256((salt + pw).encode()).hexdigest()
                    if expected == h:
                        courses = json.loads(lec.courses or "[]")
                        token = mint_token(lec.username, True)
                        return {"token": token, "role": "lecturer",
                                "username": lec.username, "name": lec.name or lec.username,
                                "courses": courses}

        # 3. CatSooP instructor
        if uname and _verify_catsoop_instructor(uname, pw):
            lec = db.query(models.Lecturer).filter_by(username=uname).first()
            courses = json.loads(lec.courses or "[]") if lec else []
            token = mint_token(uname, True)
            return {"token": token, "role": "lecturer", "username": uname,
                    "name": uname, "courses": courses}

        raise HTTPException(status_code=401, detail="Invalid credentials")

    @router.get("/admin/auto-token")
    async def admin_auto_token():
        if ADMIN_PASSWORD:
            raise HTTPException(status_code=403, detail="Password required")
        token = mint_token("admin", True)
        return {"token": token, "role": "admin", "username": "admin"}

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_panel():
        with open(ADMIN_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        html = html.replace("__API_BASE__", SERVER_BASE_URL)
        return html

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
