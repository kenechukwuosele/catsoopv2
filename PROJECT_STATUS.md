# CU Quiz App — Project Status

> Last updated: 2026-05-07

## Quick Restore
A compressed backup exists at `/tmp/catsoop-project-backup.tar.gz` (23MB).
To restore: `tar xzf /tmp/catsoop-project-backup.tar.gz -C /home/alex/.local/share/`

## Architecture
- **CatSooP** runs on port 7667 (frontend for course content)
- **FastAPI** runs on `172.31.184.39:8000` (backend API, admin panel, hints, quizzes)
- **SQLite** database at `/home/alex/.local/share/catsoop/questions.db`
- Courses live under `/home/alex/.local/share/catsoop/courses/`

## File Structure (api/)
```
api/
├── main.py              (39 lines)   - FastAPI app entry, router registration
├── config.py            (6 lines)    - Path constants (CATSOOP_COURSES_DIR, etc)
├── database.py          (12 lines)   - SQLAlchemy engine, SessionLocal, Base
├── models.py            (75 lines)   - ORM: User, Lecture, Question, Attempt, Hint, LiveFile
├── schemas.py           (114 lines)  - Pydantic models for all API requests/responses
├── templates.py         (386 lines)  - CatSooP template generators (quiz, lecture, problems, live panel)
├── websocket.py         (36 lines)   - ConnectionManager + /ws endpoint
├── admin.html           (~1100 lines) - Admin panel UI (dark theme, sidebar nav)
└── routes/
    ├── __init__.py       (empty)     - Makes routes/ a Python package
    ├── questions.py      (144 lines) - Dynamic /{course}/{week} routes
    ├── admin.py          (103 lines) - /admin page + live file upload/download
    ├── courses.py        (230 lines) - /admin/courses + /admin/courses/{id}/weeks CRUD
    └── hints.py          (206 lines) - All hint endpoints + bulk question import/export
```

## All API Endpoints

### Dynamic (course/week-scoped)
| Method | Path | Function |
|--------|------|----------|
| GET | `/{course}/{week}/example_questions` | Get all questions for a course/week |
| POST | `/{course}/{week}/example_questions` | Create a question (accepts optional hints) |
| DELETE | `/{course}/{week}/example_questions/{id}` | Delete a single question |
| POST | `/{course}/{week}/submit_attempt` | Submit quiz attempt with engagement metrics |
| GET | `/{course}/{week}/all_attempts` | Get all student attempts for performance table |

### Admin Panel & Files
| Method | Path | Function |
|--------|------|----------|
| GET | `/admin` | Serves admin.html |
| POST | `/admin/live-file` | Upload a live file (base64) |
| GET | `/admin/live-file/{course}/{week}` | Get live file metadata |
| GET | `/live-file/{course}/{week}` | Download/preview live file (inline or attachment) |

### Courses & Weeks
| Method | Path | Function |
|--------|------|----------|
| GET | `/admin/courses` | List all courses (reads from filesystem) |
| POST | `/admin/courses` | Create new course (creates directory + files) |
| PUT | `/admin/courses/{id}` | Edit course metadata |
| GET | `/admin/courses/{id}/weeks` | List weeks in a course |
| POST | `/admin/courses/{id}/weeks` | Create week (generates all .catsoop files) |
| PUT | `/admin/courses/{id}/weeks/{week_id}` | Edit week settings |

### Hints
| Method | Path | Function |
|--------|------|----------|
| GET | `/admin/questions/{course}/{week}/with-hints` | Get questions with their hints |
| POST | `/admin/questions-with-hints` | Bulk import questions with hints |
| DELETE | `/admin/questions/{course}/{week}` | Delete all questions in a course/week |
| POST | `/admin/hints` | Save/edit hints for a question |
| GET | `/admin/hints/stats` | Hint usage analytics (questions with hints, total hints, avg usage, low score + hints) |
| POST | `/admin/hints/generate` | AI-generate 3 hints via Anthropic API |
| POST | `/admin/hints/generate-single` | AI-generate a single hint (1-5 level) |
| GET | `/admin/hints/{question_id}` | Get hints for a question |
| DELETE | `/admin/hints/{question_id}` | Delete all hints for a question |

### WebSocket
| Path | Function |
|------|----------|
| `/ws` | Real-time connection for broadcasting new submissions |

## Features Implemented (All Phases Complete)

### Phase 1 — Delete Question Button
- Confirm dialog + error handling + inline status feedback

### Phase 2 — Import/Export Overhaul
- Export includes hints per question
- Import has file preview, progress bar, "clear existing" checkbox
- Backward-compatible with both legacy and new JSON formats

### Phase 3A — New Backend Hint Endpoints
- GET /admin/questions/{course}/{week}/with-hints
- POST /admin/questions-with-hints (bulk import)
- DELETE /admin/questions/{course}/{week} (bulk delete)

### Phase 3B — POST Accepts Hints
- Optional `hints` array in question creation requests

### Phase 4 — Quiz Page UI
- Inline hint creation (expandable section, "+ Add Hint")
- Enhanced hint button shows progress, disables when exhausted
- Results show hint usage per question
- Import/Export tab has preview, progress, status messages

### Phase 5 — Admin Panel Hint Management
- Questions-with-hints table (ID, text, type, hint count, Edit/Delete)
- Course/week filter dropdowns
- Enhanced hint form supports up to 5 hints (was 3)
- Individual AI generation buttons (✨) per hint level
- loadExistingHints() populates form when editing
- loadHintsTable() fetches and displays questions with hints

### Phase 6 — Hint Usage Analytics
- GET /admin/hints/stats returns:
  - `questions_with_hints` — distinct questions with hints
  - `total_hints` — total hint count
  - `avg_hints_per_attempt` — average hints used per attempt
  - `low_score_with_hints` — attempts where hints used but score < 50%
- Stats dashboard on top of Hints panel (4 stat cards)

## How to Start the Server
```bash
cd /home/alex/.local/share/catsoop
source /home/alex/catsoop-env/bin/activate
nohup python3 -m uvicorn api.main:app --host 172.31.184.39 --port 8000 > /tmp/fastapi.log 2>&1 &
```

Also start CatSooP via `./run.sh` in the catsoop directory (uses `catsoop_engine`).

## Admin Panel
- `http://172.31.184.39:8000/admin` — Admin panel
- `http://172.31.184.39:8000/docs` — FastAPI Swagger docs

## Existing Courses
- Biology (331), ENGLISH (421), Physics, Programming, Sports

## DB Models
- User, Lecture, Question, Attempt, Hint, LiveFile
- Attempt has: hint_count, click_count, seconds_spent columns
- Hint has: question_id, hint_number, hint_text

## Key Notes
- The quiz template (`generate_quiz_template` in templates.py) is a massive f-string embedded in CatSooP .catsoop files
- Live file panel is embedded directly in lecture files (no #include needed)
- `Content-Disposition: inline` for previews, `?download=1` for downloads
- `blob:` URLs used for rendering to prevent download managers from auto-triggering
