"""
Document Extraction Engine for LexiScope.
Supports PDF (via pypdf), DOCX (via python-docx), and plain text (.txt).
Enforces security boundaries, size limits, format validation, and structure preservation.
"""

import io
import math
import os
import re
from typing import List, Tuple, Dict, Any

import pypdf
import docx

from app.schemas import SectionInfo, DocumentMetadata


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 Megabytes
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/octet-stream",  # Often sent by browsers for .docx or .txt
}


class ExtractionError(Exception):
    """Safe, user-facing document extraction error."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent directory traversal and OS-specific exploit characters.
    """
    if not filename:
        return "untitled_document.txt"
    # Take only the base filename, stripping any directory components
    base = os.path.basename(filename.strip().replace("\\", "/"))
    # Remove any characters outside letters, digits, spaces, dots, dashes, underscores, parentheses
    sanitized = re.sub(r"[^\w\s\.\(\)-]", "_", base)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "document"


def validate_file_metadata(filename: str, content_length: int, content_type: str = "") -> str:
    """
    Validate extension, file size, and basic type. Returns lowercased extension.
    """
    if content_length <= 0:
        raise ExtractionError("Document is empty (0 bytes). Please upload a valid document.", status_code=400)
    
    if content_length > MAX_FILE_SIZE_BYTES:
        raise ExtractionError(
            f"File size ({content_length / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of 10 MB.",
            status_code=400,
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ExtractionError(
            f"Unsupported file format '{ext}'. LexiScope supports: {allowed}.",
            status_code=400,
        )

    return ext


def extract_from_txt(file_bytes: bytes, filename: str) -> Tuple[str, List[SectionInfo], int]:
    """
    Extract text and structured paragraphs from plain text files (.txt).
    Tries UTF-8, then Latin-1 fallback.
    """
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception as e:
            raise ExtractionError(f"Failed to decode text document encoding: {str(e)}", status_code=400)

    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ExtractionError("Text document contains no readable text content.", status_code=400)

    # Split into logical paragraphs based on double newlines
    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [text.strip()]

    sections: List[SectionInfo] = []
    total_words = 0
    words_per_page = 350

    running_words = 0
    for idx, para in enumerate(raw_paragraphs):
        para_words = len(para.split())
        running_words += para_words
        total_words += para_words
        page_est = max(1, math.ceil(running_words / words_per_page))

        # Check for simple markdown/legal heading prefix (e.g. "Article 1:", "Section 2.", "1.1")
        heading = None
        first_line = para.split("\n")[0].strip()
        if len(first_line) < 80 and re.match(r"^(section|article|clause|\d+(\.\d+)*)\b", first_line, re.IGNORECASE):
            heading = first_line

        sections.append(
            SectionInfo(
                index=idx,
                page_number=page_est,
                heading=heading,
                text=para,
                word_count=para_words,
            )
        )

    est_pages = max(1, math.ceil(total_words / words_per_page))
    return text, sections, est_pages


def extract_from_pdf(file_bytes: bytes, filename: str) -> Tuple[str, List[SectionInfo], int]:
    """
    Extract text and page-indexed sections from PDF files using pypdf.
    Detects scanned PDFs with no text layer.
    """
    try:
        stream = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(stream)
    except Exception as e:
        raise ExtractionError(
            f"Invalid or corrupted PDF file. Could not parse document structure.",
            status_code=400,
        )

    num_pages = len(reader.pages)
    if num_pages == 0:
        raise ExtractionError("PDF document has 0 pages.", status_code=400)

    sections: List[SectionInfo] = []
    full_text_parts: List[str] = []
    total_text_length = 0

    for page_idx in range(num_pages):
        page_num = page_idx + 1
        try:
            page = reader.pages[page_idx]
            page_text = page.extract_text() or ""
        except Exception as e:
            page_text = ""

        cleaned = page_text.strip()
        if cleaned:
            total_text_length += len(cleaned)
            full_text_parts.append(cleaned)
            para_words = len(cleaned.split())
            sections.append(
                SectionInfo(
                    index=page_idx,
                    page_number=page_num,
                    heading=f"Page {page_num}",
                    text=cleaned,
                    word_count=para_words,
                )
            )

    if total_text_length == 0:
        raise ExtractionError(
            "No extractable text found in PDF. Scanned PDFs require Optical Character "
            "Recognition (OCR), which is not currently supported.",
            status_code=400,
        )

    full_text = "\n\n".join(full_text_parts)
    return full_text, sections, num_pages


def extract_from_docx(file_bytes: bytes, filename: str) -> Tuple[str, List[SectionInfo], int]:
    """
    Extract text and paragraph sections from Microsoft Word (.docx) files using python-docx.
    """
    try:
        stream = io.BytesIO(file_bytes)
        doc = docx.Document(stream)
    except Exception as e:
        raise ExtractionError(
            f"Invalid or corrupted DOCX file. Could not parse document structure.",
            status_code=400,
        )

    sections: List[SectionInfo] = []
    full_text_parts: List[str] = []
    total_words = 0
    words_per_page = 350
    running_words = 0

    # Extract paragraphs
    for idx, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        if not text:
            continue
        
        words = len(text.split())
        running_words += words
        total_words += words
        page_est = max(1, math.ceil(running_words / words_per_page))

        heading = None
        if p.style and p.style.name and "heading" in p.style.name.lower():
            heading = text
        elif len(text) < 90 and re.match(r"^(section|article|clause|\d+(\.\d+)*)\b", text, re.IGNORECASE):
            heading = text

        sections.append(
            SectionInfo(
                index=len(sections),
                page_number=page_est,
                heading=heading,
                text=text,
                word_count=words,
            )
        )
        full_text_parts.append(text)

    # Also extract table contents if present
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                combined_row = " | ".join(row_texts)
                words = len(combined_row.split())
                running_words += words
                total_words += words
                page_est = max(1, math.ceil(running_words / words_per_page))
                sections.append(
                    SectionInfo(
                        index=len(sections),
                        page_number=page_est,
                        heading="Table Row",
                        text=combined_row,
                        word_count=words,
                    )
                )
                full_text_parts.append(combined_row)

    if not full_text_parts:
        raise ExtractionError("DOCX document contains no readable text content.", status_code=400)

    full_text = "\n\n".join(full_text_parts)
    est_pages = max(1, math.ceil(total_words / words_per_page))
    return full_text, sections, est_pages


def extract_document(filename: str, file_bytes: bytes, content_type: str = "") -> Tuple[str, List[SectionInfo], Dict[str, Any]]:
    """
    Main extraction dispatcher for all supported formats.
    Returns (full_text, sections, metadata_dict).
    """
    clean_name = sanitize_filename(filename)
    ext = validate_file_metadata(clean_name, len(file_bytes), content_type)

    if ext == ".txt":
        full_text, sections, page_count = extract_from_txt(file_bytes, clean_name)
        file_type = "txt"
    elif ext == ".pdf":
        full_text, sections, page_count = extract_from_pdf(file_bytes, clean_name)
        file_type = "pdf"
    elif ext == ".docx":
        full_text, sections, page_count = extract_from_docx(file_bytes, clean_name)
        file_type = "docx"
    else:
        raise ExtractionError(f"Unsupported extension {ext}", status_code=400)

    word_count = len(full_text.split())

    metadata = {
        "filename": clean_name,
        "file_type": file_type,
        "file_size_bytes": len(file_bytes),
        "word_count": word_count,
        "page_count": page_count,
        "section_count": len(sections),
    }

    return full_text, sections, metadata
