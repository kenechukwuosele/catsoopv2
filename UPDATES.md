# UPDATES

## 2026-05-14 — Codebase Refactoring Complete

### Monolithic `main.py` → Modular Structure
Split the 1213-line `main.py` into a proper package:

| File | Lines | Purpose |
|------|-------|---------|
| `api/main.py` | 39 | Entry point, creates tables, registers routers |
| `api/config.py` | 6 | Path constants (CATSOOP_COURSES_DIR, LIVE_FILES_DIR) |
| `api/database.py` | 12 | SQLAlchemy engine, SessionLocal, Base |
| `api/models.py` | 75 | ORM models: User, Lecture, Question, Attempt, Hint, LiveFile |
| `api/schemas.py` | 114 | Pydantic request/response models |
| `api/templates.py` | 386 | CatSooP template generators (quiz, lecture, live panel) |
| `api/websocket.py` | 36 | ConnectionManager + /ws endpoint |
| `api/admin.html` | ~1100 | Admin panel UI (dark theme, sidebar nav) |
| `api/routes/__init__.py` | 0 | Package marker |
| `api/routes/questions.py` | 144 | Dynamic `/{course}/{week}` routes |
| `api/routes/admin.py` | 103 | Admin page + live file upload/download |
| `api/routes/courses.py` | 230 | Course & week CRUD |
| `api/routes/hints.py` | 206 | All hint endpoints + bulk import/export |

No routes or URLs changed. Refactoring was purely structural.

### Hint System (Phases 1–6) — Already Deployed
- Phase 1: Delete confirmation + error handling
- Phase 2: Import/Export UI with preview, progress bar, hints in JSON
- Phase 3A: Backend hint endpoints (with-hints, bulk import, bulk delete)
- Phase 3B: POST question accepts optional hints
- Phase 4: Quiz UI with inline hint creation, enhanced hint button
- Phase 5: Admin panel — questions-with-hints table, course/week filter, up to 5 hints, per-hint AI generation
- Phase 6: Hint usage analytics (stats dashboard: questions with hints, total hints, avg hints/attempt, low-score-with-hints)

### Cleanup
- Removed old backup files: `main.py.bak`, `main.py.backup`, `admin.html.bak`, `main_temp.py`
- Created compressed backup at `/tmp/catsoop-project-backup.tar.gz` (23 MB)

---

## Planned: Windows Server Migration

### Problem
- Hardcoded Linux paths (`/home/alex/`) in `api/config.py`, CatSooP user config, and `AGENTS.md`
- Hardcoded server IP `172.31.184.39` in `templates.py` (lines 205, 286) and `admin.html` (line 594)
- `run.sh` is a Bash script — won't run on Windows

### Steps
1. **Paths**: Replace absolute Linux paths in `api/config.py` with env-var-based or relative-to-project-root logic
2. **IP**: Extract `172.31.184.39:8000` into a single config point (env var or settings file) used by both Python and JS templates
3. **Startup**: Port `run.sh` → PowerShell script (`.ps1`) or batch file (`.bat`)
4. **Dependencies**: Freeze `requirements.txt` from current venv for `pip install` on Windows
5. **CatSooP Config**: Update `cs_data_root` in CatSooP user config per-machine
6. **Test**: End-to-end on clean Windows (Python 3.12 + pip packages + CatSooP)

---

## Planned: Biometric / Webcam Capture

### Overview
Capture webcam snapshots during quizzes for identity verification / proctoring. **Additive only** — no changes to existing quiz flow. Extra data collected alongside attempts.

### Two-Phase Approach

#### Phase A — Snapshot-at-Submit (Quick Win)
- One photo taken when student clicks "Submit Quiz"
- Stored in new `captures` table + filesystem storage
- Viewable from admin panel per attempt

#### Phase B — Periodic Captures + Detection
- Captures every N seconds during quiz (configurable, e.g. 30s)
- Tab-switch flagging (student left the page)
- Face detection (client-side via JS or server-side via OpenCV)
- Admin panel shows flagged sessions (too many tab switches, no face detected)

### Changes Required

| Layer | Change |
|-------|--------|
| **DB** | New `Capture` model: id, attempt_id, username, course, week, filename, captured_at, is_flagged |
| **API** | `POST /{course}/{week}/capture` — upload a webcam frame |
| **API** | `GET /admin/captures/{attempt_id}` — admin view |
| **Storage** | Files under `_captures/{course}/{week}/{username}/` (like live files pattern) |
| **Quiz JS** | In `submitQuiz()`: call `getUserMedia`, snap frame, POST to `/capture` before submitting |
| **Admin UI** | New "Captures" nav panel showing attempts with photos, flag indicators |
| **Config** | `ENABLE_CAPTURES = True/False` toggle in config.py |

