import hashlib
import json
import os
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from dotenv import load_dotenv
from pypdf import PdfReader
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from ai_core.llm.groq_llm import call_groq

load_dotenv()

RAG_SUMMARY_MODEL = os.getenv("RAG_SUMMARY_MODEL", "llama-3.1-8b-instant")
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_LOCAL_ONLY = os.getenv("RAG_LOCAL_ONLY", "true").lower() == "true"
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "850"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "140"))
RAG_HASH_DIM = int(os.getenv("RAG_HASH_DIM", "384"))
RAG_MEMORY_LIMIT = int(os.getenv("RAG_MEMORY_LIMIT", "350"))
RAG_SEARCH_MULTIPLIER = int(os.getenv("RAG_SEARCH_MULTIPLIER", "8"))
RAG_MMR_LAMBDA = float(os.getenv("RAG_MMR_LAMBDA", "0.72"))


@dataclass
class RAGResult:
    text: str
    score: float
    metadata: Dict[str, Any]


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _term_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]{3,}", text.lower()))


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left | right), 1)


class RAGEngine:
    """
    Persistent FAISS vector database for travel knowledge.

    Improvements over the original version:
    - Loads the embedding model once per engine.
    - Avoids rebuilding the vector DB when documents have not changed.
    - Chunks long docs with overlap for better recall.
    - Returns ranked source-aware results.
    - Keeps the old `search(...) -> str` API for existing callers.
    """

    def __init__(self, index_dir: str = "rag_index"):
        base_dir = Path(__file__).resolve().parent
        self.index_dir = base_dir / index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.index_dir / "faiss.index"
        self.meta_path = self.index_dir / "metadata.pkl"
        self.manifest_path = self.index_dir / "manifest.json"
        self.memory_path = self.index_dir / "online_memory.jsonl"

        self.embedder = self._load_embedder()
        self.dim = self.embedder.get_sentence_embedding_dimension()

        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata: List[Dict[str, Any]] = []
        self.manifest: Dict[str, Any] = {}
        self._memory_hashes: set[str] = set()

        self._load()
        self._load_memory_hashes()

    def _load_embedder(self):
        if SentenceTransformer is not None:
            try:
                model = SentenceTransformer(RAG_EMBEDDING_MODEL, local_files_only=RAG_LOCAL_ONLY)
                model.name = RAG_EMBEDDING_MODEL
                return model
            except Exception:
                pass

        return HashingEmbedder(dim=RAG_HASH_DIM)

    def _load(self):
        if self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.meta_path, "rb") as f:
                    self.metadata = pickle.load(f)
                if self.manifest_path.exists():
                    self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception:
                self.index = faiss.IndexFlatIP(self.dim)
                self.metadata = []
                self.manifest = {}

    def _save(self, source_hash: str | None = None):
        faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.metadata, f)

        if source_hash:
            self.manifest = {
                "source_hash": source_hash,
                "embedding_model": self.embedder.name,
                "chunk_size": RAG_CHUNK_SIZE,
                "chunk_overlap": RAG_CHUNK_OVERLAP,
                "documents": len(self.metadata),
            }
            self.manifest_path.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")

    def _load_memory_hashes(self):
        self._memory_hashes = set()
        if not self.memory_path.exists():
            return

        try:
            with open(self.memory_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    item_hash = item.get("hash")
                    if item_hash:
                        self._memory_hashes.add(item_hash)
        except Exception:
            self._memory_hashes = set()

    def _load_memory_docs(self) -> List[Dict[str, Any]]:
        if not self.memory_path.exists():
            return []

        docs: List[Dict[str, Any]] = []
        try:
            with open(self.memory_path, encoding="utf-8") as f:
                lines = f.readlines()[-RAG_MEMORY_LIMIT:]
        except Exception:
            return []

        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            content = item.get("content", "")
            if not content:
                continue

            docs.append(
                {
                    "title": item.get("title", "Live travel memory"),
                    "content": content,
                    "city": item.get("city", ""),
                    "state": item.get("state", ""),
                    "source": item.get("source", "online-memory"),
                }
            )

        return docs

    def _embed(self, texts: List[str]) -> np.ndarray:
        vecs = self.embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(vecs).astype("float32")

    def _chunk_text(self, text: str, chunk_size: int = RAG_CHUNK_SIZE, overlap: int = RAG_CHUNK_OVERLAP) -> List[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []
        if len(cleaned) <= chunk_size:
            return [cleaned]

        chunks = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + chunk_size)
            window = cleaned[start:end]

            if end < len(cleaned):
                split_at = max(window.rfind(". "), window.rfind("; "), window.rfind(", "))
                if split_at > chunk_size * 0.55:
                    end = start + split_at + 1
                    window = cleaned[start:end]

            chunks.append(window.strip())
            if end >= len(cleaned):
                break
            start = max(end - overlap, start + 1)

        return chunks

    def _expand_query(self, query: str) -> str:
        travel_terms = [
            "itinerary",
            "hotel",
            "flight",
            "fare",
            "budget",
            "INR",
            "restaurants",
            "attractions",
            "transport",
            "safety",
            "weather",
            "neighborhood",
            "local logistics",
        ]
        compact_query = re.sub(r"\s+", " ", query).strip()
        return f"{compact_query} {' '.join(travel_terms)}"

    def _mmr_select(self, candidates: List[RAGResult], top_k: int) -> List[RAGResult]:
        selected: List[RAGResult] = []
        remaining = candidates[:]
        term_cache = {id(item): _term_set(f"{item.metadata.get('title', '')} {item.text}") for item in remaining}

        while remaining and len(selected) < top_k:
            best_item = None
            best_score = float("-inf")
            for item in remaining:
                similarity = 0.0
                item_terms = term_cache[id(item)]
                if selected:
                    similarity = max(
                        _jaccard(item_terms, term_cache.get(id(chosen), _term_set(chosen.text)))
                        for chosen in selected
                    )
                score = (RAG_MMR_LAMBDA * item.score) - ((1 - RAG_MMR_LAMBDA) * similarity)
                if score > best_score:
                    best_item = item
                    best_score = score

            if best_item is None:
                break
            selected.append(best_item)
            remaining.remove(best_item)

        return selected

    def _normalize_docs(self, docs: Any) -> List[Dict[str, Any]]:
        normalized = []

        if isinstance(docs, dict):
            for title, content in docs.items():
                normalized.append({"title": title, "content": content, "source": "bundled"})
        elif isinstance(docs, list):
            for doc in docs:
                if isinstance(doc, str):
                    normalized.append({"title": "Document", "content": doc, "source": "list"})
                elif isinstance(doc, dict):
                    normalized.append(
                        {
                            "title": doc.get("title", "Document"),
                            "content": doc.get("content", ""),
                            "city": doc.get("city", ""),
                            "state": doc.get("state", ""),
                            "source": doc.get("source", "dataset"),
                        }
                    )

        return [doc for doc in normalized if str(doc.get("content", "")).strip()]

    def _index_docs(self, normalized: List[Dict[str, Any]], source_hash: str | None = None):
        chunks = []
        metadata = []
        for doc in normalized:
            doc_chunks = self._chunk_text(doc["content"])
            for chunk_index, chunk in enumerate(doc_chunks):
                chunks.append(chunk)
                metadata.append(
                    {
                        "text": chunk,
                        "metadata": {
                            "title": doc.get("title", "Document"),
                            "source": doc.get("source", "dataset"),
                            "city": doc.get("city", ""),
                            "state": doc.get("state", ""),
                            "chunk": chunk_index,
                        },
                    }
                )

        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata = metadata

        if chunks:
            self.index.add(self._embed(chunks))

        self._save(source_hash=source_hash)

    def load_docs(self, docs: Any, force: bool = False):
        normalized = self._normalize_docs(docs)
        memory_docs = self._load_memory_docs()
        all_docs = normalized + memory_docs
        source_hash = _fingerprint(
            {
                "docs": all_docs,
                "embedding_model": self.embedder.name,
                "chunk_size": RAG_CHUNK_SIZE,
                "chunk_overlap": RAG_CHUNK_OVERLAP,
            }
        )

        if (
            not force
            and self.index.ntotal > 0
            and self.manifest.get("source_hash") == source_hash
            and self.manifest.get("embedding_model") == self.embedder.name
        ):
            return

        self._index_docs(all_docs, source_hash=source_hash)

    def add_documents(self, docs: Any):
        normalized = self._normalize_docs(docs)
        if not normalized:
            return

        chunks = []
        metadata = []
        for doc in normalized:
            for chunk_index, chunk in enumerate(self._chunk_text(doc["content"])):
                chunks.append(chunk)
                metadata.append(
                    {
                        "text": chunk,
                        "metadata": {
                            "title": doc.get("title", "Document"),
                            "source": doc.get("source", "dataset"),
                            "city": doc.get("city", ""),
                            "state": doc.get("state", ""),
                            "chunk": chunk_index,
                        },
                    }
                )

        if not chunks:
            return

        self.index.add(self._embed(chunks))
        self.metadata.extend(metadata)
        self._save()

    def remember_online_context(
        self,
        query: str,
        context: Any,
        city: str = "",
        source: str = "online-memory",
    ) -> bool:
        """
        Persist useful live search/API snippets into the local vector store.

        This lets later plans retrieve recent SerpAPI/Serper discoveries without
        re-querying the network every time.
        """
        content = _stable_json({"query": query, "context": context})
        if not content.strip():
            return False

        item_hash = _fingerprint({"query": query, "content": content, "source": source})
        if item_hash in self._memory_hashes:
            return False

        item = {
            "hash": item_hash,
            "title": f"Live context: {query[:80]}",
            "content": content,
            "city": city,
            "source": source,
        }

        try:
            with open(self.memory_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception:
            return False

        self._memory_hashes.add(item_hash)
        self.add_documents([item])
        return True

    def load_pdfs_from_folder(
        self,
        folder: str = "rag_pdfs",
        max_pdfs: int = 5,
        max_chunks_per_pdf: int = 24,
        chunk_size: int = RAG_CHUNK_SIZE,
        max_pdf_size_mb: int = 15,
    ):
        base_dir = Path(__file__).resolve().parent
        folder_path = base_dir / folder
        if not folder_path.exists():
            return

        docs = []
        for pdf in list(folder_path.glob("*.pdf"))[:max_pdfs]:
            try:
                if pdf.stat().st_size / (1024 * 1024) > max_pdf_size_mb:
                    continue

                reader = PdfReader(str(pdf))
                raw = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
                if raw:
                    docs.append({"title": pdf.name, "content": raw, "source": "pdf"})
            except Exception:
                continue

        if docs:
            self.add_documents(docs)

    def retrieve(self, query: str, top_k: int = 6, state: Optional[str] = None) -> List[RAGResult]:
        if self.index.ntotal == 0:
            return []

        expanded_query = self._expand_query(query)
        qvec = self._embed([expanded_query])
        search_k = min(max(top_k * RAG_SEARCH_MULTIPLIER, top_k), self.index.ntotal)
        scores, indices = self.index.search(qvec, search_k)

        query_terms = _term_set(expanded_query)
        candidates: List[RAGResult] = []
        seen_titles = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue

            doc = self.metadata[idx]
            meta = doc.get("metadata", {})

            if state:
                combined = f"{meta.get('state', '')} {meta.get('city', '')} {meta.get('title', '')}".lower()
                if state.lower() not in combined:
                    continue

            text = doc["text"]
            text_terms = _term_set(text)
            lexical_overlap = len(query_terms & text_terms)
            lexical_bonus = min(lexical_overlap * 0.014, 0.18)
            title_key = meta.get("title", "")
            diversity_penalty = 0.03 if title_key in seen_titles else 0
            source = str(meta.get("source", "")).lower()
            source_bonus = 0.04 if "live" in source or "online" in source else 0
            seen_titles.add(title_key)

            candidates.append(
                RAGResult(
                    text=text,
                    score=float(score) + lexical_bonus + source_bonus - diversity_penalty,
                    metadata=meta,
                )
            )

        candidates.sort(key=lambda item: item.score, reverse=True)
        return self._mmr_select(candidates, top_k)

    def format_context(self, results: List[RAGResult]) -> str:
        if not results:
            return "[RAG] No relevant documents."

        blocks = []
        for index, item in enumerate(results, start=1):
            meta = item.metadata
            source = meta.get("source", "local")
            title = meta.get("title", "Document")
            blocks.append(f"[{index}] {title} ({source})\n{item.text}")

        return "\n\n".join(blocks)

    def format_context_json(self, results: List[RAGResult]) -> str:
        return json.dumps(
            [
                {
                    "rank": index,
                    "score": round(item.score, 4),
                    "title": item.metadata.get("title", "Document"),
                    "source": item.metadata.get("source", "local"),
                    "city": item.metadata.get("city", ""),
                    "state": item.metadata.get("state", ""),
                    "text": item.text,
                }
                for index, item in enumerate(results, start=1)
            ],
            ensure_ascii=False,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        state: Optional[str] = None,
        summarize: bool = False,
    ):
        results = self.retrieve(query=query, top_k=top_k, state=state)
        context = self.format_context(results)

        if not summarize or not results:
            return context

        try:
            prompt = f"""
Summarize the following retrieved travel knowledge into concise, source-aware bullet points.
Focus on attractions, food, safety, logistics, seasonality, and practical constraints.
Keep specific place names and avoid adding facts not present in the context.

{context}
"""
            return call_groq(prompt, model=RAG_SUMMARY_MODEL)
        except Exception:
            return context


class HashingEmbedder:
    name = "local-hashing-embedder"

    def __init__(self, dim: int = 384):
        self.dim = dim

    def get_sentence_embedding_dimension(self) -> int:
        return self.dim

    def encode(self, texts: List[str], normalize_embeddings: bool = True, show_progress_bar: bool = False):
        vectors = np.zeros((len(texts), self.dim), dtype="float32")

        for row, text in enumerate(texts):
            tokens = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
            for token in tokens:
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "little") % self.dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vectors[row, bucket] += sign

        if normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = np.divide(vectors, np.maximum(norms, 1e-8))

        return vectors
