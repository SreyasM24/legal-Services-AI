# AXIOM — Legal Research & Document Intelligence

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.5+-F7931E.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **AXIOM** is a lightweight, professional legal technology application designed for automated legal document text extraction, rule-based legal clause classification, sentence-level extractive summarization, and passage-level information retrieval using TF-IDF and Cosine Similarity.

---

## 1. Problem Statement & Objectives

### Problem Statement
Legal practitioners, contract managers, and students frequently review extensive legal agreements, commercial contracts, and non-disclosure agreements (NDAs). Manual review is time-consuming, prone to oversight of critical obligations (such as termination triggers or liability caps), and traditionally relies on either heavyweight enterprise software or opaque cloud LLM services that raise confidentiality and cost concerns.

### Project Objectives
- **Multi-Format Ingestion:** Extract clean text while preserving page and section structures from PDF, DOCX, and TXT files.
- **Rule-Based Clause Detection:** Identify clauses across eight fundamental legal categories using deterministic keywords and regex patterns with exact source references.
- **Verbatim Extractive Summarization:** Summarize contracts without generative hallucination by ranking sentence importance using TF-IDF document centrality.
- **Source-Attributed Passage Retrieval:** Retrieve ranked passages using TF-IDF vectorization and cosine similarity, attributing exact document names, chunk indices, and page/section numbers.
- **Zero Heavy Dependencies:** Run locally without external cloud LLM APIs, paid third-party services, complex databases, or heavy JavaScript frameworks.
- **Professional User Interface:** Provide a distraction-free, academic research dashboard adhering to formal legal aesthetics (warm ivory, muted burgundy, sage green, and classical serif typography).

---

## 2. Technology Stack

### Backend
- **Language:** Python 3.13
- **Web Framework:** FastAPI (RESTful API, automatic OpenAPI/Swagger documentation, static asset hosting)
- **ASGI Server:** Uvicorn (standard event loop)
- **Machine Learning & NLP:** Scikit-learn (`TfidfVectorizer`, `cosine_similarity`, NumPy)
- **Document Parsers:** 
  - `pypdf` (digital PDF text extraction and page segmentation)
  - `python-docx` (Microsoft Word paragraph and table extraction)
  - Native Python text processing (UTF-8 / Latin-1 encoding fallbacks)
- **Testing & Verification:** Pytest, HTTPX, Starlette TestClient

### Frontend
- **Markup:** HTML5 (semantic structure, ARIA accessibility roles)
- **Styling:** Custom CSS3 (CSS custom properties, responsive grid layouts, legal color palette)
- **Scripting:** Vanilla JavaScript (ES6+, native `fetch` API, safe DOM rendering via text properties)
- **Architecture:** Single-Page Application (SPA) served directly from FastAPI over same-origin `/api`

---

## 3. Architecture & Document Processing Workflow

```
[ User Browser ]
       │
       ▼ (HTTP / Same-Origin)
┌────────────────────────────────────────────────────────┐
│ FastAPI Application (http://127.0.0.1:8000)            │
│  ├── Static Mounts: / (index.html), /css, /js          │
│  ├── Interactive Docs: /docs (Swagger UI), /redoc      │
│  └── REST API Router: /api/*                           │
└──────────────────────────┬─────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
│ Extractor    │   │ Analyzer &   │   │ Information          │
│ Service      │   │ Clauses      │   │ Retriever            │
├──────────────┤   ├──────────────┤   ├──────────────────────┤
│ • PDF (pypdf)│   │ • Statistics │   │ • Chunking (140 wds) │
│ • DOCX (docx)│   │ • Entities   │   │ • TfidfVectorizer    │
│ • TXT        │   │ • Extractive │   │ • Cosine Similarity  │
│ • Pagination │   │   Summary    │   │ • Exact Source Ref   │
│ • 10MB Limit │   │ • 8 Clauses  │   │ • Snippet Highlight  │
└──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘
       │                  │                      │
       └──────────────────┼──────────────────────┘
                          ▼
            ┌───────────────────────────┐
            │ In-Memory Document Store  │
            │ (Thread-Safe RLock)       │
            └───────────────────────────┘
```

