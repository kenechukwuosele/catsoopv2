# CU Quiz App — API Endpoint Reference

Base URLs: **FastAPI** `http://<host>:8000` | **CatSooP** `http://<host>:7667`

Auth types:
- **public** — no token required
- **require_user** — student JWT (`Authorization: Bearer <token>`)
- **require_admin** — admin/lecturer JWT
- **require_admin_or_lecturer** — either of the above
- **token (WS)** — JWT passed as `?token=` query param

---

## Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/admin/login` | public | Authenticate with username+password; returns JWT. Tries: system admin → FastAPI lecturer → CatSooP instructor |
| GET | `/admin/auto-token` | public | Issue JWT with no password (only when `CU_QUIZ_ADMIN_PASSWORD` is unset) |
| GET | `/admin` | public | Serve admin panel HTML shell (login is client-side) |

---

## Live Files (Course Materials)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/admin/live-file` | require_admin | Upload course material (PDF, image, doc). Body: `{course, week, filename, content_type, data_base64}`. Max 20 MB. |
| GET | `/admin/live-file/{course}/{week}` | require_admin | Get metadata for uploaded live file (admin only) |
| DELETE | `/admin/live-file/{course}/{week}` | require_admin | Remove uploaded live file from disk and DB |
| GET | `/live-file-info/{course}/{week}` | public | Get basic file info (`{filename, content_type}`) |
| GET | `/live-file/{course}/{week}` | public | Download or view file inline. Query: `?download=true` for attachment mode |

---

## Course & Week Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/courses` | require_admin | List all courses with metadata |
| POST | `/admin/courses` | require_admin | Create course. Body: `{course_id, long_name, course_number, description, icon}` |
| PUT | `/admin/courses/{course_id}` | require_admin | Update course metadata |
| DELETE | `/admin/courses/{course_id}` | require_admin | Delete course and DB records |
| GET | `/admin/courses/{course_id}/weeks` | require_admin | List weeks in a course |
| POST | `/admin/courses/{course_id}/weeks` | require_admin | Create week (scaffolds lecture, problems, quiz, example_questions files) |
| PUT | `/admin/courses/{course_id}/weeks/{week_id}` | require_admin | Update week metadata |
| DELETE | `/admin/courses/{course_id}/weeks/{week_id}/submissions` | require_admin | Clear all student submissions/grades for a week |
| POST | `/admin/repair` | require_admin | Regenerate quiz templates, example questions, leaderboard widgets, and gradebook files for all courses |
| GET | `/admin/performance` | require_admin | Aggregate grade statistics across all courses/weeks |

---

## Questions (stored in `quiz.catsoop`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/questions/{course}/{week}` | require_admin | List all questions for a week |
| POST | `/admin/questions/{course}/{week}` | require_admin | Add a question. Body: `{question_text, question_type, options, correct_answer, points}` |
| DELETE | `/admin/questions/{course}/{week}/{csq_name}` | require_admin | Delete a specific question and its hints |
| DELETE | `/admin/questions/{course}/{week}` | require_admin | Delete all questions for a week |
| POST | `/admin/bulk-import/{course}/{week}` | require_admin | Batch import questions. Body: `{questions: [...], clear_existing: bool}` |

---

## Hints (stored in `_hint_store/`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/hints/{course}/{week}/{csq_name}` | require_user | Get all hints for a question |
| POST | `/admin/hints/{course}/{week}/{csq_name}` | require_admin | Save/update hints. Body: `{hints: ["text1", ...]}` |
| DELETE | `/admin/hints/{course}/{week}/{csq_name}` | require_admin | Delete all hints for a question |
| GET | `/admin/hints/stats/{course}/{week}` | require_admin | Count of questions with hints and total hints |
| POST | `/admin/hints/generate/{course}/{week}/{csq_name}` | require_admin | AI-generate 3 progressive hints (RAG + Ollama). Rate-limit: 30/min |
| POST | `/admin/hints/generate-single/{course}/{week}/{csq_name}` | require_admin | Generate a single hint at a specific level. Rate-limit: 30/min |
| POST | `/admin/hints/generate-all/{course}/{week}` | require_admin | Generate hints for all questions in a week |

