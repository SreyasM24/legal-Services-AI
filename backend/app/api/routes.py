"""
FastAPI Route Handlers for AXIOM API.
Endpoints for health, document upload, extraction, legal analysis, clause detection, and IR search.
"""

from datetime import datetime, timezone
import sys
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, status

from app.schemas import (
    HealthResponse,
    DocumentMetadata,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentAnalysisResponse,
    AnalyzeRequest,
    SearchRequest,
    SearchResponse,
)
from app.services.extractor import extract_document, ExtractionError
from app.services.analyzer import compute_document_statistics, generate_extractive_summary
from app.services.clauses import identify_document_clauses
from app.storage import document_store


router = APIRouter(prefix="/api", tags=["AXIOM Legal API"])


@router.get("/health", response_model=HealthResponse)
async def check_health():
    """
    Check application health and individual engine statuses.
    """
    engine_status = {
        "document_extractor": "operational",
        "clause_analyzer": "operational",
        "extractive_summarizer": "operational",
        "tfidf_retriever": "operational",
    }
    return HealthResponse(
        status="healthy",
        app_name="AXIOM",
        version="1.0.0",
        python_version=sys.version.split()[0],
        engine_status=engine_status,
        documents_indexed=document_store.count(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/documents/upload",
    response_model=DocumentMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract legal document",
)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF, DOCX, or TXT legal document.
    Extracts text, preserves source pagination/sections, and indexes document for retrieval.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file was provided in the upload request.")

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file stream.")

    try:
        full_text, sections, meta = extract_document(
            filename=file.filename,
            file_bytes=file_bytes,
            content_type=file.content_type or "",
        )
    except ExtractionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Document extraction error: Could not process file '{file.filename}'.",
        )

    stored_doc = document_store.add_document(
        filename=meta["filename"],
        file_type=meta["file_type"],
        file_size_bytes=meta["file_size_bytes"],
        word_count=meta["word_count"],
        page_count=meta["page_count"],
        full_text=full_text,
        sections=sections,
    )

    return stored_doc.to_metadata()


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
)
async def list_documents():
    """
    Return list of all currently indexed documents in memory.
    """
    docs = document_store.list_documents()
    return DocumentListResponse(total_documents=len(docs), documents=docs)


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentDetailResponse,
    summary="Retrieve document text and sections",
)
async def get_document(doc_id: str):
    """
    Retrieve full extracted text, structure, and page/paragraph sections for a specific document.
    """
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{doc_id}' not found.",
        )
    return DocumentDetailResponse(
        metadata=doc.to_metadata(),
        sections=doc.sections,
        full_text=doc.full_text,
    )


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document from session memory",
)
async def delete_document(doc_id: str):
    """
    Remove a document from session storage and update search index.
    """
    success = document_store.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{doc_id}' not found.",
        )
    return {"message": f"Document '{doc_id}' successfully removed.", "remaining_documents": document_store.count()}


@router.post(
    "/documents/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Perform NLP document analysis, extractive summary, and clause detection",
)
async def analyze_document(request: AnalyzeRequest):
    """
    Analyze a previously uploaded document:
    - Computes descriptive statistics (word count, dates, monetary amounts, emails, top terms)
    - Generates sentence-level TF-IDF extractive summary preserving verbatim phrasing
    - Detects standard legal clauses across 8 predefined categories
    """
    doc = document_store.get_document(request.document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{request.document_id}' not found. Please upload it first.",
        )

    statistics = compute_document_statistics(doc.full_text, doc.sections)
    summary = generate_extractive_summary(doc.full_text, target_sentences=request.summary_sentences)
    clauses = identify_document_clauses(doc.sections, doc.full_text)

    return DocumentAnalysisResponse(
        document_id=doc.doc_id,
        filename=doc.filename,
        statistics=statistics,
        summary=summary,
        detected_clauses=clauses,
    )


@router.post(
    "/documents/search",
    response_model=SearchResponse,
    summary="Search passages across documents via TF-IDF & Cosine Similarity",
)
async def search_documents(request: SearchRequest):
    """
    Query the document corpus for relevant passages.
    Returns ranked chunks with verbatim matching snippets and page/section references.
    """
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    results = document_store.retriever.search(
        query=clean_query,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )
    return results