### Detailed Ingestion & Analysis Lifecycle:
1. **Upload & Validation:** The uploaded file is inspected for size ($\le 10\text{ MB}$) and extension (`.pdf`, `.docx`, `.txt`). Basenames are sanitized to prevent directory traversal.
2. **Text & Section Extraction:** Text is extracted preserving page numbers (PDF) or paragraph/table blocks (DOCX/TXT). If a PDF contains 0 extractable characters, the engine detects this and returns an explicit notice that scanned PDFs require OCR.
3. **Chunking & Indexing:** Extracted documents are partitioned into cohesive chunks (target 140 words with 30-word overlap) preserving chunk indices, page numbers, and section headings. The `LegalRetriever` recalculates the global `TfidfVectorizer` index across all active chunks.
4. **Descriptive NLP Metrics:** The document is scanned for word counts, sentence boundaries (handling legal abbreviations like *Corp.*, *Inc.*, *v.*, *Sec.*), dates, monetary amounts, and email addresses.
5. **Sentence-Level Extractive Summarization:** A sentence-level TF-IDF matrix is computed. Sentences with the highest cosine similarity to the aggregate document centroid are selected and presented in their original document order to preserve coherent narrative flow without hallucinations.
6. **Rule-Based Clause Detection:** Candidate sentences are checked against eight legal clause category pattern specifications, assigning a heuristic confidence indicator and source location.

---

## 4. Eight Legal Clause Categories

AXIOM implements pattern and keyword detection across eight standard commercial and contract categories:

| Category | Description | Representative Keywords / Patterns |
| :--- | :--- | :--- |
| **Confidentiality and Non-Disclosure** | Obligations to safeguard proprietary information and trade secrets. | *confidential information, non-disclosure, trade secret, duty of confidentiality, proprietary* |
| **Termination and Default** | Conditions, notice periods, and events triggering agreement dissolution. | *termination, material breach, event of default, cure period, written notice of termination* |
| **Indemnity and Hold Harmless** | Protection and reimbursement obligations against third-party claims. | *indemnify, indemnification, hold harmless, defend and hold harmless, third-party claims* |
| **Limitation of Liability** | Caps on monetary recovery and waivers of consequential or punitive damages. | *limitation of liability, in no event shall, consequential damages, aggregate liability, cap on liability* |
| **Governing Law and Dispute Resolution** | Applicable jurisdiction, competent courts, and binding arbitration. | *governing law, jurisdiction, dispute resolution, arbitration, American Arbitration Association* |
| **Warranties and Representations** | Formal statements of facts, fitness for purpose, and authority. | *representations and warranties, warrants that, as is, merchantability, fitness for a particular purpose* |
| **Force Majeure** | Relief from contractual performance due to uncontrollable catastrophic events. | *force majeure, acts of God, beyond reasonable control, unforeseeable circumstances, natural disasters* |
| **Intellectual Property Rights** | Ownership of copyrights, patents, trademarks, and deliverable titles. | *intellectual property, patents, copyrights, trademarks, work made for hire, proprietary rights* |

> **Notice:** Clause identification is rule-based and pattern-driven. Matches are labelled as potential indicators for human legal review and do not constitute formal legal classification or legal advice.

---

## 5. Information Retrieval Engine

Passage search across ingested documents uses classical statistical NLP:
- **Segmentation:** Documents are segmented into indexed chunks preserving source metadata (document ID, filename, chunk index, page number, section reference).
- **Vector Space:** `TfidfVectorizer(ngram_range=(1, 2), stop_words='english', sublinear_tf=True)` converts all chunks into a unified document-term matrix.
- **Scoring:** User queries are transformed into the same vector space, and `cosine_similarity(query_vector, chunk_matrix)` scores each passage from `0.0` to `1.0`.
- **Snippet Extraction:** The engine pinpoints the dense cluster of query terms within the winning chunk and extracts a contextual snippet with `<mark class="highlight">` emphasis.

---

## 6. Project Directory Structure

