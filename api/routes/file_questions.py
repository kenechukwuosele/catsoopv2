"""
File-based question CRUD — reads/writes <question> blocks in quiz.catsoop files.
Replaces the old SQLite-backed questions route.
Also provides the /grades endpoint that reads CatSooP cslog for grade data.
"""
import os
import re
import ast
import json
import uuid
import struct
import pickle
import lzma
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..validation import safe_course, safe_week, safe_qname, ensure_within
from ..config import CATSOOP_COURSES_DIR

DATA_ROOT = os.path.dirname(CATSOOP_COURSES_DIR)
HINT_STORE = os.path.join(DATA_ROOT, "_hint_store")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def quiz_file_path(course: str, week: str) -> str:
    return os.path.join(CATSOOP_COURSES_DIR, course, week, "quiz.catsoop")


def _normalize_type(raw_type: str, renderer: str = "radio") -> str:
    if raw_type == "multiplechoice":
        return "checkbox" if renderer == "checkbox" else "multiple-choice"
    if raw_type == "smallbox":
        return "short-answer"
    if raw_type in ("expression", "numerical"):
        return "numerical"
    if raw_type == "pythoncode":
        return "pythoncode"
    return raw_type


def parse_questions(filepath: str) -> list[dict]:
    """Return question dicts parsed from <question> blocks in a .catsoop file."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    questions = []
    for m in re.finditer(r"<question\s+(\w+)>(.*?)</question>", content, re.DOTALL):
        qtype_raw = m.group(1)
        body = m.group(2)
        q: dict = {}
        for line in body.strip().splitlines():
            line = line.strip()
            if "=" in line and line.startswith("csq_"):
                key, _, val = line.partition("=")
                try:
                    q[key.strip()] = ast.literal_eval(val.strip())
                except Exception:
                    q[key.strip()] = val.strip()

        questions.append({
            "csq_name": q.get("csq_name", ""),
            "question_type": _normalize_type(qtype_raw, str(q.get("csq_renderer", "radio"))),
            "question_text": q.get("csq_prompt", ""),
            "options": q.get("csq_options") or [],
            "correct_answer": q.get("csq_soln", ""),
            "points": int(q.get("csq_npoints") or 1),
        })
    return questions


def _read_all_cslog(filepath: str) -> list:
    """Return all entries from a cslog binary file."""
    if not os.path.exists(filepath):
        return []
    entries = []
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        pos = 0
        while pos + 16 <= len(data):
            length = struct.unpack("<Q", data[pos: pos + 8])[0]
            if pos + 8 + length + 8 > len(data):
                break
            entry_data = data[pos + 8: pos + 8 + length]
            try:
                obj = pickle.loads(entry_data)
            except Exception:
                try:
                    obj = pickle.loads(lzma.decompress(entry_data))
                except Exception:
                    obj = None
            if obj is not None:
                entries.append(obj)
            pos += 8 + length + 8
    except Exception:
        pass
    return entries


def _read_time_limit(week_path: str) -> int:
    """Read cs_quiz_time_limit from a week's __INFO__.py (returns 0 if not set)."""
    info = os.path.join(week_path, "__INFO__.py")
    if not os.path.exists(info):
        return 0
    with open(info) as f:
        for line in f:
            if "cs_quiz_time_limit" in line:
                try:
                    return int(line.split("=")[-1].strip())
                except Exception:
                    pass
    return 0


def _save_hints_json(course: str, week: str, csq_name: str, hints: list):
    hint_dir = os.path.join(HINT_STORE, course, week)
    os.makedirs(hint_dir, exist_ok=True)
    with open(os.path.join(hint_dir, f"{csq_name}.json"), "w") as f:
        json.dump(hints, f)