### DB Model (new table)
```python
class Capture(Base):
    __tablename__ = "captures"
    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("attempts.id"))
    username = Column(String)
    course = Column(String)
    week = Column(String)
    filename = Column(String)
    captured_at = Column(String)
    is_flagged = Column(Integer, default=0)
    # Flags: 0=normal, 1=no_face, 2=tab_switch
```

### Browser Capture Flow
```javascript
async function captureFrame() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    const video = document.createElement('video');
    video.srcObject = stream;
    await video.play();
    const canvas = document.createElement('canvas');
    canvas.width = 320; canvas.height = 240;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.7));
    stream.getTracks().forEach(t => t.stop());
    return blob;
}
```

### Privacy & UX Considerations
- Prominent notice before quiz: *"This quiz will take periodic webcam photos for verification"*
- Visual indicator (red dot / pulsing border) when camera is active
- Data stored locally, only accessible to instructors via admin panel
- Configurable toggle to disable the feature entirely (`ENABLE_CAPTURES = False`)
- GDPR-compliant: no external transmission, no third-party APIs

---

## Planned: Student Mastery Model

### Overview
Track student knowledge state across questions/courses/weeks, giving instructors a per-student mastery dashboard and students visibility into their own progress.

### Approach — Weighted Evidence Accumulation
Simple, interpretable model built on existing `Attempt` data (no new data collection needed):

- **Per-question mastery** = weighted average of recent attempts (more recent = higher weight, decay factor `0.85`)
- **Per-week mastery** = aggregate of per-question scores
- **Per-course mastery** = rolling window of last N weeks
- **Concept tags** optionally attached to questions, enabling concept-level mastery
- **Struggling threshold**: flagged if mastery < 60% for 2+ consecutive weeks

### Changes Required

| Layer | Change |
|-------|--------|
| **DB** | New `StudentMastery` model OR compute on-the-fly from attempts (no new table) |
| **API** | `GET /admin/mastery/{course}` — all students' mastery for a course |
| **API** | `GET /admin/mastery/{course}/{week}` — per-question breakdown for a week |
| **API** | `GET /admin/mastery/{course}/{week}/{username}` — single student detail |
| **Admin UI** | New "Mastery" nav tab with course selector, student list, heatmap grid |
| **Visualization** | Color-coded mastery matrix (students × weeks), bar charts per student |

### DB Model (new table, optional — can also compute on-the-fly)
```python
class StudentMastery(Base):
    __tablename__ = "student_mastery"
    id = Column(Integer, primary_key=True)
    username = Column(String, index=True)
    course = Column(String, index=True)
    week = Column(String)
    question_id = Column(Integer, ForeignKey("questions.id"))
    mastery_score = Column(Float)        # 0.0 – 1.0
    attempt_count = Column(Integer)
    last_updated = Column(String)
    __table_args__ = (UniqueConstraint("username", "course", "week", "question_id", name="uq_mastery"),)
```

### Mastery Calculation (server-side)
```python
def compute_mastery(user_attempts, decay=0.85):
    weights = [decay ** i for i in range(len(user_attempts))][::-1]
    total_weight = sum(weights)
    return sum(a.score / a.total * w for a, w in zip(user_attempts, weights)) / total_weight
```

### Admin UI Features
- **Mastery Matrix**: rows = students, columns = weeks, cells = color-coded (red < 50%, yellow 50–75%, green > 75%)
- **Student Drill-down**: click a student → per-question breakdown with trend line
- **Export**: CSV download of mastery data
- **Flagged Students**: auto-highlighted if mastery drops below threshold

---

## Planned: Improved Performance Table

### Current State
- Admin panel `loadAttempts()` shows 5 flat columns (username, score, time, date, hint count)
- Quiz page `loadPerformance()` shows 8 columns with basic data
- No sorting, filtering, pagination, or visual indicators

### Improvements

| Feature | Detail |
|---------|--------|
| **Color-coded scores** | Green ≥ 80%, Yellow 50–79%, Red < 50% (badge classes) |
| **Search/filter by username** | Live text input filters rows in real-time |
| **Sortable columns** | Click column header to sort asc/desc (score, date, time spent, hint count) |
| **Pagination** | 25 / 50 / 100 rows per page with page navigation |
| **Question-level breakdown** | Expandable row shows each question's result (✓ / ✗) |
| **Export CSV** | One-click download of filtered table data |
| **Engagement metrics** | Highlight unusually fast submissions (< 30s) or high hint usage |
| **Average row** | Bottom row shows averages for score, time, hint count across all attempts |