```
legal-Services-AI/
├── .gitignore                      # Git exclusion rules (caches, venv, temporary files)
├── README.md                       # Comprehensive documentation
├── requirements.txt                # Root-level dependencies
├── backend/
│   ├── requirements.txt            # Backend dependencies
│   ├── app/
│   │   ├── __init__.py             # App package marker
│   │   ├── main.py                 # FastAPI application, static mounts, and error handlers
│   │   ├── schemas.py              # Pydantic data contracts and models
│   │   ├── storage.py              # Thread-safe in-memory DocumentStore
│   │   ├── api/
│   │   │   ├── __init__.py         # API package marker
│   │   │   └── routes.py           # REST endpoints (/health, /upload, /analyze, /search, etc.)
│   │   └── services/
│   │       ├── __init__.py         # Services package marker
│   │       ├── extractor.py        # PDF, DOCX, TXT parsers and security validation
│   │       ├── analyzer.py         # Descriptive metrics & TF-IDF extractive summarizer
│   │       ├── clauses.py          # Rule-based detector for 8 legal clause categories
│   │       └── retriever.py        # Semantic chunker & TF-IDF Cosine Similarity engine
│   └── tests/
│       ├── __init__.py             # Test package marker
│       ├── conftest.py             # Shared synthetic legal fixtures and generators
│       ├── test_extractor.py       # Unit tests for text extraction, encodings, and limits
│       ├── test_analyzer.py        # Unit tests for metrics, entities, and summarization
│       ├── test_clauses.py         # Unit tests for all 8 clause categories
│       ├── test_retriever.py       # Unit tests for TF-IDF ranking and source attribution
│       ├── test_api.py             # Integration tests for FastAPI endpoints
│       └── test_frontend_integration.py # Integration tests for SPA delivery and static assets
└── frontend/
    ├── index.html                  # Semantic HTML5 legal technology dashboard
    ├── css/
    │   └── styles.css              # Custom CSS design system (ivory, burgundy, sage)
    └── js/
        ├── api.js                  # Centralized vanilla API client mapped to /api
        └── app.js                  # Client state store, safe DOM rendering, and event handlers
```

---

## 7. API Reference

All endpoints are hosted under `/api`. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

| Method | Endpoint | Description | Request Payload | Response Body |
| :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/health` | Service and engine readiness | None | `HealthResponse` |
| **POST** | `/api/documents/upload` | Ingest PDF, DOCX, or TXT file | Multipart `file: UploadFile` | `DocumentMetadata` |
| **GET** | `/api/documents` | List all active session documents | None | `DocumentListResponse` |
| **GET** | `/api/documents/{doc_id}` | Retrieve document text & sections | Path param `doc_id` | `DocumentDetailResponse` |
| **DELETE**| `/api/documents/{doc_id}` | Remove document from session | Path param `doc_id` | `{"message": "...", "remaining_documents": int}` |
| **POST** | `/api/documents/analyze` | Run NLP stats, summary & clauses | `{"document_id": str, "summary_sentences": int}` | `DocumentAnalysisResponse` |
| **POST** | `/api/documents/search` | TF-IDF passage search | `{"query": str, "document_ids": list\|null, "top_k": int}` | `SearchResponse` |

---

## 8. Installation & Setup Instructions

### Prerequisites
- **Operating System:** Windows, macOS, or Linux
- **Python:** Python 3.10+ (tested on Python 3.13)
- **Git** (for version control)

### Step 1: Clone the Repository
```powershell
git clone https://github.com/SreyasM24/legal-Services-AI.git
cd legal-Services-AI
```

### Step 2: Create and Activate a Virtual Environment
**On Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

---

## 9. Running the Application

Start the unified FastAPI server using Uvicorn:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once started:
- **Application Dashboard:** Open your browser to **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
- **Interactive Swagger Documentation:** Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
- **Health Endpoint:** Access **[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)**

---

## 10. Running the Automated Tests

AXIOM includes a comprehensive automated test suite with 34 tests covering document extraction, error boundaries, security sanitization, descriptive statistics, clause pattern matching, TF-IDF ranking precision, and API/frontend integration:

```powershell
# From the project root
pytest backend/tests -v
```

Expected output:
```text
collected 34 items

