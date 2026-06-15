# AI Generator from File — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single "AI Generator" admin panel that lets instructors upload a PDF/Word/text file and with one click generate a lecture notes page, quiz questions, and hints — all reviewed in a preview before saving.

**Architecture:** A new `POST /admin/generate-from-file/{course}/{week}` endpoint parses the file (pdfplumber/python-docx), embeds text chunks into a dedicated `live_files` ChromaDB collection, then calls Ollama in sequence for a lecture HTML summary and N questions with embedded hints, saving an ephemeral preview JSON to `_live_gen/`. A second `POST /admin/confirm-generated/{job_id}` endpoint writes everything to disk (quiz.catsoop, _hint_store, lecture_ai.catsoop) only after instructor approval. A new "AI Generator" nav tab in the admin panel drives the whole flow with a file picker, review panel, and confirm button.

**Tech Stack:** Python (pdfplumber, python-docx), FastAPI, ChromaDB, sentence-transformers, Ollama (phi3:mini), vanilla JS (existing admin panel patterns).

---

## File Map

| Action | Path |
|--------|------|
| Create | `api/services/file_parser.py` |
| Create | `api/routes/generate.py` |
| Create | `api/tests/test_file_parser.py` |
| Modify | `api/services/rag_service.py` — add `ingest_live_file_text()`, `build_lecture_summary_prompt()` |
| Modify | `api/config.py` — add `LIVE_GEN_DIR` |
| Modify | `api/main.py` — register generate router |
| Modify | `api/admin.html` — add "AI Generator" nav item + panel HTML |
| Modify | `api/static/admin/admin.js` — add `generateFromFile()`, `renderAgQuestionsPreview()`, `confirmGenerated()`, `cancelGenerated()` |

---

## Task 1: Install dependencies

**Files:** no code changes

- [ ] **Step 1: Install pdfplumber and python-docx**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
pip install pdfplumber python-docx
```

Expected output: `Successfully installed pdfplumber-X.Y.Z python-docx-X.Y.Z` (exact versions vary)

- [ ] **Step 2: Verify imports work**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
python3 -c "import pdfplumber; import docx; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd ~/.local/share/catsoop && git add -A && git commit -m "$(cat <<'EOF'
chore: install pdfplumber and python-docx for file text extraction

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add LIVE_GEN_DIR to config

**Files:**
- Modify: `api/config.py`

- [ ] **Step 1: Add the constant**

In `api/config.py`, append after the last `OLLAMA_MODEL` block (after line 31):

```python
LIVE_GEN_DIR = os.environ.get(
    "LIVE_GEN_DIR",
    os.path.join(PROJECT_ROOT, "_live_gen")
)
```

- [ ] **Step 2: Verify**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
python3 -c "from api.config import LIVE_GEN_DIR; print(LIVE_GEN_DIR)"
```

Expected: prints a path ending in `_live_gen`

- [ ] **Step 3: Commit**

```bash
git add api/config.py && git commit -m "$(cat <<'EOF'
feat: add LIVE_GEN_DIR config constant for ephemeral generation previews

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Create file_parser service

**Files:**
- Create: `api/services/file_parser.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/test_file_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `api/tests/__init__.py` (empty):
```python
```

