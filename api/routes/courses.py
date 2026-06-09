import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..auth import require_admin
from ..validation import safe_course, safe_week, safe_text_for_pyfile, ensure_within
from ..schemas import CourseCreate, CourseEdit, WeekCreate, WeekEdit
from ..templates import (generate_lecture_template, generate_problems_template, generate_native_quiz,
                         generate_live_file_panel, generate_quiz_template, generate_leaderboard_page,
                         generate_leaderboard_widget, LEADERBOARD_SENTINEL, generate_gradebook_template)
from ..config import CATSOOP_COURSES_DIR
from ..routes.file_questions import parse_questions, quiz_file_path, _read_time_limit, DATA_ROOT


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router() -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_admin)])

    @router.get("/admin/courses")
    async def list_courses():
        courses = []
        if not os.path.exists(CATSOOP_COURSES_DIR):
            return {"courses": []}
        for folder in os.listdir(CATSOOP_COURSES_DIR):
            path = os.path.join(CATSOOP_COURSES_DIR, folder)
            if not os.path.isdir(path) or folder.startswith('_'):
                continue
            info_path = os.path.join(path, "__INFO__.py")
            number, description, icon, content = "", "", "", ""
            if os.path.exists(info_path):
                with open(info_path) as f:
                    for line in f.read().splitlines():
                        if "cs_course_number" in line:
                            number = line.split("=")[-1].strip().strip('"').strip("'")
                        if "cs_course_description" in line:
                            description = line.split("=", 1)[-1].strip().strip('"').strip("'")
                        if "cs_course_icon" in line:
                            icon = line.split("=", 1)[-1].strip().strip('"').strip("'")
            content_path = os.path.join(path, "content.catsoop")
            if os.path.exists(content_path):
                with open(content_path) as f:
                    raw = f.read()
                after_python = raw.split("</python>", 1)[-1] if "</python>" in raw else raw
                content = after_python.split(LEADERBOARD_SENTINEL)[0].strip()
            courses.append({
                "id": folder, "name": folder, "number": number,
                "icon": icon, "description": description, "content": content
            })
        return {"courses": sorted(courses, key=lambda x: x["id"])}

    @router.post("/admin/courses")
    async def create_course(course: CourseCreate):
        raw_name = safe_text_for_pyfile((course.name or "").strip(), max_len=128)
        course_id = raw_name.replace(" ", "_")
        course_id = safe_course(course_id)
        number = safe_text_for_pyfile(course.number or "", max_len=64)
        description = safe_text_for_pyfile(course.description or "", max_len=2048)
        icon = safe_text_for_pyfile(course.icon or "", max_len=64)

        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        ensure_within(CATSOOP_COURSES_DIR, course_path)
        if os.path.exists(course_path):
            raise HTTPException(status_code=400, detail=f"Course '{course_id}' already exists")
        os.makedirs(course_path)
        open(os.path.join(course_path, "__init__.py"), "w").close()
        with open(os.path.join(course_path, "preload.py"), "w") as f:
            f.write('cs_view_without_auth = False\n')
        with open(os.path.join(course_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = {raw_name!r}\n')
            f.write(f'cs_course_number = {number!r}\n')
            f.write(f'cs_course_description = {description!r}\n')
            if icon:
                f.write(f'cs_course_icon = {icon!r}\n')
        extra = course.content or "* No materials yet."
        with open(os.path.join(course_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = {("Welcome to " + raw_name)!r}\n</python>\n')
            f.write(f'{description}\n\n## Course Materials\n{extra}\n')
            f.write(generate_leaderboard_widget(course_id))
        with open(os.path.join(course_path, "gradebook.catsoop"), "w") as f:
            f.write(generate_gradebook_template(course_id))
        return {"status": "success", "course_id": course_id}

    @router.put("/admin/courses/{course_id}")
    async def edit_course(course_id: str, data: CourseEdit):
        course_id = safe_course(course_id)
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        ensure_within(CATSOOP_COURSES_DIR, course_path)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        name = course_id.replace("_", " ")
        number = safe_text_for_pyfile(data.number or "", max_len=64)
        description = safe_text_for_pyfile(data.description or "", max_len=2048)
        icon = safe_text_for_pyfile(data.icon or "", max_len=64)
        with open(os.path.join(course_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = {name!r}\ncs_course_number = {number!r}\ncs_course_description = {description!r}\n')
            if icon:
                f.write(f'cs_course_icon = {icon!r}\n')
        with open(os.path.join(course_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = {("Welcome to " + name)!r}\n</python>\n\n{data.content}\n\n')
            f.write(generate_leaderboard_widget(course_id))
        return {"status": "success"}

    @router.delete("/admin/courses/{course_id}")
    async def delete_course(course_id: str, db: Session = Depends(get_db)):
        course_id = safe_course(course_id)
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        ensure_within(CATSOOP_COURSES_DIR, course_path)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        for model_cls in [models.LiveFile, models.ContentChunk, models.EngagementSample]:
            if hasattr(model_cls, 'course'):
                db.query(model_cls).filter(model_cls.course == course_id).delete(synchronize_session=False)
        db.commit()
        shutil.rmtree(course_path)
        return {"status": "success"}

    @router.get("/admin/courses/{course_id}/weeks")
    async def list_weeks(course_id: str):
        course_id = safe_course(course_id)
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        ensure_within(CATSOOP_COURSES_DIR, course_path)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        weeks = []
        for folder in os.listdir(course_path):
            path = os.path.join(course_path, folder)
            if not os.path.isdir(path) or folder.startswith('_'):
                continue
            title, content, lecture_title = folder, "", ""
            due_date, release_date, grace_period, lateness_penalty, allow_late = "", "", 0, 0.0, True
            time_limit_minutes = 0
            info_path = os.path.join(path, "__INFO__.py")
            if os.path.exists(info_path):
                with open(info_path) as f:
                    raw = f.read()
                for line in raw.splitlines():
                    if "cs_long_name" in line:
                        title = line.split("=")[-1].strip().strip('"').strip("'")
                    if "cs_release_date" in line:
                        release_date = line.split("=")[-1].strip().strip('"').strip("'")
                    if "cs_due_date" in line:
                        due_date = line.split("=")[-1].strip().strip('"').strip("'")
                    if "cs_grace_period" in line:
                        try:
                            grace_period = int(line.split("=")[-1].strip())
                        except Exception:
                            pass
                    if "cs_lateness_penalty" in line:
                        try:
                            lateness_penalty = float(line.split("=")[-1].strip())
                        except Exception:
                            pass
                    if "cs_allow_late" in line:
                        allow_late = "True" in line
                    if "cs_quiz_time_limit" in line:
                        try:
                            time_limit_minutes = int(line.split("=")[-1].strip())
                        except Exception:
                            pass
            content_path = os.path.join(path, "content.catsoop")
            if os.path.exists(content_path):
                with open(content_path) as f:
                    raw = f.read()
                content = raw.split("</python>", 1)[-1].strip() if "</python>" in raw else raw.strip()
            for fname in os.listdir(path):
                if fname.startswith("lecture") and fname.endswith(".catsoop"):
                    with open(os.path.join(path, fname)) as f:
                        lraw = f.read()
                    for line in lraw.splitlines():
                        if "cs_content_header" in line:
                            lecture_title = line.split("=")[-1].strip().strip('"').strip("'")
            weeks.append({
                "id": folder, "title": title, "content": content,
                "lecture_title": lecture_title, "release_date": release_date,
                "due_date": due_date,
                "grace_period": grace_period, "lateness_penalty": lateness_penalty,
                "allow_late": allow_late, "time_limit_minutes": time_limit_minutes
            })
        return {"weeks": sorted(weeks, key=lambda x: x["id"])}

    @router.get("/admin/performance")
    async def get_performance():
        """Aggregate grade data across all courses/weeks from CatSooP cslog."""
        from ..routes.file_questions import _read_all_cslog

        data_root = os.path.dirname(CATSOOP_COURSES_DIR)
        log_base = os.path.join(data_root, "_logs", "_courses")
        result = []

        if not os.path.isdir(CATSOOP_COURSES_DIR):
            return {"performance": []}

        for course_id in sorted(os.listdir(CATSOOP_COURSES_DIR)):
            course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
            if not os.path.isdir(course_path) or course_id.startswith("_"):
                continue
            for week_id in sorted(os.listdir(course_path)):
                week_path = os.path.join(course_path, week_id)
                if not os.path.isdir(week_path) or week_id.startswith("_"):
                    continue
                course_log = os.path.join(log_base, course_id)
                if not os.path.isdir(course_log):
                    continue
                student_percents: list[float] = []
                for username in os.listdir(course_log):
                    user_dir = os.path.join(course_log, username)
                    if not os.path.isdir(user_dir):
                        continue
                    for sub in [os.path.join(week_id, "quiz"), week_id]:
                        entries = _read_all_cslog(os.path.join(user_dir, sub, "problemactions.log"))
                        if not entries:
                            continue
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
                        if q_scores:
                            n = len(q_scores)
                            student_percents.append(sum(q_scores.values()) / n * 100)
                            break
                if student_percents:
                    result.append({
                        "course": course_id,
                        "week": week_id,
                        "total_students": len(student_percents),
                        "total_attempts": len(student_percents),
                        "avg_score": round(sum(student_percents) / len(student_percents), 1),
                        "max_score": round(max(student_percents), 1),
                        "min_score": round(min(student_percents), 1),
                        "hints_used": 0,
                    })

        return {"performance": result}

    @router.post("/admin/courses/{course_id}/weeks")
    async def create_week(course_id: str, week: WeekCreate):
        course_id = safe_course(course_id)
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        ensure_within(CATSOOP_COURSES_DIR, course_path)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        week_id_clean = (week.week_id or "").strip().lower().replace(" ", "").replace("-", "").replace("_", "")
        week_id_clean = safe_week(week_id_clean)
        title = safe_text_for_pyfile(week.title or week_id_clean, max_len=128)
        release_date = safe_text_for_pyfile(week.release_date or "", max_len=64)
        due_date = safe_text_for_pyfile(week.due_date or "", max_len=64)
        grace_period = int(week.grace_period or 0)
        lateness_penalty = float(week.lateness_penalty or 0)
        allow_late = bool(week.allow_late)
        time_limit_minutes = int(week.time_limit_minutes or 0)
        week_path = os.path.join(course_path, week_id_clean)
        ensure_within(course_path, week_path)
        if os.path.exists(week_path):
            raise HTTPException(status_code=400, detail=f"Week '{week_id_clean}' already exists")
        os.makedirs(week_path)
        open(os.path.join(week_path, "__init__.py"), "w").close()
        num = ''.join(filter(str.isdigit, week_id_clean)) or week_id_clean

        with open(os.path.join(week_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = {title!r}\n')
            if release_date:
                f.write(f'cs_release_date = {release_date!r}\n')
            if due_date:
                f.write(f'cs_due_date = {due_date!r}\n')
            if grace_period:
                f.write(f'cs_grace_period = {grace_period}\n')
            if lateness_penalty:
                f.write(f'cs_lateness_penalty = {lateness_penalty}\n')
            f.write(f'cs_allow_late = {allow_late}\n')
            if time_limit_minutes:
                f.write(f'cs_quiz_time_limit = {time_limit_minutes}\n')

        lecture_title = week.lecture_title or f"Lecture {num}: {title}"
        lecture_content = week.lecture_content or f"<h1>{lecture_title}</h1>\n<p>Lecture content goes here.</p>"
        lecture_fname = f"lecture{num}.catsoop"
        with open(os.path.join(week_path, lecture_fname), "w") as f:
            f.write(generate_lecture_template(lecture_title, lecture_content))
            f.write(generate_live_file_panel())

        problem_fname = f"problem{num}.catsoop"
        with open(os.path.join(week_path, problem_fname), "w") as f:
            f.write(generate_problems_template(f"{title} Practice Problems", week.practice_problems))

        with open(os.path.join(week_path, "quiz.catsoop"), "w") as f:
            placeholder = (
                f'<python>\ncs_content_header = {(title + " Quiz")!r}\ncs_show_due = True\n</python>\n\n'
                '<p>No questions published yet. The instructor will publish the quiz soon.</p>\n'
            )
            f.write(placeholder)
        with open(os.path.join(week_path, "example_questions.catsoop"), "w") as f:
            f.write(generate_quiz_template(course_id, week_id_clean))

        body = week.content or f"Welcome to {title}."
        with open(os.path.join(week_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = {title!r}\n</python>\n\n')
            f.write(f'{body}\n\n## Learning Materials\n')
            f.write(f'* [Lecture Notes]({week_id_clean}/{lecture_fname.replace(".catsoop","")})\n')
            f.write(f'* [Practice Problems]({week_id_clean}/{problem_fname.replace(".catsoop","")})\n')
            f.write(f'* [Quiz]({week_id_clean}/quiz)\n')

        # Scaffold leaderboard page once per course
        lb_path = os.path.join(course_path, "leaderboard.catsoop")
        if not os.path.exists(lb_path):
            with open(lb_path, "w") as f:
                f.write(generate_leaderboard_page(course_id))

        course_content_path = os.path.join(course_path, "content.catsoop")
        if os.path.exists(course_content_path):
            with open(course_content_path, "r", encoding="utf-8") as f:
                _cc = f.read()
            _link = f'\n* [{title}]({course_id}/{week_id_clean})'
            if LEADERBOARD_SENTINEL in _cc:
                _cc = _cc.replace(LEADERBOARD_SENTINEL, _link + '\n' + LEADERBOARD_SENTINEL)
            else:
                _cc += _link
            with open(course_content_path, "w", encoding="utf-8") as f:
                f.write(_cc)

        return {"status": "success", "week_id": week_id_clean}

    @router.put("/admin/courses/{course_id}/weeks/{week_id}")
    async def edit_week(course_id: str, week_id: str, data: WeekEdit, db: Session = Depends(get_db)):
        course_id = safe_course(course_id)
        week_id = safe_week(week_id)
        week_path = os.path.join(CATSOOP_COURSES_DIR, course_id, week_id)
        ensure_within(CATSOOP_COURSES_DIR, week_path)
        if not os.path.exists(week_path):
            raise HTTPException(status_code=404, detail="Week not found")
        title = safe_text_for_pyfile(data.title or week_id, max_len=128)
        release_date = safe_text_for_pyfile(data.release_date or "", max_len=64)
        due_date = safe_text_for_pyfile(data.due_date or "", max_len=64)
        grace_period = int(data.grace_period or 0)
        lateness_penalty = float(data.lateness_penalty or 0)
        allow_late = bool(data.allow_late)
        time_limit_minutes = int(data.time_limit_minutes or 0)
        with open(os.path.join(week_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = {title!r}\n')
            if release_date:
                f.write(f'cs_release_date = {release_date!r}\n')
            if due_date:
                f.write(f'cs_due_date = {due_date!r}\n')
            if grace_period:
                f.write(f'cs_grace_period = {grace_period}\n')
            if lateness_penalty:
                f.write(f'cs_lateness_penalty = {lateness_penalty}\n')
            f.write(f'cs_allow_late = {allow_late}\n')
            if time_limit_minutes:
                f.write(f'cs_quiz_time_limit = {time_limit_minutes}\n')
        qpath = quiz_file_path(course_id, week_id)
        if os.path.exists(qpath):
            existing_questions = parse_questions(qpath)
            new_time_limit = _read_time_limit(week_path)
            with open(qpath, "w", encoding="utf-8") as f:
                f.write(generate_native_quiz(course_id, week_id, existing_questions, new_time_limit))
        with open(os.path.join(week_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = {title!r}\n</python>\n\n')
            f.write(f'{data.content}\n')
        num = ''.join(filter(str.isdigit, week_id)) or week_id
        lecture_fname = os.path.join(week_path, f"lecture{num}.catsoop")
        if os.path.exists(lecture_fname):
            raw = open(lecture_fname).read()
            if 'live-file-panel' not in raw:
                with open(lecture_fname, "a") as f:
                    f.write(generate_live_file_panel())
        if data.lecture_title or data.lecture_content:
            if os.path.exists(lecture_fname):
                with open(lecture_fname, "w") as f:
                    f.write(generate_lecture_template(data.lecture_title, data.lecture_content))
                    f.write(generate_live_file_panel())

        if data.practice_problems:
            problem_fname = f"problem{num}.catsoop"
            with open(os.path.join(week_path, problem_fname), "w") as f:
                f.write(generate_problems_template(f"{title} Practice Problems", data.practice_problems))

        example_path = os.path.join(week_path, "example_questions.catsoop")
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(generate_quiz_template(course_id, week_id))

        return {"status": "success"}

    @router.delete("/admin/courses/{course_id}/weeks/{week_id}/submissions",
                   dependencies=[Depends(require_admin)])
    async def reset_week_submissions(course_id: str, week_id: str):
        course_id = safe_course(course_id)
        week_id = safe_week(week_id)
        logs_base = os.path.join(DATA_ROOT, "_logs", "_courses", course_id)
        deleted = 0
        if os.path.exists(logs_base):
            for username in os.listdir(logs_base):
                user_dir = os.path.join(logs_base, username)
                for sub in [os.path.join(week_id, "quiz"), week_id]:
                    log_path = os.path.join(user_dir, sub, "problemactions.log")
                    if os.path.isfile(log_path):
                        os.remove(log_path)
                        deleted += 1
        return {"status": "ok", "logs_deleted": deleted}

    return router