---

## Grades

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/{course}/{week}/grades` | require_admin | Read CatSooP cslog; returns per-student scores with per-question breakdown |
| GET | `/{course}/gradebook` | CatSooP page | Instructor-only gradebook page; access requires admin/instructor/lecturer role |

---

## Gamification (XP, Streaks, Badges, Leaderboard)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/{course}/{week}/quiz-complete` | require_user | Award XP/badges on quiz completion. Deduped by `ProcessedQuizEvent`. Rate-limit: 5/min |
| GET | `/{course}/leaderboard` | public | Top-10 ranked leaderboard with XP, streak, badge counts |
| GET | `/{course}/my-stats` | public | User stats: XP, rank, streak, badges. Query: `?username=` |
| GET | `/{course}/is-lecturer` | public | Check if user is admin/lecturer for a course. Query: `?username=` |

---

## Face Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/{course}/face-status` | require_user | Check if user has a face enrollment. Query: `?username=` |
| POST | `/{course}/enroll-face` | require_user | Enroll with 128-dim FaceNet descriptor. Body: `{descriptor: [128 floats]}` |
| POST | `/{course}/verify-face` | require_user | Verify face; Euclidean distance < 0.5 = pass. Body: `{descriptor: [128 floats]}`. Rate-limit: 10/min |
| GET | `/admin/face-enrollments` | require_admin | List all enrolled users with timestamps |
| DELETE | `/admin/face-enrollments/{username}` | require_admin | Remove a user's face enrollment |

---

## Engagement & Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/{course}/{week}/engagement` | require_user | Log engagement sample (webcam affect state, face detection, eye/mouth ratios) |
| GET | `/admin/engagement/{course}/{week}` | require_admin | Per-student engagement analytics: sessions, samples, face %, affect breakdown |

---

## Lecturer Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/lecturers` | require_admin | List all lecturers |
| POST | `/admin/lecturers` | require_admin | Register lecturer. Body: `{username, name, email, password, courses: [...]}` |
| DELETE | `/admin/lecturers/{username}` | require_admin | Remove a lecturer account |
| POST | `/admin/sync-instructors` | require_admin | Import CatSooP Instructor-role users into the lecturers table (idempotent) |
| GET | `/lecturer` | public | Redirect to admin panel (302) |
| POST | `/lecturer/login` | public | Authenticate lecturer; returns JWT |
| GET | `/lecturer/students` | require_admin_or_lecturer | List students in a course |
| POST | `/lecturer/students/{username}/reset-password` | require_admin_or_lecturer | Reset a student's CatSooP password |

---

## RAG (Retrieval-Augmented Generation)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/admin/rag/ingest/{course}/{week}` | require_admin | Index course content and Q&A pairs with embeddings |
| GET | `/admin/rag/status` | require_admin | Show indexed chunk count and Q&A pair count |
| DELETE | `/admin/rag/clear` | require_admin | Clear all vector store indices |
| POST | `/admin/rag/generate-hint` | require_admin | Generate a hint using RAG + Ollama |
| POST | `/admin/rag/generate-questions/{course}/{week}` | require_admin | Generate quiz questions from course content |

---

## WebSocket

| Protocol | Path | Auth | Description |
|----------|------|------|-------------|
| WS | `/ws` | token (query param) | Real-time room-based messaging. Messages: `JOIN`, `LEAVE`, `SUBMISSION`, `AFFECT_CHANGE`, `HINT_USED`, `PUSH_HINT`, `INSTRUCTOR_MESSAGE`, `QUIZ_DONE` |

---

## Totals

| Category | Count |
|----------|-------|
| GET | 21 |
| POST | 22 |
| PUT | 2 |
| DELETE | 10 |
| WebSocket | 1 |
| **Total** | **56** |
