import os
import uuid
import datetime
import tempfile
import hashlib
from sqlalchemy.orm import Session
from loguru import logger

from app.models.document import Document, DocumentChunk
from app.services.document_storage import DocumentStorage
from app.services.extractors.factory import DocumentExtractorFactory
from app.services.text_normalizer import normalize_text
from app.services.document_security import scan_document_text
from app.services.chunking.service import DocumentChunkerService
from app.services.embedding_service import EmbeddingService
from app.core.config import settings
from app.core.document_exceptions import DocumentNotFound, InvalidFile

class DocumentProcessingService:
    @staticmethod
    def process_document(db: Session, document_id: uuid.UUID) -> None:
        """
        Processes a document in a background worker context.
        Flow:
        1. Status = PROCESSING -> Extract text -> Normalize text -> Scan security.
        2. Status = CHUNKING -> Split into chunks -> Save to DB.
        3. Status = EMBEDDING -> Generate and store vector embeddings.
        4. Status = READY on success, FAILED on exception.
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
        meta = dict(doc.meta_data)
        meta["processing_started_at"] = datetime.datetime.utcnow().isoformat()
        doc.meta_data = meta
        db.commit()

        temp_file_path = None
        try:
            # 2. Retrieve file bytes from storage
            storage = DocumentStorage()
            file_bytes = storage.get_file(doc.storage_path)

            # 3. Write to a temporary file
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
            if extracted_doc.page_count:
                doc.page_count = extracted_doc.page_count
                
            ext_meta = extracted_doc.metadata or {}
            if "duration" in ext_meta and ext_meta["duration"] is not None:
                doc.duration_seconds = ext_meta["duration"]
            if "width" in ext_meta and ext_meta["width"] is not None:
                doc.width = ext_meta["width"]
            if "height" in ext_meta and ext_meta["height"] is not None:
                doc.height = ext_meta["height"]

            meta = dict(doc.meta_data)
            meta["word_count"] = extracted_doc.word_count
            meta["character_count"] = extracted_doc.character_count
            meta["security_scan"] = security_info
            meta["title"] = ext_meta.get("title", "") or ext_meta.get("Title", "") or ""
            meta["author"] = ext_meta.get("author", "") or ext_meta.get("Author", "") or ""
            meta["ocr_available"] = ext_meta.get("ocr_available", False)
            meta["sheets"] = ext_meta.get("sheet_names", [])
            doc.meta_data = meta
            db.commit()

            # 8. STEP: CHUNKING
            doc.status = "CHUNKING"
            db.commit()
            
            # Wipe existing chunks for re-indexing idempotency
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            db.commit()

            chunk_results = DocumentChunkerService.chunk_document(extracted_doc)
            db_chunks = []

            for cr in chunk_results:
                chash = hashlib.sha256(cr.content.encode('utf-8')).hexdigest()
                db_chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    user_id=doc.user_id,
                    workspace_id=doc.workspace_id,
                    chunk_index=cr.chunk_index,
                    content=cr.content,
                    content_hash=chash,
                    token_count=cr.token_count,
                    character_count=cr.character_count,
                    page_number=cr.page_number,
                    section_title=cr.section_title,
                    start_offset=cr.start_offset,
                    end_offset=cr.end_offset,
                    embedding_model=settings.EMBEDDING_MODEL,
                    embedding_dimension=settings.EMBEDDING_DIMENSION,
                    meta_data={
                        "document_id": str(doc.id),
                        "page": cr.page_number,
                        "section": cr.section_title,
                        "chunk_index": cr.chunk_index,
                        "source_type": doc.file_extension.lstrip("."),
                        "document_name": doc.original_filename,
                        "workspace_id": str(doc.workspace_id)
                    }
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)
            
            db.commit()

            # 9. STEP: EMBEDDING
            doc.status = "EMBEDDING"
            db.commit()

            # Generate and store embeddings using batching service
            EmbeddingService.generate_and_store_embeddings(db, db_chunks)

            # 10. Finalize processing pipeline: Document READY
            doc.status = "READY"
            meta = dict(doc.meta_data)
            meta["processing_completed_at"] = datetime.datetime.utcnow().isoformat()
            doc.meta_data = meta
            doc.processing_error = None
            db.commit()

            logger.info(f"Document {document_id} processed successfully: status READY, total chunks: {len(db_chunks)}")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            db.rollback()
            
            # Re-fetch document inside error transaction scope
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "FAILED"
                safe_err_msg = str(e)
                if "traceback" in safe_err_msg or "password" in safe_err_msg or "db" in safe_err_msg:
                    safe_err_msg = "An internal parser or system error occurred during chunking/embedding."
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
