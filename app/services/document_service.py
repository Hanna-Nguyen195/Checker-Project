from typing import Optional, List, BinaryIO
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from app.models.document import UserDocument, ReferenceDocument
from app.models.user import User
from app.services.storage_service import StorageService
from app.core.exceptions import NotFoundException, AuthorizationException, ValidationException
from app.utils.validators import validate_file_upload

logger = structlog.get_logger(__name__)


class DocumentService:
    """Service for document management operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = StorageService()
    
    def upload_user_document(
        self,
        user_id: int,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        title: Optional[str] = None
    ) -> UserDocument:
        """Upload a user document."""
        try:
            # Upload file to storage
            object_id = self.storage_service.upload_file(
                file_data=file_data,
                original_filename=filename,
                content_type=content_type,
                file_size=file_size
            )
            
            # Create database record
            document = UserDocument(
                user_id=user_id,
                title=title or filename,
                object_id=object_id,
                content_type=content_type,
                status="pending"
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(
                "User document uploaded",
                document_id=document.id,
                user_id=user_id,
                filename=filename
            )
            
            return document
            
        except Exception as e:
            logger.error("Failed to upload user document", error=str(e))
            raise
    
    def get_user_document(self, document_id: int, user_id: Optional[int] = None) -> Optional[UserDocument]:
        """Get user document by ID."""
        query = self.db.query(UserDocument).filter(UserDocument.id == document_id)
        
        if user_id:
            query = query.filter(UserDocument.user_id == user_id)
        
        return query.first()
    
    def get_user_documents(
        self,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserDocument]:
        """Get user documents with optional filtering."""
        query = self.db.query(UserDocument).filter(UserDocument.user_id == user_id)
        
        if status:
            query = query.filter(UserDocument.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    def get_user_documents_count(self, user_id: int, status: Optional[str] = None) -> int:
        """Get count of user documents."""
        query = self.db.query(UserDocument).filter(UserDocument.user_id == user_id)
        
        if status:
            query = query.filter(UserDocument.status == status)
        
        return query.count()
    
    def download_user_document(self, document_id: int, user_id: int) -> bytes:
        """Download user document content."""
        document = self.get_user_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document not found")
        
        return self.storage_service.download_file(document.object_id)
    
    def delete_user_document(self, document_id: int, user_id: int) -> bool:
        """Delete user document."""
        document = self.get_user_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document not found")
        
        # Delete from storage
        self.storage_service.delete_file(document.object_id)
        
        # Delete from database
        self.db.delete(document)
        self.db.commit()
        
        logger.info("User document deleted", document_id=document_id, user_id=user_id)
        return True
    
    def approve_user_document(self, document_id: int, admin_id: int, comment: Optional[str] = None) -> UserDocument:
        """Approve user document for inclusion in reference database."""
        document = self.db.query(UserDocument).filter(UserDocument.id == document_id).first()
        if not document:
            raise NotFoundException("Document not found")
        
        if document.status != "pending":
            raise ValidationException("Document is not in pending status")
        
        # Update document status
        document.status = "approved"
        document.approved_by = admin_id
        document.approved_at = None  # Will be set by database default
        document.comment = comment
        
        # Create reference document
        reference_doc = ReferenceDocument(
            title=document.title,
            object_id=document.object_id,
            content_type=document.content_type,
            created_by=admin_id,
            source_user_document_id=document.id
        )
        
        self.db.add(reference_doc)
        self.db.commit()
        self.db.refresh(document)
        
        logger.info("User document approved", document_id=document_id, admin_id=admin_id)
        return document
    
    def reject_user_document(self, document_id: int, admin_id: int, comment: str) -> UserDocument:
        """Reject user document."""
        document = self.db.query(UserDocument).filter(UserDocument.id == document_id).first()
        if not document:
            raise NotFoundException("Document not found")
        
        if document.status != "pending":
            raise ValidationException("Document is not in pending status")
        
        # Update document status
        document.status = "rejected"
        document.approved_by = admin_id
        document.approved_at = None  # Will be set by database default
        document.comment = comment
        
        self.db.commit()
        self.db.refresh(document)
        
        logger.info("User document rejected", document_id=document_id, admin_id=admin_id)
        return document
    
    def get_pending_documents(self, skip: int = 0, limit: int = 100) -> List[UserDocument]:
        """Get pending user documents for admin review."""
        return self.db.query(UserDocument).filter(
            UserDocument.status == "pending"
        ).offset(skip).limit(limit).all()
    
    def get_pending_documents_count(self) -> int:
        """Get count of pending documents."""
        return self.db.query(UserDocument).filter(UserDocument.status == "pending").count()
    
    def create_reference_document(
        self,
        admin_id: int,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        title: str,
        metadata: Optional[dict] = None
    ) -> ReferenceDocument:
        """Create a reference document directly."""
        try:
            # Upload file to storage
            object_id = self.storage_service.upload_file(
                file_data=file_data,
                original_filename=filename,
                content_type=content_type,
                file_size=file_size
            )
            
            # Create database record
            document = ReferenceDocument(
                title=title,
                object_id=object_id,
                content_type=content_type,
                metadata=metadata,
                created_by=admin_id
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(
                "Reference document created",
                document_id=document.id,
                admin_id=admin_id,
                title=title
            )
            
            return document
            
        except Exception as e:
            logger.error("Failed to create reference document", error=str(e))
            raise
    
    def get_reference_documents(self, skip: int = 0, limit: int = 100) -> List[ReferenceDocument]:
        """Get reference documents."""
        return self.db.query(ReferenceDocument).offset(skip).limit(limit).all()
    
    def get_reference_documents_count(self) -> int:
        """Get count of reference documents."""
        return self.db.query(ReferenceDocument).count()
    
    def get_reference_document(self, document_id: int) -> Optional[ReferenceDocument]:
        """Get reference document by ID."""
        return self.db.query(ReferenceDocument).filter(ReferenceDocument.id == document_id).first()
    
    def delete_reference_document(self, document_id: int) -> bool:
        """Delete reference document."""
        document = self.get_reference_document(document_id)
        if not document:
            raise NotFoundException("Reference document not found")
        
        # Delete from storage
        self.storage_service.delete_file(document.object_id)
        
        # Delete from database
        self.db.delete(document)
        self.db.commit()
        
        logger.info("Reference document deleted", document_id=document_id)
        return True
