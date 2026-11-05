"""
Legal Clause Identification Service for LexiScope.
Rule-based keyword and regular-expression detection covering 8 standard legal categories.
Labels findings as potential matches for informational review only.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from app.schemas import DetectedClause, SectionInfo


CLAUSE_PATTERNS: Dict[str, Dict[str, Any]] = {
    "Confidentiality and Non-Disclosure": {
        "keywords": [
            "confidential information",
            "non-disclosure",
            "nondisclosure",
            "proprietary information",
            "trade secret",
            "duty of confidentiality",
            "confidentiality obligations",
            "recipient agrees not to disclose",
            "standard of care",
            "compelled disclosure",
            "return or destruction",
        ],
        "regex": r"\b(confidential\s+information|non-?disclosure|trade\s+secrets?|proprietary\s+(information|materials)|duty\s+of\s+confidentiality)\b",
    },
    "Termination and Default": {
        "keywords": [
            "termination",
            "terminate this agreement",
            "event of default",
            "material breach",
            "cure period",
            "written notice of termination",
            "upon termination",
            "immediate termination",
            "survival of terms",
            "right to terminate",
        ],
        "regex": r"\b(terminat(e|ed|ion|ing)|events?\s+of\s+default|material\s+breach|written\s+notice\s+of\s+termination|right\s+to\s+terminate)\b",
    },
    "Indemnity and Hold Harmless": {
        "keywords": [
            "indemnify",
            "indemnification",
            "hold harmless",
            "defend and hold harmless",
            "indemnified party",
            "indemnifying party",
            "losses, damages, costs",
            "third-party claims",
            "reasonable attorneys' fees",
        ],
        "regex": r"\b(indemnif(y|ied|ication)|hold\s+harmless|defend\s+and\s+hold\s+harmless|third-?party\s+claims?)\b",
    },
    "Limitation of Liability": {
        "keywords": [
            "limitation of liability",
            "in no event shall",
            "consequential damages",
            "indirect, incidental, special",
            "aggregate liability",
            "maximum liability",
            "cap on liability",
            "punitive damages",
            "loss of profits",
            "disclaimer of damages",
        ],
        "regex": r"\b(limitation\s+of\s+liability|in\s+no\s+event\s+shall|consequential\s+damages|aggregate\s+liability|maximum\s+(aggregate\s+)?liability)\b",
    },
    "Governing Law and Dispute Resolution": {
        "keywords": [
            "governing law",
            "dispute resolution",
            "jurisdiction",
            "arbitration",
            "venue",
            "laws of the state of",
            "exclusive jurisdiction",
            "american arbitration association",
            "binding arbitration",
            "competent courts",
        ],
        "regex": r"\b(governing\s+law|dispute\s+resolution|arbitration|exclusive\s+jurisdiction|laws\s+of\s+(the\s+state\s+of|the\s+republic|india|new\s+york|delaware|california|england))\b",
    },
    "Warranties and Representations": {
        "keywords": [
            "representations and warranties",
            "warrants that",
            "represents and warrants",
            "as is",
            "disclaimer of warranties",
            "express or implied warranties",
            "merchantability",
            "fitness for a particular purpose",
            "covenants",
            "authority to enter into",
        ],
        "regex": r"\b(representations?\s+and\s+warrant(y|ies)|represents?\s+and\s+warrants?|disclaimer\s+of\s+warranties?|fitness\s+for\s+a\s+particular\s+purpose|merchantability|as[\s-]is)\b",
    },
    "Force Majeure": {
        "keywords": [
            "force majeure",
            "acts of god",
            "unforeseeable circumstances",
            "beyond reasonable control",
            "natural disasters",
            "epidemic",
            "pandemic",
            "war, terrorism, riot",
            "labor strikes",
            "governmental action",
        ],
        "regex": r"\b(force\s+majeure|acts?\s+of\s+god|beyond\s+(the\s+)?reasonable\s+control|unforeseeable\s+circumstances)\b",
    },
    "Intellectual Property Rights": {
        "keywords": [
            "intellectual property",
            "patents, copyrights, trademarks",
            "work for hire",
            "ownership of deliverables",
            "proprietary rights",
            "moral rights",
            "license grant",
            "infringement",
            "title and ownership",
            "work made for hire",
        ],
        "regex": r"\b(intellectual\s+property|patents?,\s*copyrights?|work\s+(made\s+)?for\s+hire|proprietary\s+rights|ownership\s+of\s+deliverables|license\s+grant)\b",
    },
}


from app.services.analyzer import parse_sentences


def detect_clauses_in_section(
    section_text: str,
    location_label: str,
    section_index: Optional[int] = None,
    page_number: Optional[int] = None,
) -> List[DetectedClause]:
    """
    Scan a document section (or paragraph/page) and detect candidate legal clauses.
    """
    detected: List[DetectedClause] = []
    sentences = parse_sentences(section_text)
    if not sentences:
        sentences = [section_text.strip()] if len(section_text.strip()) > 15 else []

    for category, spec in CLAUSE_PATTERNS.items():
        pattern_regex = re.compile(spec["regex"], re.IGNORECASE)
        keywords_list = spec["keywords"]

        # Check section-level first or sentence-level
        for sentence in sentences:
            sentence_lower = sentence.lower()
            matched_kw = []

            for kw in keywords_list:
                if kw in sentence_lower:
                    matched_kw.append(kw)

            regex_match = pattern_regex.search(sentence)
            if regex_match:
                matched_kw.append(regex_match.group(0).lower())

            matched_kw = sorted(list(set(matched_kw)))

            if matched_kw:
                # Calculate heuristic confidence score
                # Base 0.5 for 1 keyword/regex match, +0.15 for each additional up to 0.95
                confidence = min(0.95, 0.50 + (len(matched_kw) * 0.12))
                confidence = round(confidence, 2)

                detected.append(
                    DetectedClause(
                        category=category,
                        matched_text=sentence,
                        matched_keywords=matched_kw,
                        confidence=confidence,
                        source_location=location_label,
                        section_index=section_index,
                        page_number=page_number,
                    )
                )

    return detected


def identify_document_clauses(sections: List[SectionInfo], full_text: str) -> List[DetectedClause]:
    """
    Detect all clauses across all document sections.
    Deduplicates overlapping or redundant matches for the same category and sentence.
    """
    all_clauses: List[DetectedClause] = []
    seen_matches = set()

    for sec in sections:
        loc = f"Page {sec.page_number}" if sec.page_number else f"Section {sec.index + 1}"
        if sec.heading and sec.heading != f"Page {sec.page_number}":
            loc = f"{loc} ({sec.heading})"

        sec_clauses = detect_clauses_in_section(
            section_text=sec.text,
            location_label=loc,
            section_index=sec.index,
            page_number=sec.page_number,
        )

        for c in sec_clauses:
            key = (c.category, c.matched_text.strip().lower()[:120])
            if key not in seen_matches:
                seen_matches.add(key)
                all_clauses.append(c)

    # If no clauses were found from sections (e.g. unsegmented or single block), check full text
    if not all_clauses and full_text.strip():
        loc = "Document Body"
        full_clauses = detect_clauses_in_section(full_text, loc)
        for c in full_clauses:
            key = (c.category, c.matched_text.strip().lower()[:120])
            if key not in seen_matches:
                seen_matches.add(key)
                all_clauses.append(c)

    # Sort clauses by category and confidence descending
    all_clauses.sort(key=lambda x: (x.category, -x.confidence))
    return all_clauses
