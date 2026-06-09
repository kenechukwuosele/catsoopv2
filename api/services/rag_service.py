import os
import hashlib
import re
from typing import Optional

from ..config import VECTOR_STORE_DIR, EMBED_MODEL_NAME


class RAGService:
    _instance = None

    def __init__(self):
        self._embed_model = None
        self._vector_store = None
        self._initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _lazy_init(self):
        if self._initialized:
            return
        try:
            import chromadb
            self._vector_store = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
        except ImportError:
            self._vector_store = None
        try:
            import os
            from sentence_transformers import SentenceTransformer
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            self._embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        except ImportError:
            self._embed_model = None
        self._initialized = True

    @property
    def embed_model(self):
        self._lazy_init()
        return self._embed_model

    @property
    def vector_store(self):
        self._lazy_init()
        return self._vector_store

    def _get_embedding(self, text: str) -> list[float]:
        if self.embed_model:
            return self.embed_model.encode(text).tolist()
        return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> list[float]:
        h = hashlib.md5(text.encode()).digest()
        return [b / 255.0 for b in h[:384]]

    def _get_collection(self, name: str, create=True):
        if not self.vector_store:
            return None
        try:
            return self.vector_store.get_collection(name)
        except Exception:
            if create:
                return self.vector_store.create_collection(name)
            return None

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[tuple[str, int]]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = []
        current_len = 0
        idx = 0
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            current.append(s)
            current_len += len(s)
            if current_len >= chunk_size:
                chunk_text = " ".join(current)
                chunks.append((chunk_text, idx))
                idx += 1
                overlap_text = " ".join(current[-2:]) if len(current) >= 2 else current[-1]
                if len(overlap_text) < overlap:
                    current = current[-1:]
                    current_len = len(current[-1])
                else:
                    current = [overlap_text]
                    current_len = len(overlap_text)
        if current:
            chunks.append((" ".join(current), idx))
        return chunks

    def ingest_course_content(self, course: str, week: str, content_dir: str):
        """Chunk and embed .catsoop files from a course/week directory."""
        from datetime import datetime
        from .. import models
        from ..database import SessionLocal

        col = self._get_collection("course_content")
        if not col:
            return 0

        week_path = os.path.join(content_dir, course, week)
        if not os.path.isdir(week_path):
            return 0

        total_chunks = 0
        db = SessionLocal()
        try:
            for fname in os.listdir(week_path):
                if not fname.endswith(".catsoop"):
                    continue
                fpath = os.path.join(week_path, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                text = re.sub(r'<python>.*?</python>', '', raw, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    continue

                chunks = self._chunk_text(text)
                for chunk_text, chunk_idx in chunks:
                    doc_id = f"{course}_{week}_{fname}_{chunk_idx}"
                    emb = self._get_embedding(chunk_text)
                    col.add(
                        ids=[doc_id],
                        embeddings=[emb],
                        metadatas=[{
                            "course": course,
                            "week": week,
                            "source_file": fname,
                            "chunk_index": chunk_idx,
                            "timestamp": datetime.now().isoformat(),
                        }],
                        documents=[chunk_text],
                    )
                    record = models.ContentChunk(
                        course=course,
                        week=week,
                        source_file=fname,
                        chunk_index=chunk_idx,
                        chunk_text=chunk_text,
                    )
                    db.add(record)
                    total_chunks += 1
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
        return total_chunks

    def ingest_questions_with_hints(self, course: str, week: str):
        """Embed existing questions and their hints from .catsoop files + _hint_store JSON."""
        import json
        from ..routes.file_questions import parse_questions
        from ..config import CATSOOP_COURSES_DIR

        col = self._get_collection("qa_hints")
        if not col:
            return 0

        quiz_path = os.path.join(CATSOOP_COURSES_DIR, course, week, "quiz.catsoop")
        questions = parse_questions(quiz_path)

        hint_store_base = os.path.join(
            os.path.dirname(CATSOOP_COURSES_DIR), "_hint_store", course, week
        )

        total = 0
        for q in questions:
            csq_name = q.get("csq_name", "")
            question_text = q.get("question_text", "")
            if not question_text:
                continue

            hint_texts = []
            hint_file = os.path.join(hint_store_base, f"{csq_name}.json")
            if os.path.exists(hint_file):
                try:
                    with open(hint_file) as f:
                        hints = json.load(f)
                    hint_texts = [h.get("text", "") for h in hints if h.get("text")]
                except Exception:
                    pass

            combined = f"Q: {question_text}\nHints: {' | '.join(hint_texts)}" if hint_texts else question_text
            doc_id = f"qa_{course}_{week}_{csq_name}"
            emb = self._get_embedding(combined)
            col.add(
                ids=[doc_id],
                embeddings=[emb],
                metadatas=[{
                    "course": course,
                    "week": week,
                    "csq_name": csq_name,
                    "hint_count": len(hint_texts),
                }],
                documents=[combined],
            )
            total += 1
        return total

    def retrieve_similar(self, query: str, collection: str = "qa_hints", n: int = 3) -> list[dict]:
        col = self._get_collection(collection, create=False)
        if not col:
            return []
        emb = self._get_embedding(query)
        results = col.query(query_embeddings=[emb], n_results=n)
        out = []
        if results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                out.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })
        return out

    def build_prompt(self, question_text: str, hint_level: int, similar_qa: list[dict], content_chunks: list[dict]) -> str:
        level_descriptions = {
            1: "a vague, encouraging nudge (1-2 sentences, no specifics)",
            2: "a more specific hint pointing toward the approach or formula (1-2 sentences)",
            3: "a specific hint that nearly gives away the answer but leaves the final step (1-2 sentences)",
            4: "the key insight or formula needed to solve this (1-2 sentences)",
            5: "a detailed step-by-step walkthrough of the solution approach (2-3 sentences)",
        }
        desc = level_descriptions.get(hint_level, level_descriptions[1])

        context_parts = []
        if content_chunks:
            context_parts.append("Course Content Context:")
            for c in content_chunks:
                context_parts.append(f"- {c['text'][:300]}")
        if similar_qa:
            context_parts.append("\nSimilar Questions and Hints:")
            for s in similar_qa:
                context_parts.append(f"- {s['text'][:300]}")

        context_str = "\n".join(context_parts)
        prompt = f"""{context_str}

Student Question: {question_text}

Generate {desc}

Respond with ONLY the hint text, no JSON, no markdown formatting."""
        return prompt

    def build_question_generation_prompt(self, content_chunks: list[dict], question_type: str, topic: str = "") -> str:
        type_instructions = {
            "multiple-choice": (
                'Required JSON keys: "text" (question string), "options" (list of exactly 4 strings), '
                '"correct_answer" (one of the 4 option strings), "hints" (list of exactly 3 progressive hint strings).'
            ),
            "short-answer": (
                'Required JSON keys: "text" (question string), "correct_answer" (expected short answer), '
                '"hints" (list of exactly 3 progressive hint strings). Omit "options".'
            ),
            "numerical": (
                'Required JSON keys: "text" (question string), "correct_answer" (numeric value as string), '
                '"hints" (list of exactly 3 progressive hint strings). Omit "options".'
            ),
            "checkbox": (
                'Required JSON keys: "text" (question string), "options" (list of 4-5 strings), '
                '"correct_answer" (comma-separated correct option strings), "hints" (list of exactly 3 progressive hint strings).'
            ),
        }
        instructions = type_instructions.get(question_type, type_instructions["short-answer"])
        topic_clause = f' focused on "{topic}"' if topic else ""
        context = "\n".join(f"- {c['text'][:400]}" for c in content_chunks[:6])
        return (
            f"Based on the following course material, write one {question_type} university exam question{topic_clause}.\n"
            f"Output ONLY a valid JSON object , no explanation, no markdown, no code fences.\n"
            f"{instructions}\n\n"
            f"Course material:\n{context}\n\n"
            f"JSON:"
        )

    def status(self) -> dict:
        self._lazy_init()
        result = {
            "embed_model": str(self.embed_model) if self.embed_model else "fallback (md5)",
            "chromadb_available": self.vector_store is not None,
            "collections": {},
        }
        if self.vector_store:
            for name in ["course_content", "qa_hints"]:
                try:
                    col = self.vector_store.get_collection(name)
                    result["collections"][name] = col.count()
                except Exception:
                    result["collections"][name] = 0
        return result

    def clear(self):
        self._lazy_init()
        if self.vector_store:
            for name in ["course_content", "qa_hints"]:
                try:
                    self.vector_store.delete_collection(name)
                except Exception:
                    pass
        from .. import models
        from ..database import SessionLocal
        db = SessionLocal()
        try:
            db.query(models.ContentChunk).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