def append_questions(course: str, week: str, new_questions: list[dict]) -> list[str]:
    """Append a batch of question dicts to quiz.catsoop. Returns list of assigned csq_names."""
    from ..templates import generate_native_quiz

    path = quiz_file_path(course, week)
    week_path = os.path.join(CATSOOP_COURSES_DIR, course, week)
    questions = parse_questions(path)
    assigned = []
    for item in new_questions:
        csq_name = f"q_{uuid.uuid4().hex[:8]}"
        correct = item.get("correct_answer", "")
        if isinstance(correct, list):
            correct = correct[0] if correct else ""
        questions.append({
            "csq_name": csq_name,
            "question_type": item.get("question_type", "short-answer"),
            "question_text": item.get("question_text", ""),
            "options": item.get("options") or [],
            "correct_answer": str(correct),
            "points": int(item.get("points") or 1),
        })
        if item.get("hints"):
            _save_hints_json(course, week, csq_name, [
                {"number": i + 1, "text": str(h)}
                for i, h in enumerate(item["hints"]) if str(h).strip()
            ])
        assigned.append(csq_name)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(generate_native_quiz(course, week, questions, _read_time_limit(week_path)))
    return assigned


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def get_router() -> APIRouter:
    router = APIRouter()

    @router.get("/admin/questions/{course}/{week}", dependencies=[Depends(require_admin)])
    async def list_questions(course: str, week: str):
        course = safe_course(course); week = safe_week(week)
        return {"questions": parse_questions(quiz_file_path(course, week))}

    @router.post("/admin/questions/{course}/{week}", dependencies=[Depends(require_admin)])
    async def add_question(course: str, week: str, body: dict):
        course = safe_course(course); week = safe_week(week)
        from ..templates import generate_native_quiz

        text = (body.get("question_text") or body.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="question_text is required")

        qtype = body.get("question_type") or body.get("type", "short-answer")
        options = body.get("options") or []
        correct = body.get("correct_answer") or body.get("correctAnswer", "")
        if isinstance(correct, list):
            correct = correct[0] if correct else ""
        hints_raw = body.get("hints") or []

        csq_name = f"q_{uuid.uuid4().hex[:8]}"
        path = quiz_file_path(course, week)
        week_path = os.path.join(CATSOOP_COURSES_DIR, course, week)
        questions = parse_questions(path)
        questions.append({
            "csq_name": csq_name,
            "question_type": qtype,
            "question_text": text,
            "options": options,
            "correct_answer": correct,
            "points": int(body.get("points") or 1),
        })

        content = generate_native_quiz(course, week, questions, _read_time_limit(week_path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        if hints_raw:
            _save_hints_json(course, week, csq_name, [
                {"number": i + 1, "text": str(h)}
                for i, h in enumerate(hints_raw) if str(h).strip()
            ])

        return {"status": "success", "csq_name": csq_name}

    @router.delete("/admin/questions/{course}/{week}/{csq_name}", dependencies=[Depends(require_admin)])
    async def delete_question(course: str, week: str, csq_name: str):
        course = safe_course(course); week = safe_week(week); csq_name = safe_qname(csq_name)
        from ..templates import generate_native_quiz

        path = quiz_file_path(course, week)
        week_path = os.path.join(CATSOOP_COURSES_DIR, course, week)
        questions = parse_questions(path)
        filtered = [q for q in questions if q["csq_name"] != csq_name]
        if len(filtered) == len(questions):
            raise HTTPException(status_code=404, detail=f"Question '{csq_name}' not found")

        with open(path, "w", encoding="utf-8") as f:
            f.write(generate_native_quiz(course, week, filtered, _read_time_limit(week_path)))

        hint_file = os.path.join(HINT_STORE, course, week, f"{csq_name}.json")
        if os.path.exists(hint_file):
            os.remove(hint_file)

        return {"status": "success", "deleted": csq_name}

    @router.delete("/admin/questions/{course}/{week}", dependencies=[Depends(require_admin)])
    async def delete_all_questions(course: str, week: str):
        course = safe_course(course); week = safe_week(week)
        from ..templates import generate_native_quiz

        path = quiz_file_path(course, week)
        week_path = os.path.join(CATSOOP_COURSES_DIR, course, week)
        questions = parse_questions(path)
        for q in questions:
            hint_file = os.path.join(HINT_STORE, course, week, f"{q['csq_name']}.json")
            if os.path.exists(hint_file):
                os.remove(hint_file)

        with open(path, "w", encoding="utf-8") as f:
            f.write(generate_native_quiz(course, week, [], _read_time_limit(week_path)))

        return {"status": "success", "deleted": len(questions)}

    @router.post("/admin/bulk-import/{course}/{week}", dependencies=[Depends(require_admin)])
    async def bulk_import(course: str, week: str, body: dict):
        course = safe_course(course); week = safe_week(week)
        from ..templates import generate_native_quiz

        incoming = body.get("questions", []) or []
        if not incoming:
            raise HTTPException(status_code=400, detail="No questions provided")

        path = quiz_file_path(course, week)
        if body.get("clear_existing", False):
            for q in parse_questions(path):
                hint_file = os.path.join(HINT_STORE, course, week, f"{q['csq_name']}.json")
                if os.path.exists(hint_file):
                    os.remove(hint_file)
            questions = []
        else:
            questions = parse_questions(path)

        imported = 0
        for item in incoming:
            text = (item.get("text") or item.get("question_text", "")).strip()
            if not text:
                continue
            csq_name = f"q_{uuid.uuid4().hex[:8]}"
            correct = item.get("correct_answer") or item.get("correct_answers", "")
            if isinstance(correct, list):
                correct = correct[0] if correct else ""
            questions.append({
                "csq_name": csq_name,
                "question_type": item.get("type") or item.get("question_type", "short-answer"),
                "question_text": text,
                "options": item.get("options") or [],
                "correct_answer": correct,
                "points": int(item.get("points") or 1),
            })
            if item.get("hints"):
                _save_hints_json(course, week, csq_name, [
                    {"number": i + 1, "text": str(h)}
                    for i, h in enumerate(item["hints"]) if str(h).strip()
                ])
            imported += 1

        week_path = os.path.join(CATSOOP_COURSES_DIR, course, week)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(generate_native_quiz(course, week, questions, _read_time_limit(week_path)))

        return {"status": "success", "imported": imported}

    # --- Grades (reads CatSooP cslog problemactions) ---

    @router.get("/{course}/{week}/grades", dependencies=[Depends(require_admin)])
    async def get_grades(course: str, week: str):
        course = safe_course(course); week = safe_week(week)
        log_base = os.path.join(DATA_ROOT, "_logs", "_courses", course)
        if not os.path.isdir(log_base):
            return {"grades": []}

        grades = []
        for username in sorted(os.listdir(log_base)):
            user_dir = os.path.join(log_base, username)
            if not os.path.isdir(user_dir):
                continue

            for sub in [os.path.join(week, "quiz"), week]:
                entries = _read_all_cslog(os.path.join(user_dir, sub, "problemactions.log"))
                if not entries:
                    continue

                q_scores: dict[str, float] = {}
                q_times: dict[str, str] = {}
                for entry in entries:
                    if not isinstance(entry, dict) or entry.get("action") != "submit":
                        continue
                    ts = entry.get("timestamp", "")
                    # CatSooP stores per-question scores in the 'scores' dict
                    entry_scores: dict = entry.get("scores") or {}
                    for name, raw_score in entry_scores.items():
                        try:
                            score = float(raw_score or 0)
                        except Exception:
                            score = 0.0
                        if name not in q_times or ts > q_times[name]:
                            q_scores[name] = score
                            q_times[name] = ts

                if q_scores:
                    total = sum(q_scores.values())
                    n = len(q_scores)
                    grades.append({
                        "username": username,
                        "score": round(total, 2),
                        "total": n,
                        "percent": round(total / n * 100, 1) if n else 0,
                        "question_scores": q_scores,
                        "last_submit": max(q_times.values()) if q_times else "",
                    })
                    break

        return {"grades": grades}

    return router
