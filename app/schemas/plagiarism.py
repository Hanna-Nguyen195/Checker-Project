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


# Schema for external API result structure
class SimilarityContent(BaseModel):
    content: str = Field(..., min_length=1, description="Matched sentence content")
    rects: List[List[float]] = Field(..., min_items=1, description="Bounding box coordinates")


class SimilarityBoxSentence(BaseModel):
    pageNumber: int = Field(..., ge=1, description="Page number where match was found")
    similarity_content: List[SimilarityContent] = Field(..., min_items=1, description="List of matched content on this page")


class SimilarityDocument(BaseModel):
    name: str = Field(..., min_length=1, description="Reference document name")
    similarity_value: float = Field(..., ge=0, le=100, description="Similarity percentage")
    similarity_box_sentences: List[SimilarityBoxSentence] = Field(..., min_items=1, description="Matched sentences by page")
    reference_document_id: int = Field(..., gt=0, description="Required reference document ID from database")


class SizePageInfo(BaseModel):
    width: float = Field(..., gt=0, description="Page width")
    height: float = Field(..., gt=0, description="Page height")


class ExternalApiData(BaseModel):
    total_percent: float = Field(..., ge=0, le=100, description="Overall similarity percentage")
    size_page: SizePageInfo
    similarity_documents: List[SimilarityDocument] = Field(..., min_items=1, description="List of matched documents")


class ExternalApiResult(BaseModel):
    data: ExternalApiData
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "total_percent": 72.5,
                    "size_page": {
                        "width": 595.0,
                        "height": 842.0
                    },
                    "similarity_documents": [
                        {
                            "name": "document_A.pdf",
                            "similarity_value": 45.0,
                            "reference_document_id": 1,
                            "similarity_box_sentences": [
                                {
                                    "pageNumber": 1,
                                    "similarity_content": [
                                        {
                                            "content": "This is a matched sentence from the input document.",
                                            "rects": [
                                                [100.0, 200.0, 300.0, 220.0],
                                                [100.0, 225.0, 300.0, 245.0]
                                            ]
                                        },
                                        {
                                            "content": "Another similar sentence found in the document.",
                                            "rects": [
                                                [120.0, 250.0, 310.0, 270.0]
                                            ]
                                        },
                                        {
                                            "content": "Third matched sentence with multiple bounding boxes.",
                                            "rects": [
                                                [90.0, 280.0, 280.0, 300.0],
                                                [90.0, 305.0, 280.0, 325.0]
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "pageNumber": 2,
                                    "similarity_content": [
                                        {
                                            "content": "Sentence match found on page 2 of the document.",
                                            "rects": [
                                                [85.0, 150.0, 275.0, 170.0]
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "pageNumber": 3,
                                    "similarity_content": [
                                        {
                                            "content": "Yet another matched sentence on page 3.",
                                            "rects": [
                                                [80.0, 400.0, 280.0, 420.0]
                                            ]
                                        },
                                        {
                                            "content": "Final sentence match with detailed coordinates.",
                                            "rects": [
                                                [75.0, 450.0, 285.0, 470.0],
                                                [75.0, 475.0, 285.0, 495.0]
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "name": "document_B.pdf",
                            "similarity_value": 30.0,
                            "reference_document_id": 2,
                            "similarity_box_sentences": [
                                {
                                    "pageNumber": 1,
                                    "similarity_content": [
                                        {
                                            "content": "Opening sentence match in document B.",
                                            "rects": [
                                                [110.0, 180.0, 320.0, 200.0]
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "pageNumber": 2,
                                    "similarity_content": [
                                        {
                                            "content": "Overlapping sentence found in another document.",
                                            "rects": [
                                                [150.0, 220.0, 320.0, 240.0]
                                            ]
                                        },
                                        {
                                            "content": "Additional matched content on the same page.",
                                            "rects": [
                                                [140.0, 260.0, 330.0, 280.0],
                                                [140.0, 285.0, 330.0, 305.0]
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "pageNumber": 4,
                                    "similarity_content": [
                                        {
                                            "content": "Final page match with comprehensive bounding data.",
                                            "rects": [
                                                [95.0, 350.0, 295.0, 370.0]
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "name": "document_C.pdf",
                            "similarity_value": 15.5,
                            "reference_document_id": 3,
                            "similarity_box_sentences": [
                                {
                                    "pageNumber": 1,
                                    "similarity_content": [
                                        {
                                            "content": "Minor similarity detected in document C.",
                                            "rects": [
                                                [105.0, 190.0, 305.0, 210.0]
                                            ]
                                        },
                                        {
                                            "content": "Secondary match with lower confidence score.",
                                            "rects": [
                                                [100.0, 230.0, 300.0, 250.0]
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }
