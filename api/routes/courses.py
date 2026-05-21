import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from .. import models
from ..schemas import CourseCreate, CourseEdit, WeekCreate, WeekEdit
from ..templates import generate_lecture_template, generate_problems_template, generate_native_quiz, generate_live_file_panel, generate_quiz_template
from ..config import CATSOOP_COURSES_DIR


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_router() -> APIRouter:
    router = APIRouter()

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
                content = raw.split("</python>", 1)[-1].strip() if "</python>" in raw else raw.strip()
            courses.append({
                "id": folder, "name": folder, "number": number,
                "icon": icon, "description": description, "content": content
            })
        return {"courses": sorted(courses, key=lambda x: x["id"])}

    @router.post("/admin/courses")
    async def create_course(course: CourseCreate):
        course_id = course.name.strip().replace(" ", "_")
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        if os.path.exists(course_path):
            raise HTTPException(status_code=400, detail=f"Course '{course_id}' already exists")
        os.makedirs(course_path)
        open(os.path.join(course_path, "__init__.py"), "w").close()
        with open(os.path.join(course_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = "{course.name}"\n')
            f.write(f'cs_course_number = "{course.number}"\n')
            f.write(f'cs_course_description = "{course.description}"\n')
            if course.icon:
                f.write(f'cs_course_icon = "{course.icon}"\n')
        extra = course.content or "* No materials yet."
        with open(os.path.join(course_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = "Welcome to {course.name}"\n</python>\n')
            f.write(f'{course.description}\n\n## Course Materials\n{extra}\n')
        return {"status": "success", "course_id": course_id}

    @router.put("/admin/courses/{course_id}")
    async def edit_course(course_id: str, data: CourseEdit):
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        name = course_id.replace("_", " ")
        with open(os.path.join(course_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = "{name}"\ncs_course_number = "{data.number}"\ncs_course_description = "{data.description}"\n')
            if data.icon:
                f.write(f'cs_course_icon = "{data.icon}"\n')
        with open(os.path.join(course_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = "Welcome to {name}"\n</python>\n{data.description}\n\n{data.content}\n')
        return {"status": "success"}

    @router.get("/admin/courses/{course_id}/weeks")
    async def list_weeks(course_id: str):
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        weeks = []
        for folder in os.listdir(course_path):
            path = os.path.join(course_path, folder)
            if not os.path.isdir(path) or folder.startswith('_'):
                continue
            title, content, lecture_title = folder, "", ""
            due_date, release_date, grace_period, lateness_penalty, allow_late = "", "", 0, 0.0, True
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
                "allow_late": allow_late
            })
        return {"weeks": sorted(weeks, key=lambda x: x["id"])}

    @router.post("/admin/courses/{course_id}/weeks")
    async def create_week(course_id: str, week: WeekCreate):
        course_path = os.path.join(CATSOOP_COURSES_DIR, course_id)
        if not os.path.exists(course_path):
            raise HTTPException(status_code=404, detail="Course not found")
        week_id_clean = week.week_id.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
        week_path = os.path.join(course_path, week_id_clean)
        if os.path.exists(week_path):
            raise HTTPException(status_code=400, detail=f"Week '{week_id_clean}' already exists")
        os.makedirs(week_path)
        open(os.path.join(week_path, "__init__.py"), "w").close()
        num = ''.join(filter(str.isdigit, week_id_clean)) or week_id_clean

        with open(os.path.join(week_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = "{week.title}"\n')
            if week.release_date:
                f.write(f'cs_release_date = "{week.release_date}"\n')
            if week.due_date:
                f.write(f'cs_due_date = "{week.due_date}"\n')
            if week.grace_period:
                f.write(f'cs_grace_period = {week.grace_period}\n')
            if week.lateness_penalty:
                f.write(f'cs_lateness_penalty = {week.lateness_penalty}\n')
            f.write(f'cs_allow_late = {week.allow_late}\n')

        lecture_title = week.lecture_title or f"Lecture {num}: {week.title}"
        lecture_content = week.lecture_content or f"<h1>{lecture_title}</h1>\n<p>Lecture content goes here.</p>"
        lecture_fname = f"lecture{num}.catsoop"
        with open(os.path.join(week_path, lecture_fname), "w") as f:
            f.write(generate_lecture_template(lecture_title, lecture_content))
            f.write(generate_live_file_panel())

        problem_fname = f"problem{num}.catsoop"
        with open(os.path.join(week_path, problem_fname), "w") as f:
            f.write(generate_problems_template(f"{week.title} Practice Problems", week.practice_problems))

        with open(os.path.join(week_path, "quiz.catsoop"), "w") as f:
            placeholder = f'''<python>
cs_content_header = "{week.title} Quiz"
cs_show_due = True
</python>

<p>No questions published yet. The instructor will publish the quiz soon.</p>
'''
            f.write(placeholder)
        with open(os.path.join(week_path, "example_questions.catsoop"), "w") as f:
            f.write(generate_quiz_template(course_id, week_id_clean))

        body = week.content or f"Welcome to {week.title}."
        with open(os.path.join(week_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = "{week.title}"\n</python>\n\n')
            f.write(f'{body}\n\n## Learning Materials\n')
            f.write(f'* [Lecture Notes]({week_id_clean}/{lecture_fname.replace(".catsoop","")})\n')
            f.write(f'* [Practice Problems]({week_id_clean}/{problem_fname.replace(".catsoop","")})\n')
            f.write(f'* [Quiz]({week_id_clean}/quiz)\n')

        course_content_path = os.path.join(course_path, "content.catsoop")
        if os.path.exists(course_content_path):
            with open(course_content_path, "a") as f:
                f.write(f'\n* [{week.title}]({course_id}/{week_id_clean})')

        return {"status": "success", "week_id": week_id_clean}

    @router.put("/admin/courses/{course_id}/weeks/{week_id}")
    async def edit_week(course_id: str, week_id: str, data: WeekEdit, db: Session = Depends(get_db)):
        week_path = os.path.join(CATSOOP_COURSES_DIR, course_id, week_id)
        if not os.path.exists(week_path):
            raise HTTPException(status_code=404, detail="Week not found")
        with open(os.path.join(week_path, "__INFO__.py"), "w") as f:
            f.write(f'cs_long_name = "{data.title}"\n')
            if data.release_date:
                f.write(f'cs_release_date = "{data.release_date}"\n')
            if data.due_date:
                f.write(f'cs_due_date = "{data.due_date}"\n')
            if data.grace_period:
                f.write(f'cs_grace_period = {data.grace_period}\n')
            if data.lateness_penalty:
                f.write(f'cs_lateness_penalty = {data.lateness_penalty}\n')
            f.write(f'cs_allow_late = {data.allow_late}\n')
        with open(os.path.join(week_path, "content.catsoop"), "w") as f:
            f.write(f'<python>\ncs_content_header = "{data.title}"\n</python>\n\n')
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

        # Regenerate practice problems if provided
        if data.practice_problems:
            problem_fname = f"problem{num}.catsoop"
            with open(os.path.join(week_path, problem_fname), "w") as f:
                f.write(generate_problems_template(f"{data.title} Practice Problems", data.practice_problems))

        # Regenerate quiz.catsoop from DB if questions exist
        questions = db.query(models.Question).filter(
            models.Question.course == course_id,
            models.Question.week == week_id
        ).all()
        if questions:
            quiz_path = os.path.join(week_path, "quiz.catsoop")
            with open(quiz_path, "w", encoding="utf-8") as f:
                f.write(generate_native_quiz(course_id, week_id, questions))

        # Always refresh example_questions.catsoop with current template
        example_path = os.path.join(week_path, "example_questions.catsoop")
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(generate_quiz_template(course_id, week_id))

        return {"status": "success"}

    return router
