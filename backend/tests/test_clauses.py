"""
Tests for Legal Clause Identification Service across the 8 required categories.
"""

import re
from app.services.clauses import identify_document_clauses, CLAUSE_PATTERNS
from app.services.extractor import extract_document


def test_detect_all_eight_clause_categories(sample_contract_text):
    raw_bytes = sample_contract_text.encode("utf-8")
    full_text, sections, _ = extract_document("contract.txt", raw_bytes)

    detected = identify_document_clauses(sections, full_text)
    detected_categories = {c.category for c in detected}

    # Verify that all 8 categories defined in CLAUSE_PATTERNS are detected
    expected_categories = set(CLAUSE_PATTERNS.keys())
    assert len(expected_categories) == 8

    for cat in expected_categories:
        assert cat in detected_categories, f"Expected clause '{cat}' to be detected in sample contract."

    normalized_full = re.sub(r"\s+", " ", full_text)
    # Verify properties of detected clauses
    for clause in detected:
        assert clause.category in expected_categories
        assert len(clause.matched_text) > 15
        assert len(clause.matched_keywords) > 0
        assert 0.0 < clause.confidence <= 1.0
        assert clause.source_location is not None
        # Matched text must be verbatim substring of original document
        assert clause.matched_text in normalized_full


def test_non_legal_text_yields_no_clauses():
    ordinary_text = """
    Yesterday morning, the weather was pleasant and sunny.
    We decided to take a stroll around the park and observed several species of migratory birds.
    After lunch at the local cafe, we returned home to read a novel.
    """
    raw_bytes = ordinary_text.encode("utf-8")
    full_text, sections, _ = extract_document("journal.txt", raw_bytes)

    detected = identify_document_clauses(sections, full_text)
    assert len(detected) == 0, "Ordinary non-legal narrative should not trigger false legal clauses"
