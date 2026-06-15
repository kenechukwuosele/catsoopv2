import pytest

COURSE = "TestCourse"
WEEK = "week1"


@pytest.fixture(autouse=True)
def quiz_file(tmp_path, monkeypatch):
    import api.config as cfg
    import api.routes.file_questions as fq
    courses_dir = tmp_path / "courses" / COURSE / WEEK
    courses_dir.mkdir(parents=True)
    (courses_dir / "quiz.catsoop").write_text("")
    hint_dir = tmp_path / "_hint_store"
    hint_dir.mkdir()
    monkeypatch.setattr(cfg, "CATSOOP_COURSES_DIR", str(tmp_path / "courses"))
    monkeypatch.setattr(fq, "CATSOOP_COURSES_DIR", str(tmp_path / "courses"))
    monkeypatch.setattr(fq, "HINT_STORE", str(hint_dir))


def test_list_questions_empty(client, auth_headers):
    r = client.get(f"/admin/questions/{COURSE}/{WEEK}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["questions"] == []


def test_add_and_list_question(client, auth_headers):
    payload = {
        "question_text": "What is 2+2?",
        "question_type": "multiple-choice",
        "options": ["3", "4", "5"],
        "correct_answer": "4",
        "points": 1,
    }
    r = client.post(f"/admin/questions/{COURSE}/{WEEK}", json=payload, headers=auth_headers)
    assert r.status_code == 200
    name = r.json()["csq_name"]
    assert name.startswith("q_")

    r2 = client.get(f"/admin/questions/{COURSE}/{WEEK}", headers=auth_headers)
    assert r2.status_code == 200
    assert len(r2.json()["questions"]) == 1
    assert r2.json()["questions"][0]["question_text"] == "What is 2+2?"


def test_delete_question(client, auth_headers):
    payload = {
        "question_text": "Delete me",
        "question_type": "short-answer",
        "options": [],
        "correct_answer": "yes",
        "points": 1,
    }
    r = client.post(f"/admin/questions/{COURSE}/{WEEK}", json=payload, headers=auth_headers)
    name = r.json()["csq_name"]

    r2 = client.delete(f"/admin/questions/{COURSE}/{WEEK}/{name}", headers=auth_headers)
    assert r2.status_code == 200

    r3 = client.get(f"/admin/questions/{COURSE}/{WEEK}", headers=auth_headers)
    assert all(q["csq_name"] != name for q in r3.json()["questions"])


def test_delete_all_questions(client, auth_headers):
    for i in range(3):
        client.post(f"/admin/questions/{COURSE}/{WEEK}", json={
            "question_text": f"Q{i}",
            "question_type": "short-answer",
            "options": [],
            "correct_answer": "x",
            "points": 1,
        }, headers=auth_headers)

    r = client.delete(f"/admin/questions/{COURSE}/{WEEK}", headers=auth_headers)
    assert r.status_code == 200

    r2 = client.get(f"/admin/questions/{COURSE}/{WEEK}", headers=auth_headers)
    assert r2.json()["questions"] == []
