"""
Frontend and FastAPI Integration Tests for AXIOM.
Verifies that FastAPI properly serves index.html, static CSS/JS assets, Swagger docs,
and that all API routes interface seamlessly with the frontend client expectations.
"""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_serve_frontend_index():
    """Verify GET / delivers frontend/index.html with correct headers and title."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AXIOM" in response.text
    assert "DOCUMENT INTELLIGENCE" in response.text
    assert 'id="panel-overview"' in response.text
    assert 'id="panel-documents"' in response.text
    assert 'id="panel-analysis"' in response.text
    assert 'id="panel-search"' in response.text


def test_serve_frontend_index_html_alias():
    """Verify GET /index.html also delivers the single-page application."""
    response = client.get("/index.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AXIOM" in response.text


def test_serve_static_css_and_js_assets():
    """Verify that CSS and JS assets are served correctly through FastAPI static mounts."""
    # Stylesheet
    css_res = client.get("/css/styles.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers.get("content-type", "")
    assert "--primary:" in css_res.text or "#6B1D2F" in css_res.text

    # API Client JavaScript
    api_js_res = client.get("/js/api.js")
    assert api_js_res.status_code == 200
    assert "javascript" in api_js_res.headers.get("content-type", "")
    assert "LexiScopeAPI" in api_js_res.text
    assert "/api" in api_js_res.text

    # Main Application JavaScript
    app_js_res = client.get("/js/app.js")
    assert app_js_res.status_code == 200
    assert "javascript" in app_js_res.headers.get("content-type", "")
    assert "LexiScopeApp" in app_js_res.text


def test_swagger_documentation_intact():
    """Verify that OpenAPI documentation remains intact at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


def test_end_to_end_frontend_backend_flow(sample_contract_text):
    """
    Simulate full frontend user workflow:
    1. Upload legal document
    2. Retrieve library list
    3. Retrieve full document detail
    4. Run legal NLP analysis (stats, extractive summary, clauses)
    5. Query legal search (TF-IDF passage retrieval)
    6. Delete document from session
    """
    # 1. Upload
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("master_agreement.txt", sample_contract_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 201
    meta = upload_res.json()
    doc_id = meta["id"]
    assert meta["filename"] == "master_agreement.txt"

    # 2. List
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_documents"] >= 1
    assert any(d["id"] == doc_id for d in list_data["documents"])

    # 3. Detail
    detail_res = client.get(f"/api/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["metadata"]["id"] == doc_id
    assert len(detail["sections"]) > 0

    # 4. Analyze
    analyze_res = client.post(
        "/api/documents/analyze",
        json={"document_id": doc_id, "summary_sentences": 4},
    )
    assert analyze_res.status_code == 200
    analysis = analyze_res.json()
    assert analysis["statistics"]["word_count"] > 100
    assert len(analysis["summary"]["sentences"]) == 4
    assert len(analysis["detected_clauses"]) >= 5

    # 5. Search
    search_res = client.post(
        "/api/documents/search",
        json={"query": "material breach termination and notice", "top_k": 3},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_matches"] > 0
    assert "terminate" in search_data["results"][0]["full_chunk_text"].lower()

    # 6. Delete
    delete_res = client.delete(f"/api/documents/{doc_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["remaining_documents"] == 0
