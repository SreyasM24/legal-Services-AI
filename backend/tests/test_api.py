"""
API Integration Tests for LexiScope FastAPI endpoints.
Tests endpoints using FastAPI TestClient (HTTPX).
"""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "AXIOM"
    assert "document_extractor" in data["engine_status"]
    assert "clause_analyzer" in data["engine_status"]
    assert "extractive_summarizer" in data["engine_status"]
    assert "tfidf_retriever" in data["engine_status"]


def test_api_upload_txt(sample_contract_text):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("legal_contract.txt", sample_contract_text.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "legal_contract.txt"
    assert data["file_type"] == "txt"
    assert data["word_count"] > 100


def test_api_upload_pdf(sample_pdf_bytes):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("agreement.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "pdf"
    assert data["page_count"] == 1


def test_api_upload_docx(sample_docx_bytes):
    response = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "contract.docx",
                sample_docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_type"] == "docx"


def test_api_upload_invalid_format():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("malicious.exe", b"binarycontent", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_api_upload_empty_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_api_get_documents_and_detail(sample_contract_text):
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("test_doc.txt", sample_contract_text.encode("utf-8"), "text/plain")},
    )
    doc_id = upload_res.json()["id"]

    # List documents
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_documents"] >= 1
    assert any(d["id"] == doc_id for d in list_data["documents"])

    # Get specific document detail
    detail_res = client.get(f"/api/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["metadata"]["id"] == doc_id
    assert len(detail_data["sections"]) > 0
    assert "CONFIDENTIALITY" in detail_data["full_text"]


def test_api_get_document_not_found():
    response = client.get("/api/documents/non-existent-uuid-12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_analyze_document(sample_contract_text):
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("nda.txt", sample_contract_text.encode("utf-8"), "text/plain")},
    )
    doc_id = upload_res.json()["id"]

    # Analyze document
    analyze_res = client.post(
        "/api/documents/analyze",
        json={"document_id": doc_id, "summary_sentences": 4},
    )
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["document_id"] == doc_id
    assert "statistics" in data
    assert data["statistics"]["word_count"] > 100
    assert len(data["statistics"]["dates"]) > 0
    assert len(data["statistics"]["monetary_amounts"]) > 0

    assert "summary" in data
    assert data["summary"]["sentence_count"] == 4
    assert len(data["summary"]["full_summary"]) > 50

    assert "detected_clauses" in data
    assert len(data["detected_clauses"]) >= 5
    categories = [c["category"] for c in data["detected_clauses"]]
    assert "Termination and Default" in categories
    assert "Indemnity and Hold Harmless" in categories
    assert "Limitation of Liability" in categories

    assert "disclaimer" in data
    assert "Disclaimer:" in data["disclaimer"]


def test_api_search_documents(sample_contract_text):
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("nda_search.txt", sample_contract_text.encode("utf-8"), "text/plain")},
    )
    doc_id = upload_res.json()["id"]

    search_res = client.post(
        "/api/documents/search",
        json={"query": "arbitration jurisdiction dispute resolution", "top_k": 3},
    )
    assert search_res.status_code == 200
    data = search_res.json()

    assert data["query"] == "arbitration jurisdiction dispute resolution"
    assert data["total_matches"] > 0
    top = data["results"][0]
    assert top["document_id"] == doc_id
    assert "arbitration" in top["full_chunk_text"].lower() or "dispute" in top["full_chunk_text"].lower()
    assert top["score"] > 0.05
    assert len(top["matched_snippet"]) > 0


def test_api_search_empty_query():
    response = client.post(
        "/api/documents/search",
        json={"query": "   ", "top_k": 5},
    )
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()
