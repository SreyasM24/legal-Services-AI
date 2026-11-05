"""
Pydantic schemas for AXIOM API requests, responses, and internal data structures.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


LEGAL_DISCLAIMER = (
    "Disclaimer: AXIOM is an educational and legal information analysis tool. "
    "All statistics, summaries, clause detections, and search rankings are rule-based and "
    "probabilistic aids. This application does not provide legal advice, legal opinions, "
    "or formal attorney-client work product."
)


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status ('healthy' or 'degraded')")
    app_name: str = Field("AXIOM", description="Application name")
    version: str = Field("1.0.0", description="Application semantic version")
    python_version: str = Field(..., description="Runtime Python version")
    engine_status: Dict[str, str] = Field(..., description="Status of individual engine components")
    documents_indexed: int = Field(..., description="Number of currently loaded documents in memory")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of health check")


class SectionInfo(BaseModel):
    index: int = Field(..., description="Sequential 0-based section index")
    page_number: Optional[int] = Field(None, description="1-based page number if available (e.g. from PDF)")
    heading: Optional[str] = Field(None, description="Extracted heading or section label if detected")
    text: str = Field(..., description="Raw text content of this section")
    word_count: int = Field(..., description="Number of words in this section")


class DocumentMetadata(BaseModel):
    id: str = Field(..., description="Unique UUID assigned to the document")
    filename: str = Field(..., description="Sanitized original document filename")
    file_type: str = Field(..., description="Document file extension/type ('pdf', 'docx', 'txt')")
    file_size_bytes: int = Field(..., description="Total size in bytes")
    word_count: int = Field(..., description="Total word count extracted")
    page_count: int = Field(..., description="Total pages (PDF) or estimated pages (DOCX/TXT)")
    section_count: int = Field(..., description="Total segmented sections/paragraphs")
    uploaded_at: str = Field(..., description="ISO 8601 timestamp when uploaded")


class DocumentDetailResponse(BaseModel):
    metadata: DocumentMetadata
    sections: List[SectionInfo]
    full_text: str


class DocumentListResponse(BaseModel):
    total_documents: int
    documents: List[DocumentMetadata]


class TermFrequency(BaseModel):
    term: str = Field(..., description="Extracted legal/content term")
    count: int = Field(..., description="Raw occurrence count in document")


class DocumentStatistics(BaseModel):
    word_count: int = Field(..., description="Total number of words")
    sentence_count: int = Field(..., description="Total number of parsed sentences")
    paragraph_count: int = Field(..., description="Total number of parsed paragraphs")
    dates: List[str] = Field(default_factory=list, description="Extracted dates found in document")
    monetary_amounts: List[str] = Field(default_factory=list, description="Extracted monetary references")
    emails: List[str] = Field(default_factory=list, description="Extracted email addresses")
    top_terms: List[TermFrequency] = Field(default_factory=list, description="Most frequent key terms")


class DetectedClause(BaseModel):
    category: str = Field(..., description="One of 8 predefined legal clause categories")
    matched_text: str = Field(..., description="Verbatim sentence or paragraph text containing the match")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords that triggered detection")
    confidence: float = Field(..., description="Heuristic score between 0.0 and 1.0 based on match density")
    source_location: str = Field(..., description="Human-readable location (e.g. 'Page 2', 'Paragraph 5')")
    section_index: Optional[int] = Field(None, description="0-based section index if matched in a specific section")
    page_number: Optional[int] = Field(None, description="1-based page number if available")


class DocumentSummary(BaseModel):
    sentences: List[str] = Field(default_factory=list, description="Selected representative sentences in original order")
    full_summary: str = Field(..., description="Concatenated summary text preserving original wording")
    sentence_count: int = Field(..., description="Number of sentences in summary")
    compression_ratio: float = Field(..., description="Ratio of summary words to original document words")


class DocumentAnalysisResponse(BaseModel):
    document_id: str
    filename: str
    statistics: DocumentStatistics
    summary: DocumentSummary
    detected_clauses: List[DetectedClause]
    disclaimer: str = LEGAL_DISCLAIMER


class AnalyzeRequest(BaseModel):
    document_id: str = Field(..., description="Unique ID of document to analyze")
    summary_sentences: int = Field(4, ge=1, le=15, description="Target number of sentences for summary")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language search query")
    document_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs to restrict search scope")
    top_k: int = Field(5, ge=1, le=25, description="Maximum number of ranked results to return")


class SearchResultItem(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    page_number: Optional[int] = None
    section_reference: Optional[str] = None
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    matched_snippet: str = Field(..., description="Highlighted excerpt surrounding key matching query terms")
    full_chunk_text: str = Field(..., description="Complete text of matching document chunk")


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    results: List[SearchResultItem]
    execution_time_ms: float
    disclaimer: str = LEGAL_DISCLAIMER