backend/tests/test_analyzer.py::test_statistics_entity_extraction PASSED
backend/tests/test_analyzer.py::test_extractive_summary_quality PASSED
backend/tests/test_analyzer.py::test_extractive_summary_short_text PASSED
backend/tests/test_api.py::test_api_health PASSED
backend/tests/test_api.py::test_api_upload_txt PASSED
backend/tests/test_api.py::test_api_upload_pdf PASSED
backend/tests/test_api.py::test_api_upload_docx PASSED
backend/tests/test_api.py::test_api_upload_invalid_format PASSED
backend/tests/test_api.py::test_api_upload_empty_file PASSED
backend/tests/test_api.py::test_api_get_documents_and_detail PASSED
backend/tests/test_api.py::test_api_get_document_not_found PASSED
backend/tests/test_api.py::test_api_analyze_document PASSED
backend/tests/test_api.py::test_api_search_documents PASSED
backend/tests/test_api.py::test_api_search_empty_query PASSED
backend/tests/test_clauses.py::test_detect_all_eight_clause_categories PASSED
backend/tests/test_clauses.py::test_non_legal_text_yields_no_clauses PASSED
backend/tests/test_extractor.py::test_sanitize_filename PASSED
backend/tests/test_extractor.py::test_validate_file_metadata_errors PASSED
backend/tests/test_extractor.py::test_extract_txt_success PASSED
backend/tests/test_extractor.py::test_extract_txt_latin1_encoding PASSED
backend/tests/test_extractor.py::test_extract_pdf_success PASSED
backend/tests/test_extractor.py::test_scanned_pdf_error PASSED
backend/tests/test_extractor.py::test_extract_docx_success PASSED
backend/tests/test_extractor.py::test_corrupted_pdf_error PASSED
backend/tests/test_extractor.py::test_corrupted_docx_error PASSED
backend/tests/test_frontend_integration.py::test_serve_frontend_index PASSED
backend/tests/test_frontend_integration.py::test_serve_frontend_index_html_alias PASSED
backend/tests/test_frontend_integration.py::test_serve_static_css_and_js_assets PASSED
backend/tests/test_frontend_integration.py::test_swagger_documentation_intact PASSED
backend/tests/test_frontend_integration.py::test_end_to_end_frontend_backend_flow PASSED
backend/tests/test_retriever.py::test_retriever_ranking_termination_over_unrelated PASSED
backend/tests/test_retriever.py::test_multi_document_search PASSED
backend/tests/test_retriever.py::test_retriever_empty_and_no_match PASSED
backend/tests/test_retriever.py::test_extract_matched_snippet_helper PASSED

======================== 34 passed in 2.00s ========================
```

---

## 11. Known Limitations

1. **Scanned PDFs (No OCR):** Only digital PDFs containing embedded text streams can be parsed by `pypdf`. Image-only or scanned PDFs lacking OCR text layers will trigger an informative notice explaining that OCR is not supported.
2. **In-Memory Session Storage:** For this lightweight demonstration stage, documents and search indexes reside in memory. They do not persist across server restarts.
3. **Lexical vs. Dense Semantic Search:** Passage retrieval is based on TF-IDF term frequencies and bi-gram statistics. Queries rely on shared vocabulary with the underlying contract and do not perform dense semantic embeddings.
4. **Heuristic Clause Identification:** Clause detection uses deterministic keyword frequencies and regular expressions. Findings are indicators for human review, not certified legal classifications.

---

## 12. Future Improvements

- Add local open-source OCR integration (e.g., Tesseract OCR) for scanned legacy legal documents.
- Optional persistent storage (e.g., SQLite via SQLAlchemy) with exportable session archives.
- Side-by-side contract diffing tool to highlight clause changes across agreement versions.
- Export analysis reports as formatted PDF or Word summaries.

---

## 13. Legal Disclaimer

> **IMPORTANT NOTICE:** AXIOM is an educational, research, and legal information retrieval tool. All statistics, extractive summaries, clause detections, and passage rankings are heuristic and probabilistic aids. This software does not provide legal advice, legal opinions, or attorney-client representations. Always consult a qualified attorney for formal legal matters.

---

<p align="center">
  <strong>Built by Sreyas | AI Project Presentation</strong>
</p>

