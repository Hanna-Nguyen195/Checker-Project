from typing import Optional, List, BinaryIO
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog
from datetime import datetime

from app.models.document import ReferenceDocument, PlagiarismDocument, PendingReferenceDocument
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
    
    # New methods for the three-database structure
    
    def upload_plagiarism_document(
        self,
        user_id: int,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        title: Optional[str] = None
    ) -> PlagiarismDocument:
        """Upload a document for plagiarism checking."""
        try:
            # Upload file to storage first
            object_id = self.storage_service.upload_file(
                file_data=file_data,
                original_filename=filename,
                content_type=content_type,
                file_size=file_size
            )
            
            # Create database record only after successful storage upload
            document = PlagiarismDocument(
                user_id=user_id,
                title=title or filename,
                object_id=object_id,
                content_type=content_type,
                document_metadata={}
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(
                "Plagiarism document uploaded",
                document_id=document.id,
                user_id=user_id,
                filename=filename
            )
            
            return document
            
        except Exception as e:
            # Ensure database session is clean on any failure
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.warning("Failed to rollback database session", error=str(rollback_error))
            
            logger.error("Failed to upload plagiarism document", error=str(e), exc_info=True)
            raise
    
    def get_plagiarism_document(self, document_id: int, user_id: Optional[int] = None) -> Optional[PlagiarismDocument]:
        """Get plagiarism document by ID."""
        query = self.db.query(PlagiarismDocument).filter(PlagiarismDocument.id == document_id)
        
        if user_id:
            query = query.filter(PlagiarismDocument.user_id == user_id)
        
        return query.first()
    
    def get_plagiarism_documents(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PlagiarismDocument]:
        """Get plagiarism documents for a user."""
        return self.db.query(PlagiarismDocument)\
            .filter(PlagiarismDocument.user_id == user_id)\
            .order_by(PlagiarismDocument.created_at.desc())\
            .offset(skip).limit(limit).all()
    
    def get_plagiarism_documents_count(self, user_id: int) -> int:
        """Get count of plagiarism documents for a user."""
        return self.db.query(PlagiarismDocument).filter(PlagiarismDocument.user_id == user_id).count()
    
    def download_plagiarism_document(self, document_id: int, user_id: int) -> bytes:
        """Download plagiarism document content."""
        document = self.get_plagiarism_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document not found")
        
        return self.storage_service.download_file(document.object_id)
    
    def delete_plagiarism_document(self, document_id: int, user_id: int) -> bool:
        """Delete plagiarism document."""
        document = self.get_plagiarism_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document not found")
        
        # Delete from storage
        self.storage_service.delete_file(document.object_id)
        
        # Delete from database
        self.db.delete(document)
        self.db.commit()
        
        logger.info("Plagiarism document deleted", document_id=document_id, user_id=user_id)
        return True
    
    def submit_pending_reference_document(
        self,
        user_id: int,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        title: str
    ) -> PendingReferenceDocument:
        """Submit a document for consideration as a reference document."""
        try:
            # Upload file to storage first
            object_id = self.storage_service.upload_file(
                file_data=file_data,
                original_filename=filename,
                content_type=content_type,
                file_size=file_size
            )
            
            # Create database record only after successful storage upload
            document = PendingReferenceDocument(
                user_id=user_id,
                title=title or filename,
                object_id=object_id,
                content_type=content_type,
                status="pending",
                document_metadata={}
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(
                "Pending reference document submitted",
                document_id=document.id,
                user_id=user_id,
                filename=filename
            )
            
            return document
            
        except Exception as e:
            # Ensure database session is clean on any failure
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.warning("Failed to rollback database session", error=str(rollback_error))
            
            logger.error("Failed to submit pending reference document", error=str(e), exc_info=True)
            raise
    
    def get_pending_reference_document(self, document_id: int) -> Optional[PendingReferenceDocument]:
        """Get pending reference document by ID."""
        return self.db.query(PendingReferenceDocument).filter(PendingReferenceDocument.id == document_id).first()
    
    def get_pending_reference_documents(self, skip: int = 0, limit: int = 100) -> List[PendingReferenceDocument]:
        """Get pending reference documents for admin review."""
        return self.db.query(PendingReferenceDocument).filter(
            PendingReferenceDocument.status == "pending"
        ).order_by(PendingReferenceDocument.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_pending_reference_documents_count(self) -> int:
        """Get count of pending reference documents."""
        return self.db.query(PendingReferenceDocument).filter(PendingReferenceDocument.status == "pending").count()
    
    def approve_pending_reference_document(
        self, 
        document_id: int, 
        admin_id: int, 
        admin_comment: Optional[str] = None
    ) -> ReferenceDocument:
        """Approve pending reference document and create a reference document."""
        document = self.get_pending_reference_document(document_id)
        if not document:
            raise NotFoundException("Pending reference document not found")
        
        if document.status != "pending":
            raise ValidationException("Document is not in pending status")
        
        # Update document status
        document.status = "approved"
        document.approved_by = admin_id
        document.approved_at = datetime.utcnow()
        document.admin_comment = admin_comment
        
        # Create reference document
        reference_doc = ReferenceDocument(
            title=document.title,
            object_id=document.object_id,
            content_type=document.content_type,
            created_by=admin_id,
            source_pending_document_id=document.id,
            document_metadata=document.document_metadata
        )
        
        self.db.add(reference_doc)
        self.db.commit()
        self.db.refresh(document)
        self.db.refresh(reference_doc)
        
        logger.info("Pending reference document approved", document_id=document_id, admin_id=admin_id)
        return reference_doc
    
    def reject_pending_reference_document(
        self, 
        document_id: int, 
        admin_id: int, 
        admin_comment: str
    ) -> PendingReferenceDocument:
        """Reject pending reference document."""
        document = self.get_pending_reference_document(document_id)
        if not document:
            raise NotFoundException("Pending reference document not found")
        
        if document.status != "pending":
            raise ValidationException("Document is not in pending status")
        
        # Update document status
        document.status = "rejected"
        document.approved_by = admin_id
        document.approved_at = datetime.utcnow()
        document.admin_comment = admin_comment
        
        self.db.commit()
        self.db.refresh(document)
        
        logger.info("Pending reference document rejected", document_id=document_id, admin_id=admin_id)
        return document
    
    # Legacy UserDocument methods have been removed
    
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
                document_metadata=metadata,
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
        """Delete reference document and handle related plagiarism matches."""
        document = self.get_reference_document(document_id)
        if not document:
            raise NotFoundException("Reference document not found")
        
        try:
            # First, handle related plagiarism_matches
            from app.models.plagiarism import PlagiarismMatch
            
            # Find all plagiarism matches related to this document
            related_matches = self.db.query(PlagiarismMatch).filter(
                PlagiarismMatch.reference_document_id == document_id
            ).all()
            
            if related_matches:
                logger.info(f"Found {len(related_matches)} plagiarism matches to delete for document {document_id}")
                
                # Delete all related plagiarism matches
                for match in related_matches:
                    self.db.delete(match)
                
                # Commit the deletion of plagiarism matches
                self.db.flush()
                logger.info(f"Deleted {len(related_matches)} plagiarism matches for document {document_id}")
            
            # Delete from storage
            try:
                self.storage_service.delete_file(document.object_id)
                logger.info(f"Deleted file {document.object_id} from storage")
            except Exception as e:
                logger.warning(f"Failed to delete file from storage: {str(e)}")
                # Continue with database deletion even if storage deletion fails
            
            # Delete the document from database
            self.db.delete(document)
            self.db.commit()
            
            logger.info("Reference document deleted successfully", document_id=document_id)
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete reference document: {str(e)}")
            raise
        
    def synchronize_storage_with_database(self, document_type: str = "all") -> dict:
        """Synchronize MinIO storage with PostgreSQL database records.
        
        This method checks if files in the database exist in MinIO storage.
        If files are missing in MinIO but exist in the database, it marks them as unavailable.
        
        Args:
            document_type: Type of documents to check ('user', 'reference', or 'all')
            
        Returns:
            Dictionary with synchronization results
        """
        results = {
            "checked": 0,
            "missing_in_storage": 0,
            "updated_records": 0,
            "errors": 0,
            "missing_documents": []
        }
        
        try:
            # Check if storage service is available
            if not self.storage_service.is_connected:
                logger.warning("Storage service is not available for synchronization")
                return {
                    "error": "Storage service is not available",
                    "status": "failed"
                }
            
            # Force a connection test to ensure MinIO is accessible
            try:
                # Check if client is initialized
                if not self.storage_service.client:
                    logger.error("MinIO client is not initialized")
                    return {
                        "error": "MinIO client is not initialized",
                        "status": "failed"
                    }
                
                # Log MinIO configuration
                logger.info(
                    "MinIO configuration", 
                    endpoint=getattr(self.storage_service, 'endpoint', None),
                    bucket=self.storage_service.bucket_name,
                    is_connected=self.storage_service.is_connected
                )
                
                # Try to list buckets to verify connection
                buckets = list(self.storage_service.client.list_buckets())
                logger.info(f"MinIO connection verified successfully. Found {len(buckets)} buckets")
                
                # Try to list objects in the bucket
                try:
                    objects = list(self.storage_service.client.list_objects(self.storage_service.bucket_name, recursive=True))
                    logger.info(f"Found {len(objects)} objects in bucket {self.storage_service.bucket_name}")
                    
                    # Log the first few objects for debugging
                    if objects:
                        logger.info(f"Sample objects: {[obj.object_name for obj in objects[:5]]}")
                    else:
                        logger.warning(f"No objects found in bucket {self.storage_service.bucket_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to list objects in bucket: {str(e)}")
            except Exception as e:
                logger.error("MinIO connection test failed", error=str(e))
                return {
                    "error": f"MinIO connection test failed: {str(e)}",
                    "status": "failed"
                }
            
            # Legacy user documents processing has been removed
            
            # Process reference documents
            if document_type in ["all", "reference"]:
                ref_docs = self.db.query(ReferenceDocument).all()
                logger.info(f"Checking {len(ref_docs)} reference documents")
                
                for doc in ref_docs:
                    results["checked"] += 1
                    try:
                        # Check if file exists in storage
                        exists = False
                        try:
                            # Use stat_object instead of file_exists for more reliable check
                            self.storage_service.client.stat_object(
                                self.storage_service.bucket_name, 
                                doc.object_id
                            )
                            exists = True
                            logger.info(f"Reference file exists in MinIO: {doc.object_id} (ID: {doc.id})")
                            
                            # Explicitly mark as available
                            if doc.document_metadata is None:
                                doc.document_metadata = {}
                            elif not isinstance(doc.document_metadata, dict):
                                doc.document_metadata = {}
                                
                            doc.document_metadata["storage_status"] = "available"
                            doc.document_metadata["last_checked"] = str(datetime.utcnow())
                        except Exception as file_error:
                            exists = False
                            logger.warning(f"Reference file missing in MinIO: {doc.object_id} (ID: {doc.id}), Error: {str(file_error)}")
                            
                            # Double-check with list_objects if stat_object fails
                            try:
                                objects = list(self.storage_service.client.list_objects(
                                    self.storage_service.bucket_name,
                                    prefix=doc.object_id,
                                    recursive=False
                                ))
                                if objects:
                                    exists = True
                                    logger.info(f"Reference file found via list_objects: {doc.object_id} (ID: {doc.id})")
                                    
                                    # Explicitly mark as available
                                    if doc.document_metadata is None:
                                        doc.document_metadata = {}
                                    elif not isinstance(doc.document_metadata, dict):
                                        doc.document_metadata = {}
                                        
                                    doc.document_metadata["storage_status"] = "available"
                                    doc.document_metadata["last_checked"] = str(datetime.utcnow())
                            except Exception as list_error:
                                logger.error(f"Error checking reference file with list_objects: {str(list_error)}")
                                # Keep exists = False
                        
                        if not exists:
                            logger.warning(
                                "Reference document file missing in storage",
                                document_id=doc.id,
                                object_id=doc.object_id
                            )
                            # Add a document_metadata field if it doesn't exist
                            if doc.document_metadata is None:
                                doc.document_metadata = {}
                            elif not isinstance(doc.document_metadata, dict):
                                # Convert to dict if it's not already
                                try:
                                    doc.document_metadata = {}
                                except Exception as e:
                                    logger.error(f"Failed to initialize document_metadata: {e}")
                                    doc.document_metadata = {}
                            
                            # Update metadata to indicate storage issue
                            doc.document_metadata["storage_status"] = "missing"
                            doc.document_metadata["last_checked"] = str(datetime.utcnow())
                            results["missing_in_storage"] += 1
                            results["updated_records"] += 1
                            results["missing_documents"].append({
                                "id": doc.id,
                                "title": doc.title,
                                "type": "reference"
                            })
                    except Exception as e:
                        logger.error(
                            "Error checking reference document",
                            document_id=doc.id,
                            error=str(e)
                        )
                        results["errors"] += 1
            
            # Always commit changes, even if just updating storage_status to available
            self.db.commit()
            logger.info(
                "Storage synchronization completed",
                checked=results["checked"],
                updated_records=results["updated_records"],
                missing_files=results["missing_in_storage"]
            )
            
            return {
                **results,
                "status": "completed"
            }
                
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to synchronize storage with database", error=str(e))
            return {
                "error": str(e),
                "status": "failed"
            }
