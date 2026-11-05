"""
Tests for TF-IDF Information Retrieval Engine and Cosine Similarity Ranking.
"""

from app.storage import document_store
from app.services.extractor import extract_document
from app.services.retriever import extract_matched_snippet


def test_retriever_ranking_termination_over_unrelated(sample_contract_text):
    """
    Controlled test: Query concerning termination must rank the termination passage #1.
    """
    raw_bytes = sample_contract_text.encode("utf-8")
    full_text, sections, meta = extract_document("contract.txt", raw_bytes)
    doc = document_store.add_document(
        filename=meta["filename"],
        file_type=meta["file_type"],
        file_size_bytes=meta["file_size_bytes"],
        word_count=meta["word_count"],
        page_count=meta["page_count"],
        full_text=full_text,
        sections=sections,
    )

    query = "immediate termination for material breach and event of default"
    response = document_store.retriever.search(query=query, top_k=5)

    assert response.total_matches > 0
    top_result = response.results[0]

    # Verify top result is from the uploaded document
    assert top_result.document_id == doc.doc_id
    assert top_result.document_name == "contract.txt"

    # Verify termination is discussed in top ranking result
    top_text_lower = top_result.full_chunk_text.lower()
    assert "terminate" in top_text_lower or "termination" in top_text_lower
    assert top_result.score > 0.1

    # Verify source attribution
    assert top_result.chunk_index >= 0
    assert top_result.matched_snippet is not None
    assert len(top_result.matched_snippet) > 10


def test_multi_document_search():
    doc1_text = """
    EMPLOYMENT AGREEMENT
    Employee shall receive an annual base salary of $120,000 USD paid bi-weekly.
    Vacation entitlement includes 20 days paid leave per calendar year.
    Health insurance benefits cover employee and immediate dependents.
    """
    doc2_text = """
    SOFTWARE LICENSE AGREEMENT
    Licensor grants Licensee a non-exclusive, non-transferable license to use the Software.
    Licensee shall not reverse engineer, decompile, or disassemble the binary files.
    The subscription fee is $5,000 per month.
    """
    # Ingest doc 1
    t1, s1, m1 = extract_document("employment.txt", doc1_text.encode("utf-8"))
    d1 = document_store.add_document(m1["filename"], m1["file_type"], m1["file_size_bytes"], m1["word_count"], m1["page_count"], t1, s1)

    # Ingest doc 2
    t2, s2, m2 = extract_document("license.txt", doc2_text.encode("utf-8"))
    d2 = document_store.add_document(m2["filename"], m2["file_type"], m2["file_size_bytes"], m2["word_count"], m2["page_count"], t2, s2)

    assert document_store.count() == 2

    # Query doc1 specific topic
    res_emp = document_store.retriever.search("annual base salary paid leave vacation", top_k=3)
    assert res_emp.total_matches > 0
    assert res_emp.results[0].document_id == d1.doc_id

    # Query doc2 specific topic
    res_lic = document_store.retriever.search("reverse engineer decompile software binary", top_k=3)
    assert res_lic.total_matches > 0
    assert res_lic.results[0].document_id == d2.doc_id

    # Test filtering by document_ids
    filtered = document_store.retriever.search("salary", document_ids=[d2.doc_id], top_k=3)
    # Even if term exists, d2 has no salary so should have 0 or very low score
    for r in filtered.results:
        assert r.document_id == d2.doc_id


def test_retriever_empty_and_no_match():
    # Empty query
    empty_res = document_store.retriever.search("", top_k=5)
    assert empty_res.total_matches == 0
    assert len(empty_res.results) == 0

    # Non-matching gibberish on empty store
    gibberish = document_store.retriever.search("xyznonexistentterm12345qwerty", top_k=5)
    assert gibberish.total_matches == 0


def test_extract_matched_snippet_helper():
    text = (
        "The party of the first part hereby agrees to provide technical consultancy services. "
        "Upon occurrence of an event of material default, the non-defaulting party may terminate immediately. "
        "All notices must be delivered via certified courier mail."
    )
    snippet = extract_matched_snippet(text, "material default terminate", max_chars=120)
    assert "default" in snippet.lower()
    assert len(snippet) <= 150
