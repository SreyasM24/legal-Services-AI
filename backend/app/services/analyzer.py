"""
Legal Document Analysis Engine for LexiScope.
Computes document statistics, entity extraction (dates, monetary amounts, emails, top terms),
and extractive summarization via sentence-level TF-IDF importance ranking.
"""

import collections
import re
from typing import List, Dict, Any, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from app.schemas import (
    DocumentStatistics,
    DocumentSummary,
    TermFrequency,
    SectionInfo,
)


# Domain-specific legal boilerplate stopwords to filter from key terms
LEGAL_STOPWORDS = {
    "shall", "party", "parties", "agreement", "herein", "hereof", "thereto", "thereof",
    "hereto", "pursuant", "section", "article", "clause", "including", "without",
    "limitation", "set", "forth", "may", "must", "either", "neither", "whereas",
    "now", "therefore", "witnesseth", "in", "the", "and", "to", "of", "a", "an", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "should", "could", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below", "from",
    "up", "down", "on", "off", "over", "under", "again", "further", "then", "once",
    "such", "other", "any", "all", "each", "every", "both", "some", "provided", "applicable",
    "terms", "conditions", "accordance", "time", "date", "effect", "duly", "executed",
    "provisions", "obligations", "rights", "respect", "defined", "meaning", "hereunder",
}


def extract_dates(text: str) -> List[str]:
    """
    Extract significant date expressions from legal text.
    Handles formats like:
    - January 15, 2024 / 15th day of January, 2024
    - 2024-05-30
    - 15/01/2024 or 01/15/2024
    """
    patterns = [
        # "15th day of October, 2024" or "1st day of May 2025"
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}\b",
        # "October 15, 2024" or "Oct 15 2024" or "15 October 2024"
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[.]?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[.]?,?\s+\d{4}\b",
        # ISO format: 2024-12-31
        r"\b\d{4}-\d{2}-\d{2}\b",
        # Slash format: 12/31/2024 or 31/12/2024
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    ]

    found = []
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip()
            if cleaned not in found:
                found.append(cleaned)
    return found[:20]


def extract_monetary_amounts(text: str) -> List[str]:
    """
    Extract monetary expressions, currency figures, and compensation figures.
    """
    patterns = [
        # $1,000,000 or $500.00
        r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?:\s*(?:million|billion|thousand|USD))?\b",
        # USD 1,000,000 or EUR 500
        r"\b(?:USD|EUR|GBP|INR|AUD|CAD)\s*[\$€£₹]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?:\s*(?:million|billion|thousand))?\b",
        # ₹ 50,000 or Rs. 50,000
        r"(?:₹|Rs\.?)\s*\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?(?:\s*(?:crore|lakh|thousand))?\b",
        # Words: "Five Hundred Thousand Dollars ($500,000)"
        r"\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:US\s*)?Dollars\b",
    ]

    found = []
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip()
            if cleaned not in found:
                found.append(cleaned)
    return found[:20]


def extract_emails(text: str) -> List[str]:
    """
    Extract valid email addresses.
    """
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    matches = re.findall(pattern, text)
    return sorted(list(set(matches)))[:20]


def extract_top_terms(text: str, top_n: int = 12) -> List[TermFrequency]:
    """
    Extract frequently occurring domain keywords, excluding boilerplate legal stopwords.
    """
    words = re.findall(r"\b[A-Za-z]{3,}\b", text.lower())
    filtered = [w for w in words if w not in LEGAL_STOPWORDS]
    counts = collections.Counter(filtered)
    
    return [
        TermFrequency(term=term, count=cnt)
        for term, cnt in counts.most_common(top_n)
    ]


COMMON_ABBREVIATIONS = [
    "e.g.", "i.e.", "etc.", "vs.", "v.", "inc.", "corp.", "ltd.", "co.",
    "sec.", "art.", "no.", "vol.", "al.", "approx.", "para.", "ref.",
    "dept.", "u.s.", "u.k.", "jan.", "feb.", "mar.", "apr.", "jun.",
    "jul.", "aug.", "sep.", "sept.", "oct.", "nov.", "dec.", "mr.", "ms.", "mrs.", "dr."
]