Create `api/tests/test_file_parser.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


def test_plain_text_utf8():
    from api.services.file_parser import extract_text
    content = "Hello world. This is a test document."
    result = extract_text(content.encode("utf-8"), "text/plain", "notes.txt")
    assert result == content


def test_markdown_by_content_type():
    from api.services.file_parser import extract_text
    content = "# Title\n\nSome content here."
    result = extract_text(content.encode("utf-8"), "text/markdown", "notes.md")
    assert result == content


def test_txt_by_filename_extension():
    from api.services.file_parser import extract_text
    content = "plain text by extension"
    result = extract_text(content.encode("utf-8"), "application/octet-stream", "notes.txt")
    assert result == content


def test_unsupported_type_raises():
    from api.services.file_parser import extract_text
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(b"data", "image/png", "photo.png")


def test_zip_raises():
    from api.services.file_parser import extract_text
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(b"PK...", "application/zip", "archive.zip")


def test_pdf_extraction():
    from api.services.file_parser import extract_text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "This is page one content from the lecture notes."
    mock_pdf_ctx = MagicMock()
    mock_pdf_ctx.__enter__ = lambda s: mock_pdf_ctx
    mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
    mock_pdf_ctx.pages = [mock_page]
    with patch("pdfplumber.open", return_value=mock_pdf_ctx):
        result = extract_text(b"%PDF-1.4 fake", "application/pdf", "lecture.pdf")
    assert "page one content" in result


def test_pdf_skips_short_pages():
    from api.services.file_parser import extract_text
    short_page = MagicMock()
    short_page.extract_text.return_value = "Hi"
    long_page = MagicMock()
    long_page.extract_text.return_value = "This is a longer page with substantive content in it."
    mock_pdf_ctx = MagicMock()
    mock_pdf_ctx.__enter__ = lambda s: mock_pdf_ctx
    mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
    mock_pdf_ctx.pages = [short_page, long_page]
    with patch("pdfplumber.open", return_value=mock_pdf_ctx):
        result = extract_text(b"%PDF-1.4 fake", "application/pdf", "lecture.pdf")
    assert "Hi" not in result
    assert "longer page" in result


def test_pdf_detected_by_filename():
    from api.services.file_parser import extract_text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Content detected by filename extension."
    mock_pdf_ctx = MagicMock()
    mock_pdf_ctx.__enter__ = lambda s: mock_pdf_ctx
    mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
    mock_pdf_ctx.pages = [mock_page]
    with patch("pdfplumber.open", return_value=mock_pdf_ctx):
        result = extract_text(b"%PDF fake", "application/octet-stream", "slides.pdf")
    assert "Content detected" in result


def test_docx_extraction():
    from api.services.file_parser import extract_text
    para_h1 = MagicMock()
    para_h1.text = "Introduction"
    para_h1.style.name = "Heading 1"
    para_body = MagicMock()
    para_body.text = "This is the body paragraph text."
    para_body.style.name = "Normal"
    para_empty = MagicMock()
    para_empty.text = ""
    para_empty.style.name = "Normal"
    mock_doc = MagicMock()
    mock_doc.paragraphs = [para_h1, para_body, para_empty]
    with patch("docx.Document", return_value=mock_doc):
        result = extract_text(
            b"fake docx bytes",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "notes.docx",
        )
    assert "# Introduction" in result
    assert "body paragraph text" in result
    lines = [l for l in result.split("\n") if l.strip()]
    assert "" not in lines  # empty paragraphs stripped
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
PYTHONPATH=$(pwd) python -m pytest api/tests/test_file_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'api.services.file_parser'`

- [ ] **Step 3: Write the implementation**

Create `api/services/file_parser.py`:

```python
import io


def extract_text(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Return plain text extracted from uploaded file bytes.

    Supports: PDF (pdfplumber), DOCX (python-docx), TXT/MD/CSV (UTF-8).
    Raises ValueError for unsupported types.
    """
    ct = content_type.lower()
    fn = filename.lower()

    if ct == "application/pdf" or fn.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if ct in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or fn.endswith((".docx", ".doc")):
        return _extract_docx(file_bytes)
    if ct in ("text/plain", "text/markdown", "text/csv") or fn.endswith((".txt", ".md", ".csv")):
        return file_bytes.decode("utf-8", errors="ignore")

    raise ValueError(
        f"Unsupported file type for text extraction: {content_type} / {filename}. "
        "Upload a PDF, Word document (.docx), or plain text file (.txt, .md)."
    )


def _extract_pdf(file_bytes: bytes) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if len(page_text.strip()) >= 20:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = para.style.name
        if style.startswith("Heading"):
            try:
                level = int(style.replace("Heading ", ""))
                text = "#" * level + " " + text
            except ValueError:
                pass
        lines.append(text)
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
PYTHONPATH=$(pwd) python -m pytest api/tests/test_file_parser.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add api/services/file_parser.py api/tests/__init__.py api/tests/test_file_parser.py
git commit -m "$(cat <<'EOF'
feat: add file_parser service for PDF/DOCX/text extraction

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Extend RAG service with live-file ingestion and lecture prompt

**Files:**
- Modify: `api/services/rag_service.py`

- [ ] **Step 1: Add `ingest_live_file_text` and `build_lecture_summary_prompt` methods**

At the end of the `RAGService` class body (before the `status` method), add these two methods:

```python
    def ingest_live_file_text(self, course: str, week: str, text: str, source_filename: str) -> int:
        """Chunk and embed raw text into the dedicated live_files ChromaDB collection.

        Replaces any prior embeddings for the same course/week so re-uploads are safe.
        """
        from datetime import datetime

        col = self._get_collection("live_files")
        if not col:
            return 0

        # Remove stale chunks for this course/week before re-ingesting
        try:
            existing = col.get(where={"course": course, "week": week})
            if existing.get("ids"):
                col.delete(ids=existing["ids"])
        except Exception:
            pass

        chunks = self._chunk_text(text)
        for chunk_text, chunk_idx in chunks:
            doc_id = f"live_{course}_{week}_{source_filename}_{chunk_idx}"
            emb = self._get_embedding(chunk_text)
            col.add(
                ids=[doc_id],
                embeddings=[emb],
                metadatas=[{
                    "course": course,
                    "week": week,
                    "source_file": source_filename,
                    "chunk_index": chunk_idx,
                    "timestamp": datetime.now().isoformat(),
                }],
                documents=[chunk_text],
            )
        return len(chunks)

    def build_lecture_summary_prompt(self, content_chunks: list[dict]) -> str:
        """Build the Ollama prompt for generating an HTML lecture summary."""
        context = "\n".join(f"- {c['text'][:500]}" for c in content_chunks[:8])
        return (
            "Based on the following course material, write a structured lecture summary in HTML.\n"
            "Use <h2> for main topics, <p> for explanations, <ul><li> for key points.\n"
            "Keep it under 600 words. Be clear and student-friendly. No <html>/<body> wrapper.\n\n"
            f"Course material:\n{context}\n\n"
            "HTML:"
        )
