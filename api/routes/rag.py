from fastapi import APIRouter, HTTPException

from ..schemas import RAGIngestRequest, RAGGenerateHint
from ..services.rag_service import RAGService
from ..services.ollama_client import OllamaClient
from ..config import CATSOOP_COURSES_DIR, OLLAMA_BASE_URL, OLLAMA_MODEL


def get_router() -> APIRouter:
    router = APIRouter()
    rag = RAGService.get_instance()
    ollama = OllamaClient(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)

    @router.post("/admin/rag/ingest/{course}/{week}")
    async def ingest_course(course: str, week: str):
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
