"""
In-Memory Storage for LexiScope.
Maintains session document state, extraction artifacts, and updates the TF-IDF search index.
Thread-safe and lightweight (no external databases required).
"""

from datetime import datetime, timezone
import threading
import uuid
from typing import Dict, List, Optional

from app.schemas import DocumentMetadata, SectionInfo
from app.services.retriever import LegalRetriever, IndexedChunk, chunk_document


class StoredDocument:
    """Internal model for an uploaded and processed legal document."""
    def __init__(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        word_count: int,
        page_count: int,
        full_text: str,
        sections: List[SectionInfo],
        uploaded_at: str,
    ):
        self.doc_id = doc_id
        self.filename = filename
        self.file_type = file_type
        self.file_size_bytes = file_size_bytes
        self.word_count = word_count
        self.page_count = page_count
        self.full_text = full_text
        self.sections = sections
        self.uploaded_at = uploaded_at
        self.chunks: List[IndexedChunk] = []

    def to_metadata(self) -> DocumentMetadata:
        return DocumentMetadata(
            id=self.doc_id,
            filename=self.filename,
            file_type=self.file_type,
            file_size_bytes=self.file_size_bytes,
            word_count=self.word_count,
            page_count=self.page_count,
            section_count=len(self.sections),
            uploaded_at=self.uploaded_at,
        )


class DocumentStore:
    """
    Thread-safe in-memory registry of documents and unified search index.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._documents: Dict[str, StoredDocument] = {}
        self.retriever = LegalRetriever()

    def add_document(
        self,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        word_count: int,
        page_count: int,
        full_text: str,
        sections: List[SectionInfo],
    ) -> StoredDocument:
        with self._lock:
            doc_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()

            # Handle duplicate filenames visually
            existing_names = [d.filename for d in self._documents.values()]
            display_name = filename
            if display_name in existing_names:
                count = sum(1 for name in existing_names if name.startswith(display_name))
                display_name = f"{display_name} ({count + 1})"

            doc = StoredDocument(
                doc_id=doc_id,
                filename=display_name,
                file_type=file_type,
                file_size_bytes=file_size_bytes,
                word_count=word_count,
                page_count=page_count,
                full_text=full_text,
                sections=sections,
                uploaded_at=now_iso,
            )

            # Segment into search chunks
            doc.chunks = chunk_document(
                document_id=doc_id,
                document_name=display_name,
                sections=sections,
                full_text=full_text,
            )

            self._documents[doc_id] = doc
            self._rebuild_index_locked()
            return doc

    def get_document(self, doc_id: str) -> Optional[StoredDocument]:
        with self._lock:
            return self._documents.get(doc_id)

    def list_documents(self) -> List[DocumentMetadata]:
        with self._lock:
            return [d.to_metadata() for d in self._documents.values()]

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                self._rebuild_index_locked()
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
            self._rebuild_index_locked()

    def count(self) -> int:
        with self._lock:
            return len(self._documents)

    def _rebuild_index_locked(self) -> None:
        """Internal helper to refresh TF-IDF index across all active chunks."""
        all_chunks: List[IndexedChunk] = []
        for doc in self._documents.values():
            all_chunks.extend(doc.chunks)
        self.retriever.index_documents(all_chunks)


# Global singleton instance for application session
document_store = DocumentStore()