```

- [ ] **Step 2: Verify the class still imports cleanly**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
python3 -c "from api.services.rag_service import RAGService; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Also update `status()` to report the live_files collection count**

In the `status` method, change:
```python
            for name in ["course_content", "qa_hints"]:
```
to:
```python
            for name in ["course_content", "qa_hints", "live_files"]:
```

And in `clear()`, change:
```python
            for name in ["course_content", "qa_hints"]:
```
to:
```python
            for name in ["course_content", "qa_hints", "live_files"]:
```

- [ ] **Step 4: Run all existing tests to confirm no regressions**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
python -m pytest catsoop_engine/test/ -v
```

Expected: same pass/fail count as before this change

- [ ] **Step 5: Commit**

```bash
git add api/services/rag_service.py
git commit -m "$(cat <<'EOF'
feat: add live_files RAG ingestion and lecture summary prompt to RAGService

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Create the generate route

**Files:**
- Create: `api/routes/generate.py`

- [ ] **Step 1: Write the route file**

Create `api/routes/generate.py`:

```python
import json
import os
import re
import uuid
import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_admin
from ..validation import safe_course, safe_week
from ..services.rag_service import RAGService
from ..services.file_parser import extract_text
from ..services.ollama_client import OllamaClient
from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL, LIVE_GEN_DIR, CATSOOP_COURSES_DIR


class GenerateFromFileRequest(BaseModel):
    filename: str
    data_base64: str
    content_type: str
    question_type: str = "multiple-choice"
    num_questions: int = 5


class ConfirmGeneratedRequest(BaseModel):
    questions: list[dict]
    lecture_html: str


def get_router() -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_admin)])
    rag = RAGService.get_instance()
    ollama = OllamaClient(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)

    @router.post("/admin/generate-from-file/{course}/{week}")
    async def generate_from_file(course: str, week: str, body: GenerateFromFileRequest):
        course = safe_course(course)
        week = safe_week(week)

        # 1. Decode
        try:
            file_bytes = base64.b64decode(body.data_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 data")

        num_questions = max(1, min(20, body.num_questions))
        supported_types = {"multiple-choice", "short-answer", "numerical", "checkbox"}
        question_type = body.question_type if body.question_type in supported_types else "multiple-choice"

        # 2. Extract text
        try:
            text = extract_text(file_bytes, body.content_type, body.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if len(text.strip()) < 100:
            raise HTTPException(
                status_code=400,
                detail="Extracted text is too short (under 100 chars). Upload a text-rich document.",
            )

        # 3. Ingest into live_files ChromaDB collection
        try:
            chunk_count = rag.ingest_live_file_text(course, week, text, body.filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to ingest file: {e}")

        # 4. Retrieve chunks for generation
        query = "key concepts"
        content_chunks = rag.retrieve_similar(query, "live_files", n=8)
        if not content_chunks:
            content_chunks = [{"text": text[:2000]}]

        # 5. Generate lecture HTML summary
        lecture_html = ""
        try:
            lecture_prompt = rag.build_lecture_summary_prompt(content_chunks)
            system_lec = (
                "You are a university lecturer. Output ONLY valid HTML, "
                "no markdown, no code fences, no <html>/<body> wrappers."
            )
            lecture_html = await ollama.generate(lecture_prompt, system=system_lec, max_tokens=600)
            lecture_html = re.sub(r"^```[a-z]*\s*", "", lecture_html.strip())
            lecture_html = re.sub(r"\s*```$", "", lecture_html.strip())
        except Exception as e:
            lecture_html = f"<p><em>Lecture summary generation failed: {e}</em></p>"

        # 6. Generate questions with embedded hints
        system_q = "You are a university exam question writer. Output ONLY valid JSON, nothing else."
        questions = []
        errors = []

        for i in range(num_questions):
            raw = ""
            try:
                prompt = rag.build_question_generation_prompt(content_chunks, question_type)
                raw = await ollama.generate(prompt, system=system_q, max_tokens=350)
                raw = re.sub(r"^```[a-z]*\s*", "", raw.strip())
                raw = re.sub(r"\s*```$", "", raw.strip())
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                errors.append({"index": i, "error": f"JSON parse: {e}", "raw": raw[:200]})
                continue
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
                continue

            q_text = (data.get("text") or data.get("question_text") or "").strip()
            if not q_text:
                errors.append({"index": i, "error": "empty question text"})
                continue

            options = data.get("options") or []
            correct = data.get("correct_answer") or ""
            if isinstance(correct, list):
                correct = ", ".join(correct)
            hints_raw = data.get("hints") or []

            questions.append({
                "question_text": q_text,
                "question_type": question_type,
                "options": options,
                "correct_answer": str(correct),
                "points": 1,
                "hints": [{"number": j + 1, "text": h} for j, h in enumerate(hints_raw[:3])],
            })

        # 7. Persist ephemeral preview
        job_id = uuid.uuid4().hex
        os.makedirs(LIVE_GEN_DIR, exist_ok=True)
        preview = {
            "job_id": job_id,
            "course": course,
            "week": week,
            "filename": body.filename,
            "created_at": datetime.now().isoformat(),
        }
        with open(os.path.join(LIVE_GEN_DIR, f"{job_id}.json"), "w") as f:
            json.dump(preview, f)

        return {
            "job_id": job_id,
            "chunk_count": chunk_count,
            "lecture_html": lecture_html,
            "questions": questions,
            "errors": errors,
        }

    @router.post("/admin/confirm-generated/{job_id}")
    async def confirm_generated(job_id: str, body: ConfirmGeneratedRequest):
        # Validate job_id is a 32-char hex string to prevent path traversal
        if len(job_id) != 32 or not all(c in "0123456789abcdef" for c in job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")

        job_path = os.path.join(LIVE_GEN_DIR, f"{job_id}.json")
        if not os.path.exists(job_path):
            raise HTTPException(status_code=404, detail="Preview not found or already confirmed")

        with open(job_path) as f:
            preview = json.load(f)

        course = preview["course"]
        week = preview["week"]
        filename = preview.get("filename", "uploaded file")

        # 1. Write questions to quiz.catsoop
        from ..routes.file_questions import append_questions

        saved_count = 0
        csq_names = []
        if body.questions:
            try:
                csq_names = append_questions(course, week, body.questions)
                saved_count = len(csq_names)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to write questions: {e}")

        # 2. Save hints for each question
        data_root = os.path.dirname(CATSOOP_COURSES_DIR)
        hint_store_base = os.path.join(data_root, "_hint_store", course, week)
        hints_saved = 0
        for csq_name, q in zip(csq_names, body.questions):
            hints = q.get("hints") or []
            if hints:
                os.makedirs(hint_store_base, exist_ok=True)
                hint_file = os.path.join(hint_store_base, f"{csq_name}.json")
                with open(hint_file, "w") as f:
                    json.dump(hints, f)
                hints_saved += 1

        # 3. Write lecture_ai.catsoop
        lecture_path = ""
        lecture_html = (body.lecture_html or "").strip()
        if lecture_html:
            week_dir = os.path.join(CATSOOP_COURSES_DIR, course, week)
            os.makedirs(week_dir, exist_ok=True)
            lecture_file = os.path.join(week_dir, "lecture_ai.catsoop")
            with open(lecture_file, "w") as f:
                f.write(
                    f'<python>\ncs_content_header = "AI Lecture Notes: {filename}"\n</python>\n\n'
                    f"{lecture_html}\n"
                )
            lecture_path = f"{course}/{week}/lecture_ai"

        # 4. Clean up preview file
        os.remove(job_path)

        return {
            "saved_questions": saved_count,
            "hints_saved": hints_saved,
            "lecture_path": lecture_path,
        }

    return router
```

- [ ] **Step 2: Verify imports**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
python3 -c "from api.routes.generate import get_router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add api/routes/generate.py
git commit -m "$(cat <<'EOF'
feat: add generate-from-file and confirm-generated endpoints

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Register generate router in main.py

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Add the import and router registration**

In `api/main.py`, after the existing `from .routes.lecturer import get_router as get_lecturer_router` import line (line 27), add:

```python
from .routes.generate import get_router as get_generate_router
```

Then after `app.include_router(get_lecturer_router())` (line 131), add:

```python
app.include_router(get_generate_router())
```

- [ ] **Step 2: Verify FastAPI app starts**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
python3 -c "from api.main import app; print('routes:', len(app.routes))"
```

Expected: prints a number ≥ the prior count (confirms no import errors)

- [ ] **Step 3: Commit**

```bash
git add api/main.py
git commit -m "$(cat <<'EOF'
feat: register generate router in FastAPI app

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Add AI Generator panel to admin.html

**Files:**
- Modify: `api/admin.html`

- [ ] **Step 1: Add nav item**

In `api/admin.html`, find the `<div class="nav-item" onclick="showPanel('livefiles')">` line and insert the new nav item **after** it:

```html
    <div class="nav-item" onclick="showPanel('aigenerate')"><span>🤖</span> AI Generator</div>
```

- [ ] **Step 2: Add panel HTML**

In `api/admin.html`, find the closing `</div>` that ends the `<!-- LIVE FILES -->` panel section (just before `<!-- QUESTIONS`). Insert the following new panel block between them:

```html
    <!-- AI GENERATOR -->
    <div class="panel" id="panel-aigenerate">
      <div class="panel-header"><h1>AI Generator</h1><p>Upload a file — get lecture notes, quiz questions, and hints in one click</p></div>

      <div class="card">
        <div class="card-title">📤 Upload &amp; Generate</div>
        <p style="font-size:0.82em;color:var(--muted);margin:0 0 12px;">Supports PDF, Word (.docx), and plain text (.txt, .md). Generation may take 1–3 minutes depending on file size and model speed.</p>
        <div class="form-grid">
          <div class="field"><label>Course</label><select id="ag-course" onchange="loadWeeksForCourse('ag-course','ag-week')"><option value="">Select course...</option></select></div>
          <div class="field"><label>Week</label><select id="ag-week"><option value="">Select week...</option></select></div>
          <div class="field full"><label>File</label><input type="file" id="ag-file" accept=".pdf,.docx,.doc,.txt,.md,.csv"/></div>
          <div class="field"><label># Questions</label><input type="number" id="ag-num-questions" value="5" min="1" max="20"/></div>
          <div class="field"><label>Question Type</label>
            <select id="ag-question-type">
              <option value="multiple-choice">Multiple Choice</option>
              <option value="short-answer">Short Answer</option>
              <option value="numerical">Numerical</option>
              <option value="checkbox">Checkbox</option>
            </select>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" id="ag-generate-btn" onclick="generateFromFile()">🤖 Generate</button>
          <span id="ag-status" style="font-size:0.8em;color:var(--muted);"></span>
        </div>
      </div>

      <div id="ag-preview-section" style="display:none;">
        <div class="card">
          <div class="card-title">📖 Generated Lecture Notes</div>
          <p style="font-size:0.82em;color:var(--muted);margin:0 0 8px;">Edit the HTML below if needed, then click Confirm to save.</p>
          <textarea id="ag-lecture-html" rows="10" style="width:100%;font-family:var(--mono);font-size:0.82em;padding:10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);box-sizing:border-box;resize:vertical;"></textarea>
        </div>
        <div class="card">
          <div class="card-title">❓ Generated Questions</div>
          <p style="font-size:0.82em;color:var(--muted);margin:0 0 12px;">Review below. All questions will be appended to the week's quiz on confirm.</p>
          <div id="ag-questions-preview"></div>
        </div>
        <div class="card">
          <div class="btn-row">
            <button class="btn btn-success" onclick="confirmGenerated()">✓ Confirm &amp; Save All</button>
            <button class="btn btn-ghost" onclick="cancelGenerated()">✕ Discard</button>
            <span id="ag-confirm-status" style="font-size:0.8em;color:var(--muted);"></span>
          </div>
        </div>
      </div>
    </div>
```

- [ ] **Step 3: Verify HTML is well-formed**

```bash
python3 -c "
from html.parser import HTMLParser
class V(HTMLParser): pass
v = V()
v.feed(open('/home/alex/.local/share/catsoop/api/admin.html').read())
print('HTML parsed OK')
"
```

Expected: `HTML parsed OK`

- [ ] **Step 4: Commit**

```bash
git add api/admin.html
git commit -m "$(cat <<'EOF'
feat: add AI Generator panel and nav item to admin HTML

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Add JS functions to admin.js

**Files:**
- Modify: `api/static/admin/admin.js`

- [ ] **Step 1: Append the four AI Generator functions at the end of admin.js**

Open `api/static/admin/admin.js` and append the following block at the very end of the file:

```javascript
// ─── AI GENERATOR ──────────────────────────────────────────────────────────

let _agJobId = null;
let _agQuestions = [];

async function generateFromFile() {
  const course = document.getElementById('ag-course').value;
  const week   = document.getElementById('ag-week').value;
  const fileInput = document.getElementById('ag-file');
  const numQ   = parseInt(document.getElementById('ag-num-questions').value) || 5;
  const qtype  = document.getElementById('ag-question-type').value;
  const statusEl = document.getElementById('ag-status');
  const btn    = document.getElementById('ag-generate-btn');

  if (!course || !week) { statusEl.textContent = 'Select a course and week first.'; return; }
  if (!fileInput.files.length) { statusEl.textContent = 'Select a file to upload.'; return; }

  const file = fileInput.files[0];
  statusEl.textContent = 'Reading file…';
  btn.disabled = true;

  const reader = new FileReader();
  reader.onerror = () => { statusEl.textContent = 'Failed to read file.'; btn.disabled = false; };
  reader.onload = async (e) => {
    const base64 = e.target.result.split(',')[1];
    statusEl.textContent = 'Uploading and generating… (1–3 min)';
    try {
      const resp = await fetch(`/admin/generate-from-file/${course}/${week}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          data_base64: base64,
          content_type: file.type || 'application/octet-stream',
          question_type: qtype,
          num_questions: numQ,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        statusEl.textContent = 'Error: ' + (err.detail || resp.statusText);
        btn.disabled = false;
        return;
      }
      const data = await resp.json();
      _agJobId = data.job_id;
      _agQuestions = data.questions;

      document.getElementById('ag-lecture-html').value = data.lecture_html;
      renderAgQuestionsPreview(data.questions);
      document.getElementById('ag-preview-section').style.display = '';
      document.getElementById('ag-confirm-status').textContent = '';

      const errNote = data.errors && data.errors.length
        ? ` (${data.errors.length} question(s) failed to parse)`
        : '';
      statusEl.textContent =
        `Done — ${data.chunk_count} chunks indexed, ${data.questions.length} questions generated.${errNote}`;
      showToast('Content ready — review below and click Confirm to save.');
    } catch (err) {
      statusEl.textContent = 'Error: ' + err.message;
    } finally {
      btn.disabled = false;
    }
  };
  reader.readAsDataURL(file);
}

