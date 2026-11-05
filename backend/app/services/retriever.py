"""
Information Retrieval Engine for LexiScope.
Implements TF-IDF vectorization and Cosine Similarity passage search across legal documents.
Preserves exact chunk, page, and section source attribution without hallucinating references.
"""

import math
import re
import time
from typing import List, Dict, Optional, Tuple, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.schemas import SectionInfo, SearchResultItem, SearchResponse


class IndexedChunk:
    """Represents a discrete indexed text passage with rigorous source tracking."""
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        document_name: str,
        chunk_index: int,
        text: str,
        page_number: Optional[int] = None,
        section_reference: Optional[str] = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.document_name = document_name
        self.chunk_index = chunk_index
        self.text = text
        self.page_number = page_number
        self.section_reference = section_reference


def chunk_document(
    document_id: str,
    document_name: str,
    sections: List[SectionInfo],
    full_text: str,
    target_words: int = 140,
    overlap_words: int = 30,
) -> List[IndexedChunk]:
    """
    Segment a document into cohesive, overlapping text chunks while tracking source locations.
    Uses section boundaries when available, otherwise partitions paragraphs.
    """
    chunks: List[IndexedChunk] = []

    # If sections exist (pages from PDF, or paragraphs from DOCX/TXT)
    if sections:
        current_words: List[str] = []
        current_page = sections[0].page_number
        current_sec_ref = sections[0].heading or f"Section {sections[0].index + 1}"

        for sec in sections:
            sec_words = sec.text.split()
            sec_page = sec.page_number
            sec_heading = sec.heading or f"Section {sec.index + 1}"

            # If section itself is small, accumulate
            if len(current_words) + len(sec_words) <= target_words:
                current_words.extend(sec_words)
                if not current_page and sec_page:
                    current_page = sec_page
            else:
                # Flush current accumulated words if non-empty
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunks.append(
                        IndexedChunk(
                            chunk_id=f"{document_id}_c{len(chunks)}",
                            document_id=document_id,
                            document_name=document_name,
                            chunk_index=len(chunks),
                            text=chunk_text,
                            page_number=current_page,
                            section_reference=current_sec_ref,
                        )
                    )
                    # Keep overlap
                    current_words = current_words[-overlap_words:] if overlap_words > 0 else []

                # Now handle sec_words: if it's larger than target_words, partition it
                if len(sec_words) > target_words:
                    start_idx = 0
                    while start_idx < len(sec_words):
                        sub_words = sec_words[start_idx : start_idx + target_words]
                        chunks.append(
                            IndexedChunk(
                                chunk_id=f"{document_id}_c{len(chunks)}",
                                document_id=document_id,
                                document_name=document_name,
                                chunk_index=len(chunks),
                                text=" ".join(sub_words),
                                page_number=sec_page,
                                section_reference=sec_heading,
                            )
                        )
                        start_idx += (target_words - overlap_words)
                    current_words = []
                else:
                    current_words.extend(sec_words)
                    current_page = sec_page
                    current_sec_ref = sec_heading

        if current_words:
            chunks.append(
                IndexedChunk(
                    chunk_id=f"{document_id}_c{len(chunks)}",
                    document_id=document_id,
                    document_name=document_name,
                    chunk_index=len(chunks),
                    text=" ".join(current_words),
                    page_number=current_page,
                    section_reference=current_sec_ref,
                )
            )

    # Fallback if no sections were parsed
    if not chunks and full_text.strip():
        words = full_text.split()
        start_idx = 0
        while start_idx < len(words):
            sub_words = words[start_idx : start_idx + target_words]
            chunks.append(
                IndexedChunk(
                    chunk_id=f"{document_id}_c{len(chunks)}",
                    document_id=document_id,
                    document_name=document_name,
                    chunk_index=len(chunks),
                    text=" ".join(sub_words),
                    page_number=1,
                    section_reference="Document Body",
                )
            )
            start_idx += (target_words - overlap_words)

    return chunks


