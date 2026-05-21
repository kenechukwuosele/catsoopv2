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
            from sentence_transformers import SentenceTransformer
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
        """Embed existing questions and their hints from SQLite."""
        from .. import models
        from ..database import SessionLocal

        col = self._get_collection("qa_hints")
        if not col:
            return 0

        db = SessionLocal()
        total = 0
        try:
            questions = db.query(models.Question).filter(
                models.Question.course == course,
                models.Question.week == week,
            ).all()
            for q in questions:
                hints = db.query(models.Hint).filter(
                    models.Hint.question_id == q.id
                ).order_by(models.Hint.hint_number).all()
                hint_texts = [h.hint_text for h in hints]
                combined = f"Q: {q.question_text}\nHints: {' | '.join(hint_texts)}" if hint_texts else q.question_text
                doc_id = f"qa_{course}_{week}_{q.id}"
                emb = self._get_embedding(combined)
                col.add(
                    ids=[doc_id],
                    embeddings=[emb],
                    metadatas=[{
                        "course": course,
                        "week": week,
                        "question_id": q.id,
                        "hint_count": len(hints),
                    }],
                    documents=[combined],
                )
                total += 1
            db.close()
        except Exception:
            db.close()
            raise
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
