from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class CheckStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MatchType(str, Enum):
    EXACT = "exact"
    PARAPHRASE = "paraphrase"
    PARTIAL = "partial"


class PlagiarismCheckCreate(BaseModel):
    document_id: int = Field(..., description="ID of the document to check")


class SentenceMatchResponse(BaseModel):
    user_sentence: str
    reference_sentence: str
    similarity_score: float
    match_type: MatchType


class PlagiarismMatchResponse(BaseModel):
    reference_document: Dict[str, Any]
    similarity_score: float
    matched_sentences_count: int
    sentence_matches: List[SentenceMatchResponse]


class PlagiarismCheckResponse(BaseModel):
    id: int
    user_id: int
    user_document_id: int
    total_similarity_score: float
    check_status: CheckStatus
    processing_time: Optional[int]
    reference_documents_count: int
    matches_found: int
    created_at: datetime

    class Config:
        from_attributes = True


class PlagiarismCheckDetailResponse(BaseModel):
    check: Dict[str, Any]
    document: Dict[str, Any]
    matches: List[PlagiarismMatchResponse]