### Backend Changes
- Add `GET /{course}/{week}/all_attempts?search=&sort_by=score&sort_dir=desc&page=1&per_page=50` query params
- Return total count for pagination

### Frontend (admin.html)
Replace the current table with a proper data table component:
```html
<input id="att-search" placeholder="Filter by username...">
<select id="att-per-page"><option>25</option><option>50</option><option selected>100</option></select>
<table id="attempts-table">
  <thead>
    <tr>
      <th data-sort="username">User ↕</th>
      <th data-sort="score">Score ↕</th>
      <th data-sort="date">Date ↕</th>
      <th data-sort="time">Time ↕</th>
      <th data-sort="hints">Hints ↕</th>
      <th>Details</th>
    </tr>
  </thead>
  <tbody id="attempts-table-body"></tbody>
</table>
<div id="att-pagination"></div>
```

---

## Planned: RAG-Based Hint Generation (Replace Claude API)

### Problem
Current hint generation calls Anthropic Claude API (`api/routes/hints.py:133`):
- Requires internet access + API key
- No context from course material — hints are generic
- Rate-limited and costs money per call
- External dependency = failure point

### Solution — Local RAG Pipeline
Use Retrieval-Augmented Generation with local models so hints are:
- **Contextual**: retrieved from actual course content, existing hints, and similar questions
- **Offline-capable**: no API calls needed
- **Free**: zero per-generation cost
- **Private**: no data leaves the server

### Architecture

```
User clicks "Generate Hint"
        │
        ▼
Question Text + Metadata
        │
        ▼
┌─────────────────────────────┐
│  1. Retrieve Context        │
│  - Embed question text      │
│  - Query vector DB for      │
│    similar Q&A + hints      │
│  - Query course content     │
│    chunks (lecture notes)   │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  2. Build Prompt            │
│  - Retrieved context        │
│  - Question text            │
│  - Desired hint level (1-5) │
│  - Hint format instruction  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  3. Generate Hint           │
│  - Local LLM (llama.cpp /   │
│    ollama + Phi-3 / Mistral)│
│  - OR lightweight generator │
│    (template-based from     │
│    retrieved examples)      │
└──────────┬──────────────────┘
           │
           ▼
         Hint text returned to UI
```

### Components

| Component | Tech |
|-----------|------|
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` (lightweight, ~80MB) |
| **Vector store** | ChromaDB (persistent, on-disk, no server needed) |
| **Retrieval** | Top-3 most similar questions + their hints |
| **Course content ingestion** | Chunk `.catsoop` lecture files into sentences/paragraphs → embed → store |
| **Generator** | Option A: ollama + Phi-3-mini (~3.8B, runs on CPU) — best quality |
| | Option B: Template-based from retrieved hints — zero additional deps |
| | Option C: Keep Claude as optional fallback (configurable) |

### DB Changes
- New `ContentChunk` model for ingested course content
- ChromaDB persists to `_vectors/` directory in project root

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/admin/rag/ingest/{course}/{week}` | Chunk and embed course content |
| `GET` | `/admin/rag/status` | Show what's been indexed |
| `POST` | `/admin/rag/generate-hint` | Generate hint using RAG (replaces Claude endpoint) |
| `DELETE` | `/admin/rag/clear` | Clear vector store |

### Data Flow for Hint Generation (replaces `/admin/hints/generate`)

```python
async def generate_hint_rag(question_text, hint_level, db):
    # 1. Get embedding
    embedding = embed_model.encode(question_text)
    
    # 2. Retrieve similar questions + hints from vector store
    results = vector_store.query(embedding, n_results=3)
    
    # 3. Retrieve relevant course content chunks
    content_chunks = vector_store.query(embedding, 
        collection="course_content", n_results=5)
    
    # 4. Build prompt with context
    prompt = f"""Course context: {content_chunks}
Similar Q&A: {results}
Question: {question_text}
Generate hint level {hint_level}:"""

    # 5. Generate via local LLM or fallback
    if use_local_llm:
        hint = await ollama.generate(prompt)
    else:
        hint = template_from_retrieved(results, hint_level)
    
    return hint
```

### Migration Path
1. Add ChromaDB + sentence-transformers to dependencies
2. Create seed command to ingest existing hints + questions into vector store
3. Add course content ingestion per week
4. Replace Claude endpoint with RAG endpoint, keep Claude as optional fallback via config flag
5. Remove Claude API key dependency entirely once RAG quality is verified

### Dependencies to Add
```txt
chromadb>=0.4.0
sentence-transformers>=2.2.0
ollama>=0.1.0   # optional, for local LLM generation
```