def extract_matched_snippet(chunk_text: str, query: str, max_chars: int = 240) -> str:
    """
    Extract a focused text excerpt surrounding the highest concentration of query terms.
    Preserves verbatim source text.
    """
    if len(chunk_text) <= max_chars:
        return chunk_text.strip()

    # Find keywords from query
    query_terms = [re.escape(w.lower()) for w in re.findall(r"\b[A-Za-z0-9]{3,}\b", query)]
    if not query_terms:
        return chunk_text[:max_chars].strip() + "..."

    pattern = re.compile(r"\b(" + "|".join(query_terms) + r")\b", re.IGNORECASE)
    matches = list(pattern.finditer(chunk_text))

    if not matches:
        return chunk_text[:max_chars].strip() + "..."

    # Center snippet around the earliest dense match
    first_match_start = matches[0].start()
    half_window = max_chars // 2
    snippet_start = max(0, first_match_start - half_window)
    snippet_end = min(len(chunk_text), snippet_start + max_chars)

    # Adjust window if hit end
    if snippet_end == len(chunk_text):
        snippet_start = max(0, snippet_end - max_chars)

    # Align to word boundaries
    if snippet_start > 0:
        prev_space = chunk_text.find(" ", snippet_start)
        if prev_space != -1 and prev_space < snippet_start + 25:
            snippet_start = prev_space + 1

    if snippet_end < len(chunk_text):
        next_space = chunk_text.rfind(" ", snippet_start, snippet_end)
        if next_space != -1 and next_space > snippet_end - 25:
            snippet_end = next_space

    snippet = chunk_text[snippet_start:snippet_end].strip()
    prefix = "... " if snippet_start > 0 else ""
    suffix = " ..." if snippet_end < len(chunk_text) else ""
    return prefix + snippet + suffix


class LegalRetriever:
    """
    TF-IDF Vector Retrieval Engine with Cosine Similarity ranking across indexed documents.
    """
    def __init__(self):
        self.chunks: List[IndexedChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None

    def index_documents(self, documents_chunks: List[IndexedChunk]) -> None:
        """
        Rebuild TF-IDF index across all active document chunks.
        """
        self.chunks = documents_chunks
        if not self.chunks:
            self.vectorizer = None
            self.tfidf_matrix = None
            return

        corpus = [c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
            max_df=1.0,
            min_df=1,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def search(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        min_score: float = 0.04,
    ) -> SearchResponse:
        """
        Search indexed chunks by natural language query.
        Returns ranked results with exact source attribution.
        """
        start_time = time.perf_counter()
        clean_query = query.strip()

        if not clean_query or not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return SearchResponse(
                query=clean_query,
                total_matches=0,
                results=[],
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        try:
            # Transform user query using fitted TF-IDF vectorizer
            query_vec = self.vectorizer.transform([clean_query])
            
            # Check if query vector is all zeros (e.g., words not in vocabulary or only stopwords)
            if query_vec.nnz == 0:
                # Fallback: simple token containment scoring
                q_words = set(re.findall(r"\b[A-Za-z0-9]{3,}\b", clean_query.lower()))
                scores = []
                for idx, c in enumerate(self.chunks):
                    if document_ids and c.document_id not in document_ids:
                        scores.append(0.0)
                        continue
                    c_words = set(re.findall(r"\b[A-Za-z0-9]{3,}\b", c.text.lower()))
                    overlap = len(q_words.intersection(c_words))
                    scores.append(float(overlap) / max(1, len(q_words)) * 0.25)
                sim_scores = np.array(scores)
            else:
                sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

            # Rank candidate chunks
            ranked_indices = np.argsort(-sim_scores)
            results: List[SearchResultItem] = []

            for idx in ranked_indices:
                score = float(sim_scores[idx])
                if score < min_score:
                    break

                chunk = self.chunks[idx]
                # Filter by document_ids if provided
                if document_ids and chunk.document_id not in document_ids:
                    continue

                snippet = extract_matched_snippet(chunk.text, clean_query)

                results.append(
                    SearchResultItem(
                        document_id=chunk.document_id,
                        document_name=chunk.document_name,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        section_reference=chunk.section_reference,
                        score=round(score, 4),
                        matched_snippet=snippet,
                        full_chunk_text=chunk.text,
                    )
                )

                if len(results) >= top_k:
                    break

            exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return SearchResponse(
                query=clean_query,
                total_matches=len(results),
                results=results,
                execution_time_ms=exec_ms,
            )

        except Exception:
            exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return SearchResponse(
                query=clean_query,
                total_matches=0,
                results=[],
                execution_time_ms=exec_ms,
            )
