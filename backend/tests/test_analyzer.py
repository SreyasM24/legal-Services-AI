"""
Tests for Legal Document Analysis Engine (statistics, entities, extractive summary).
"""

import re
from app.services.analyzer import (
    compute_document_statistics,
    generate_extractive_summary,
    extract_dates,
    extract_monetary_amounts,
    extract_emails,
    extract_top_terms,
    parse_sentences,
)
from app.services.extractor import extract_document


def test_statistics_entity_extraction(sample_contract_text):
    raw_bytes = sample_contract_text.encode("utf-8")
    full_text, sections, _ = extract_document("test.txt", raw_bytes)

    stats = compute_document_statistics(full_text, sections)

    assert stats.word_count > 150
    assert stats.sentence_count >= 8
    assert stats.paragraph_count >= 5

    # Check dates
    date_matches = [d for d in stats.dates if "October 15, 2024" in d]
    assert len(date_matches) > 0

    # Check monetary amounts
    monetary_str = " ".join(stats.monetary_amounts)
    assert "150,000" in monetary_str or "50,000" in monetary_str

    # Check emails
    assert "contact@nexuscorp.com" in stats.emails
    assert "legal@apexsolutions.com" in stats.emails

    # Check top terms - stopwords should not dominate
    terms = [t.term for t in stats.top_terms]
    assert "shall" not in terms
    assert "party" not in terms
    assert "agreement" not in terms


def test_extractive_summary_quality(sample_contract_text):
    target = 4
    summary = generate_extractive_summary(sample_contract_text, target_sentences=target)

    assert summary.sentence_count == target
    assert len(summary.sentences) == target
    assert summary.compression_ratio < 1.0
    assert summary.compression_ratio > 0.05

    # Verify each sentence is verbatim from original text (ignoring newline vs space differences)
    normalized_full = re.sub(r"\s+", " ", sample_contract_text)
    for sent in summary.sentences:
        assert sent in normalized_full

    # Verify original document appearance order is preserved
    positions = [normalized_full.find(sent) for sent in summary.sentences]
    assert positions == sorted(positions), "Summary sentences must follow chronological document order"


def test_extractive_summary_short_text():
    short_text = "This is a single short agreement paragraph. It has only two sentences."
    summary = generate_extractive_summary(short_text, target_sentences=5)

    assert summary.sentence_count <= 2
    assert summary.compression_ratio > 0.0
