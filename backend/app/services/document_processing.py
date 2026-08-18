import os
import uuid
import datetime
import tempfile
from sqlalchemy.orm import Session
from loguru import logger

from app.models.document import Document
from app.services.document_storage import DocumentStorage
from app.services.extractors.factory import DocumentExtractorFactory
from app.services.text_normalizer import normalize_text
from app.services.document_security import scan_document_text
from app.core.document_exceptions import DocumentNotFound, InvalidFile

class DocumentProcessingService:
    @staticmethod
    def process_document(db: Session, document_id: uuid.UUID) -> None:
        """
        Processes a document in a background worker context.
        Updates status to PROCESSING, extracts content, normalizes text, scans for security,
        and saves outcomes back to the database.
        """
        doc = db.query(Document).filter(
            Document.id == document_id, 
            Document.status != "DELETED"
        ).first()

        if not doc:
            logger.error(f"Processing failed: Document {document_id} not found.")
            return

        # 1. Update status to PROCESSING
        doc.status = "PROCESSING"
        if not doc.meta_data:
            doc.meta_data = {}
        # Make a copy of metadata to satisfy SQLAlchemy mutate tracking
        meta = dict(doc.meta_data)
        meta["processing_started_at"] = datetime.datetime.utcnow().isoformat()
        doc.meta_data = meta
        db.commit()

        temp_file_path = None
        try:
            # 2. Retrieve file bytes from storage
            storage = DocumentStorage()
            file_bytes = storage.get_file(doc.storage_path)

            # 3. Write to a temporary file for local extractor access
            # Retain extension so loaders can infer type safely if needed
            with tempfile.NamedTemporaryFile(delete=False, suffix=doc.file_extension) as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name

            # 4. Resolve extractor and extract data
            extractor = DocumentExtractorFactory.get_extractor(doc.mime_type, doc.file_extension)
            extracted_doc = extractor.extract(temp_file_path)

            # 5. Normalize text content
            normalized_text = normalize_text(extracted_doc.text)

            # 6. Prompt Injection / Security scanning
            security_info = scan_document_text(normalized_text)

            # 7. Update document metrics & metadata
            doc.extracted_text_length = len(normalized_text)
            
            # Map optional extractor page/media dimensions
            if extracted_doc.page_count:
                doc.page_count = extracted_doc.page_count
                
            # If extractor returned metadata specific mappings
            ext_meta = extracted_doc.metadata or {}
            
            # Check for media duration details
            if "duration" in ext_meta and ext_meta["duration"] is not None:
                doc.duration_seconds = ext_meta["duration"]
            if "width" in ext_meta and ext_meta["width"] is not None:
                doc.width = ext_meta["width"]
            if "height" in ext_meta and ext_meta["height"] is not None:
                doc.height = ext_meta["height"]

            # Extensible JSON metadata payload updates
            meta = dict(doc.meta_data)
            meta["processing_completed_at"] = datetime.datetime.utcnow().isoformat()
            meta["word_count"] = extracted_doc.word_count
            meta["character_count"] = extracted_doc.character_count
            meta["security_scan"] = security_info
            
            # Save any other properties extracted
            meta["title"] = ext_meta.get("title", "") or ext_meta.get("Title", "") or ""
            meta["author"] = ext_meta.get("author", "") or ext_meta.get("Author", "") or ""
            meta["ocr_available"] = ext_meta.get("ocr_available", False)
            meta["sheets"] = ext_meta.get("sheet_names", [])
            
            doc.meta_data = meta
            doc.status = "PROCESSED"
            doc.processing_error = None
            db.commit()

            # Store the extracted text into DocumentChunks for future RAG (mock step)
            # In Phase 4.2 we do NOT implement chunks/embeddings yet, but we update status to PROCESSED.
            logger.info(f"Document {document_id} processed successfully. Extracted text length: {len(normalized_text)}")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            db.rollback()
            
            # Re-fetch document inside error transaction scope
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "FAILED"
                # Keep error message safe and free of server secrets / internal traces
                safe_err_msg = str(e)
                if "traceback" in safe_err_msg or "password" in safe_err_msg or "db" in safe_err_msg:
                    safe_err_msg = "An internal parser or system error occurred during text extraction."
                doc.processing_error = safe_err_msg
                
                meta = dict(doc.meta_data or {})
                meta["processing_failed_at"] = datetime.datetime.utcnow().isoformat()
                doc.meta_data = meta
                db.commit()

        finally:
            # Cleanup temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_file_path}: {e}")
