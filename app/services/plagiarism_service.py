from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog
import time

from app.models.plagiarism import PlagiarismCheck, PlagiarismMatch, SentenceMatch
from app.models.document import UserDocument, ReferenceDocument
from app.services.storage_service import StorageService
from app.core.exceptions import NotFoundException, PlagiarismCheckException
from app.utils.helpers import calculate_similarity_percentage

logger = structlog.get_logger(__name__)


class PlagiarismService:
    """Service for plagiarism detection operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = StorageService()
    
    def start_plagiarism_check(self, user_id: int, document_id: int) -> PlagiarismCheck:
        """Start plagiarism check for a user document."""
        # Verify document exists and belongs to user
        document = self.db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == user_id
        ).first()
        
        if not document:
            raise NotFoundException("Document not found")
        
        # Create plagiarism check record
        check = PlagiarismCheck(
            user_id=user_id,
            user_document_id=document_id,
            total_similarity_score=0.0,
            check_status="processing"
        )
        
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        
        logger.info("Plagiarism check started", check_id=check.id, document_id=document_id)
        
        # Process the check asynchronously (simplified for demo)
        try:
            self._process_plagiarism_check(check)
        except Exception as e:
            logger.error("Plagiarism check failed", check_id=check.id, error=str(e))
            check.check_status = "failed"
            self.db.commit()
            raise PlagiarismCheckException(f"Plagiarism check failed: {e}")
        
        return check
    
    def _process_plagiarism_check(self, check: PlagiarismCheck) -> None:
        """Process plagiarism check against reference documents."""
        start_time = time.time()
        
        try:
            # Get user document content
            user_doc = check.user_document
            user_content = self.storage_service.download_file(user_doc.object_id)
            user_text = user_content.decode('utf-8', errors='ignore')
            
            # Get all reference documents
            reference_docs = self.db.query(ReferenceDocument).all()
            
            total_matches = 0
            total_similarity = 0.0
            
            # Compare against each reference document
            for ref_doc in reference_docs:
                try:
                    ref_content = self.storage_service.download_file(ref_doc.object_id)
                    ref_text = ref_content.decode('utf-8', errors='ignore')
                    
                    # Perform similarity analysis (simplified)
                    similarity_result = self._analyze_similarity(user_text, ref_text)
                    
                    if similarity_result['similarity_score'] > 0:
                        # Create plagiarism match record
                        match = PlagiarismMatch(
                            check_id=check.id,
                            reference_document_id=ref_doc.id,
                            similarity_score=similarity_result['similarity_score'],
                            matched_sentences_count=len(similarity_result['sentence_matches'])
                        )
                        
                        self.db.add(match)
                        self.db.flush()  # Get the match ID
                        
                        # Create sentence matches
                        for sentence_match in similarity_result['sentence_matches']:
                            sent_match = SentenceMatch(
                                match_id=match.id,
                                user_sentence_text=sentence_match['user_sentence'],
                                user_sentence_start=sentence_match['user_start'],
                                user_sentence_end=sentence_match['user_end'],
                                reference_sentence_text=sentence_match['ref_sentence'],
                                reference_sentence_start=sentence_match['ref_start'],
                                reference_sentence_end=sentence_match['ref_end'],
                                similarity_score=sentence_match['score'],
                                match_type=sentence_match['type']
                            )
                            self.db.add(sent_match)
                        
                        total_matches += 1
                        total_similarity += similarity_result['similarity_score']
                
                except Exception as e:
                    logger.warning(
                        "Failed to process reference document",
                        ref_doc_id=ref_doc.id,
                        error=str(e)
                    )
                    continue
            
            # Calculate overall similarity score
            overall_similarity = total_similarity / len(reference_docs) if reference_docs else 0.0
            
            # Update check results
            check.total_similarity_score = round(overall_similarity, 2)
            check.reference_documents_count = len(reference_docs)
            check.matches_found = total_matches
            check.processing_time = int((time.time() - start_time) * 1000)  # milliseconds
            check.check_status = "completed"
            
            self.db.commit()
            
            logger.info(
                "Plagiarism check completed",
                check_id=check.id,
                similarity_score=check.total_similarity_score,
                matches_found=total_matches,
                processing_time=check.processing_time
            )
            
        except Exception as e:
            logger.error("Error processing plagiarism check", check_id=check.id, error=str(e))
            check.check_status = "failed"
            self.db.commit()
            raise
    
    def _analyze_similarity(self, user_text: str, reference_text: str) -> Dict[str, Any]:
        """Analyze similarity between two texts (simplified implementation)."""
        # This is a simplified implementation for demonstration
        # In production, you would use advanced NLP techniques
        
        user_sentences = self._split_into_sentences(user_text)
        ref_sentences = self._split_into_sentences(reference_text)
        
        sentence_matches = []
        total_score = 0.0
        
        for i, user_sentence in enumerate(user_sentences):
            for j, ref_sentence in enumerate(ref_sentences):
                similarity = self._calculate_sentence_similarity(user_sentence, ref_sentence)
                
                if similarity > 0.7:  # Threshold for considering a match
                    sentence_matches.append({
                        'user_sentence': user_sentence,
                        'user_start': i * 100,  # Simplified position
                        'user_end': (i + 1) * 100,
                        'ref_sentence': ref_sentence,
                        'ref_start': j * 100,
                        'ref_end': (j + 1) * 100,
                        'score': similarity,
                        'type': 'exact' if similarity > 0.9 else 'paraphrase'
                    })
                    total_score += similarity
        
        overall_similarity = (total_score / max(len(user_sentences), 1)) * 100
        
        return {
            'similarity_score': min(overall_similarity, 100.0),
            'sentence_matches': sentence_matches
        }
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (simplified)."""
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_sentence_similarity(self, sentence1: str, sentence2: str) -> float:
        """Calculate similarity between two sentences (simplified)."""
        # Simple word overlap similarity
        words1 = set(sentence1.lower().split())
        words2 = set(sentence2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_plagiarism_check(self, check_id: int, user_id: Optional[int] = None) -> Optional[PlagiarismCheck]:
        """Get plagiarism check by ID."""
        query = self.db.query(PlagiarismCheck).filter(PlagiarismCheck.id == check_id)
        
        if user_id:
            query = query.filter(PlagiarismCheck.user_id == user_id)
        
        return query.first()
    
    def get_user_plagiarism_checks(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PlagiarismCheck]:
        """Get plagiarism checks for a user."""
        return self.db.query(PlagiarismCheck).filter(
            PlagiarismCheck.user_id == user_id
        ).order_by(PlagiarismCheck.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_user_plagiarism_checks_count(self, user_id: int) -> int:
        """Get count of user's plagiarism checks."""
        return self.db.query(PlagiarismCheck).filter(PlagiarismCheck.user_id == user_id).count()
    
    def get_plagiarism_check_details(self, check_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get detailed plagiarism check results."""
        check = self.get_plagiarism_check(check_id, user_id)
        if not check:
            raise NotFoundException("Plagiarism check not found")
        
        # Get matches with sentence details
        matches = self.db.query(PlagiarismMatch).filter(
            PlagiarismMatch.check_id == check_id
        ).all()
        
        detailed_matches = []
        for match in matches:
            sentence_matches = self.db.query(SentenceMatch).filter(
                SentenceMatch.match_id == match.id
            ).all()
            
            detailed_matches.append({
                'reference_document': {
                    'id': match.reference_document.id,
                    'title': match.reference_document.title
                },
                'similarity_score': match.similarity_score,
                'matched_sentences_count': match.matched_sentences_count,
                'sentence_matches': [
                    {
                        'user_sentence': sm.user_sentence_text,
                        'reference_sentence': sm.reference_sentence_text,
                        'similarity_score': sm.similarity_score,
                        'match_type': sm.match_type
                    }
                    for sm in sentence_matches
                ]
            })
        
        return {
            'check': {
                'id': check.id,
                'total_similarity_score': check.total_similarity_score,
                'check_status': check.check_status,
                'processing_time': check.processing_time,
                'reference_documents_count': check.reference_documents_count,
                'matches_found': check.matches_found,
                'created_at': check.created_at
            },
            'document': {
                'id': check.user_document.id,
                'title': check.user_document.title
            },
            'matches': detailed_matches
        }
