import json
import re

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..validation import safe_course, safe_week
from ..schemas import RAGIngestRequest, RAGGenerateHint
from ..services.rag_service import RAGService
from ..services.ollama_client import OllamaClient
from ..config import CATSOOP_COURSES_DIR, OLLAMA_BASE_URL, OLLAMA_MODEL


def get_router() -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_admin)])
    rag = RAGService.get_instance()
    ollama = OllamaClient(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)

    @router.post("/admin/rag/ingest/{course}/{week}")
    async def ingest_course(course: str, week: str):
        course = safe_course(course); week = safe_week(week)
        """Chunk and embed .catsoop lecture content + questions with hints."""
        try:
            content_chunks = rag.ingest_course_content(course, week, CATSOOP_COURSES_DIR)
            qa_chunks = rag.ingest_questions_with_hints(course, week)
            return {
                "status": "success",
                "course": course,
                "week": week,
                "content_chunks_ingested": content_chunks,
                "qa_pairs_ingested": qa_chunks,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/admin/rag/generate-hint")
    async def generate_hint(data: RAGGenerateHint):
        """Generate a progressive hint using RAG + local LLM."""
        try:
            similar_qa = rag.retrieve_similar(data.question_text, "qa_hints", n=3)
            content_chunks = rag.retrieve_similar(data.question_text, "course_content", n=5)

            prompt = rag.build_prompt(
                question_text=data.question_text,
                hint_level=data.hint_level,
                similar_qa=similar_qa,
                content_chunks=content_chunks,
            )

            system = "You are a helpful tutor. Generate a concise, progressive hint that helps the student arrive at the answer themselves."
            hint = await ollama.generate(prompt, system=system)

            return {
                "hint": hint,
                "source": "rag_ollama",
                "retrieved_qa": len(similar_qa),
                "retrieved_content": len(content_chunks),
                "hint_level": data.hint_level,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG generation failed: {str(e)}")

    @router.post("/admin/rag/generate-questions/{course}/{week}")
    async def generate_questions(course: str, week: str, body: dict):
        """Generate quiz questions from course content using RAG + Ollama and immediately import them."""
        from ..routes.file_questions import append_questions

        course = safe_course(course); week = safe_week(week)
        topic = (body.get("topic") or "").strip()
        num_questions = max(1, min(10, int(body.get("num_questions", 3))))
        question_type = body.get("question_type", "multiple-choice")
        with_hints = bool(body.get("with_hints", True))

        supported_types = {"multiple-choice", "short-answer", "numerical", "checkbox"}
        if question_type not in supported_types:
            question_type = "multiple-choice"

        query = topic if topic else "key concepts from this course"
        content_chunks = rag.retrieve_similar(query, "course_content", n=6)
        if not content_chunks:
            raise HTTPException(status_code=400, detail="No course content indexed yet. Run /admin/rag/ingest first.")

        system = "You are a university exam question writer. Output ONLY valid JSON, nothing else."
        generated_data, errors = [], []

        for i in range(num_questions):
            raw = ""
            try:
                prompt = rag.build_question_generation_prompt(content_chunks, question_type, topic)
                raw = await ollama.generate(prompt, system=system, max_tokens=300)
                raw = re.sub(r'^```[a-z]*\s*', '', raw.strip())
                raw = re.sub(r'\s*```$', '', raw.strip())
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                errors.append({"index": i, "error": f"JSON parse error: {e}", "raw": raw[:200]})
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

            generated_data.append({
                "question_text": q_text,
                "question_type": question_type,
                "options": options,
                "correct_answer": str(correct),
                "points": 1,
                "hints": hints_raw[:3] if with_hints else [],
                "_preview_correct": correct,
                "_preview_options": options,
            })

        if not generated_data:
            return {"questions": [], "imported": 0, "errors": errors}

        try:
            csq_names = append_questions(course, week, generated_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write questions: {e}")

        questions_out = []
        for csq_name, item in zip(csq_names, generated_data):
            questions_out.append({
                "csq_name": csq_name,
                "question_text": item["question_text"],
                "question_type": item["question_type"],
                "options": item["_preview_options"],
                "correct_answer": item["_preview_correct"],
                "hints_count": len(item["hints"]),
            })

        return {"questions": questions_out, "imported": len(questions_out), "errors": errors}

    @router.get("/admin/rag/status")
    async def rag_status():
        """Show what's been indexed in the vector store."""
        return rag.status()

    @router.delete("/admin/rag/clear")
    async def clear_vector_store():
        """Clear all vector indices."""
        rag.clear()
        return {"status": "success", "message": "Vector store cleared"}

    return router
