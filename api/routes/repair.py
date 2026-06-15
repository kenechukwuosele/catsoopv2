import os

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..config import CATSOOP_COURSES_DIR
from ..templates import (
    generate_native_quiz, generate_quiz_template, generate_gradebook_template,
    generate_leaderboard_widget, LEADERBOARD_SENTINEL,
)


def get_router():
    router = APIRouter()

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

    return router