def parse_sentences(text: str) -> List[str]:
    """
    Split text into individual sentences while preserving legal citations and abbreviations.
    Uses fixed-width lookbehind compatible with all Python versions.
    """
    clean_text = re.sub(r"\s+", " ", text).strip()
    if not clean_text:
        return []

    # Protect abbreviations by temporarily replacing their periods
    protected = clean_text
    for abbr in COMMON_ABBREVIATIONS:
        pattern = re.compile(re.escape(abbr), re.IGNORECASE)
        protected = pattern.sub(abbr.replace(".", "§DOT§"), protected)

    # Protect single uppercase letter initials (e.g., 'John F. Kennedy')
    protected = re.sub(r"\b([A-Z])\.\s+", r"\1§DOT§ ", protected)

    # Split using fixed-width lookbehind for sentence terminator
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])", protected)

    sentences = []
    for s in raw_sentences:
        restored = s.replace("§DOT§", ".").strip()
        if len(restored) > 15:
            sentences.append(restored)

    return sentences


def generate_extractive_summary(text: str, target_sentences: int = 4) -> DocumentSummary:
    """
    Generate an extractive summary using sentence-level TF-IDF centrality.
    Scores sentences by their cosine similarity to the aggregate document centroid.
    Maintains exact original wording and presentation in original document order.
    """
    sentences = parse_sentences(text)
    total_words = len(text.split())

    if len(sentences) == 0:
        return DocumentSummary(
            sentences=[],
            full_summary=text[:300].strip(),
            sentence_count=0,
            compression_ratio=1.0,
        )

    if len(sentences) <= target_sentences:
        full_sum = " ".join(sentences)
        sum_words = len(full_sum.split())
        ratio = round(sum_words / max(1, total_words), 3)
        return DocumentSummary(
            sentences=sentences,
            full_summary=full_sum,
            sentence_count=len(sentences),
            compression_ratio=ratio,
        )

    try:
        # Build TF-IDF matrix for all sentences (max_df=1.0 allows all sentence counts)
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_df=1.0,
            min_df=1,
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform(sentences)

        # Compute document centroid (mean TF-IDF vector across all sentences)
        centroid = np.asarray(tfidf_matrix.mean(axis=0))

        # Compute cosine similarity of each sentence to the centroid
        sentence_vectors = tfidf_matrix.toarray()
        centroid_norm = np.linalg.norm(centroid)
        
        scores = []
        for idx, s_vec in enumerate(sentence_vectors):
            s_norm = np.linalg.norm(s_vec)
            if s_norm > 0 and centroid_norm > 0:
                sim = np.dot(s_vec, centroid.T)[0, 0] / (s_norm * centroid_norm)
            else:
                sim = 0.0

            # Slight position bias: opening introductory clauses often define core obligations
            pos_weight = 1.0 + (0.15 if idx < 3 else 0.0)
            length_penalty = 1.0
            s_len = len(sentences[idx].split())
            if s_len < 8 or s_len > 70:
                length_penalty = 0.7  # discourage extremely short or run-on sentences

            final_score = sim * pos_weight * length_penalty
            scores.append((idx, final_score))

        # Sort by score descending and take top N
        scores.sort(key=lambda x: x[1], reverse=True)
        chosen_indices = [idx for idx, _ in scores[:target_sentences]]

        # Crucial: Re-sort chosen sentences by original appearance index
        chosen_indices.sort()
        summary_sentences = [sentences[i] for i in chosen_indices]

    except Exception:
        # Fallback to lead sentences if TF-IDF fails (e.g. non-ascii or single-word vocab)
        summary_sentences = sentences[:target_sentences]

    full_summary = " ".join(summary_sentences)
    sum_words = len(full_summary.split())
    compression_ratio = round(sum_words / max(1, total_words), 3)

    return DocumentSummary(
        sentences=summary_sentences,
        full_summary=full_summary,
        sentence_count=len(summary_sentences),
        compression_ratio=compression_ratio,
    )


def compute_document_statistics(full_text: str, sections: List[SectionInfo]) -> DocumentStatistics:
    """
    Calculate comprehensive descriptive statistics for the legal document.
    """
    words = full_text.split()
    word_count = len(words)
    sentences = parse_sentences(full_text)
    sentence_count = len(sentences)
    paragraph_count = max(len(sections), len(re.split(r"\n\s*\n", full_text.strip())))

    dates = extract_dates(full_text)
    monetary = extract_monetary_amounts(full_text)
    emails = extract_emails(full_text)
    top_terms = extract_top_terms(full_text)

    return DocumentStatistics(
        word_count=word_count,
        sentence_count=sentence_count,
        paragraph_count=paragraph_count,
        dates=dates,
        monetary_amounts=monetary,
        emails=emails,
        top_terms=top_terms,
    )