function renderAgQuestionsPreview(questions) {
  const container = document.getElementById('ag-questions-preview');
  container.innerHTML = '';
  if (!questions.length) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.85em;">No questions were generated.</p>';
    return;
  }
  questions.forEach((q, i) => {
    const div = document.createElement('div');
    div.style.cssText = 'border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:12px;background:var(--surface2);';
    const optsHtml = q.options && q.options.length
      ? `<div style="font-size:0.8em;color:var(--muted);margin:4px 0;">Options: ${q.options.join(' | ')}</div>` : '';
    const hintsHtml = q.hints && q.hints.length
      ? `<div style="font-size:0.8em;color:var(--muted);margin:4px 0;">${q.hints.length} hint(s)</div>` : '';
    div.innerHTML =
      `<div style="font-size:0.78em;color:var(--accent);margin-bottom:4px;">Q${i+1} — ${q.question_type}</div>` +
      `<div style="font-weight:600;margin-bottom:4px;">${q.question_text}</div>` +
      optsHtml +
      `<div style="font-size:0.8em;color:var(--green);margin:4px 0;">Correct: ${q.correct_answer}</div>` +
      hintsHtml;
    container.appendChild(div);
  });
}

async function confirmGenerated() {
  if (!_agJobId) return;
  const statusEl = document.getElementById('ag-confirm-status');
  statusEl.textContent = 'Saving…';
  const lectureHtml = document.getElementById('ag-lecture-html').value;
  try {
    const resp = await fetch(`/admin/confirm-generated/${_agJobId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ questions: _agQuestions, lecture_html: lectureHtml }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      statusEl.textContent = 'Error: ' + (err.detail || resp.statusText);
      return;
    }
    const data = await resp.json();
    document.getElementById('ag-preview-section').style.display = 'none';
    _agJobId = null;
    _agQuestions = [];
    const lecNote = data.lecture_path ? ` Lecture at /${data.lecture_path}` : '';
    document.getElementById('ag-status').textContent =
      `Saved: ${data.saved_questions} question(s), ${data.hints_saved} with hints.${lecNote}`;
    statusEl.textContent = '';
    showToast(`Saved ${data.saved_questions} question(s) and lecture notes.`);
  } catch (err) {
    statusEl.textContent = 'Error: ' + err.message;
  }
}

function cancelGenerated() {
  document.getElementById('ag-preview-section').style.display = 'none';
  _agJobId = null;
  _agQuestions = [];
  document.getElementById('ag-status').textContent = 'Discarded.';
  document.getElementById('ag-confirm-status').textContent = '';
}
```

- [ ] **Step 2: Check the JS for obvious syntax errors**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
node --check api/static/admin/admin.js 2>&1 || echo "node not available — skip"
```

If node is available, expected: no output (no syntax errors). If not available, skip.

- [ ] **Step 3: Commit**

```bash
git add api/static/admin/admin.js
git commit -m "$(cat <<'EOF'
feat: add generateFromFile, confirmGenerated, cancelGenerated JS functions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: End-to-end verification

- [ ] **Step 1: Run all unit tests**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
PYTHONPATH=$(pwd) python -m pytest api/tests/ catsoop_engine/test/ -v
```

Expected: all tests pass

- [ ] **Step 2: Start the app**

```bash
cd ~/.local/share/catsoop && source ~/catsoop-env/bin/activate
CU_QUIZ_BASE_URL=http://172.31.184.39:8000 \
CU_QUIZ_ALLOWED_ORIGINS="http://localhost:7667,http://172.31.184.39:8000,http://172.31.184.39:7667" \
bash run.sh
```

- [ ] **Step 3: Confirm new endpoints appear in Swagger**

Navigate to `http://172.31.184.39:8000/docs` and verify these two routes are listed:
- `POST /admin/generate-from-file/{course}/{week}`
- `POST /admin/confirm-generated/{job_id}`

- [ ] **Step 4: Confirm nav item renders**

Navigate to `http://172.31.184.39:8000/admin`, log in, and verify the "🤖 AI Generator" nav item appears in the sidebar under "Live Files".

- [ ] **Step 5: Full happy-path test**

1. Click "🤖 AI Generator" in the sidebar
2. Select a course (e.g. Econs) and week (e.g. week1)
3. Upload a small PDF or .txt file with course-relevant content
4. Set # Questions = 2, Type = Multiple Choice
5. Click "🤖 Generate" — wait for the status to read "Done — N chunks indexed"
6. Verify toast notification appears: "Content ready — review below..."
7. Verify the lecture HTML textarea is populated
8. Verify 2 question cards are shown with correct answers and hint counts
9. Click "✓ Confirm & Save All"
10. Verify toast: "Saved 2 question(s) and lecture notes."
11. Navigate to `http://localhost:7667/Econs/week1/quiz` — confirm the 2 new questions appear
12. Navigate to `http://localhost:7667/Econs/week1/lecture_ai` — confirm the lecture page loads

- [ ] **Step 6: Run POST /admin/repair to regenerate example_questions pages**

```bash
TOKEN=$(curl -s -X POST http://172.31.184.39:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password":"'$CU_QUIZ_ADMIN_PASSWORD'"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -X POST http://172.31.184.39:8000/admin/repair \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: `{"status": "ok", ...}`
