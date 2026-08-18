import uuid
import datetime
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, status, File, UploadFile, Query, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_db
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.document import Document, DocumentChunk
from app.schemas.document import (
    DocumentUploadResponse, 
    DocumentListItemResponse, 
    DocumentDetailsResponse,
    DocumentStatusResponse,
    DocumentChunkResponse
)
from app.services.document_storage import DocumentStorage
from app.services.file_validator import FileValidator
from app.services.document_processing import DocumentProcessingService
from app.core.config import settings
from app.core.document_exceptions import (
    DocumentNotFound, 
    DocumentPermissionDenied, 
    DuplicateDocument
)

router = APIRouter(prefix="/documents", tags=["Document Hub"])

# Helper to resolve workspace ID for current user
def resolve_workspace_id(current_user: User, db: Session) -> uuid.UUID:
    ws_id_str = current_user.settings.get("default_workspace_id") if current_user.settings else None
    if ws_id_str:
        try:
            return uuid.UUID(ws_id_str)
        except ValueError:
            pass
            
    # Fallback to first membership
    member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
    if not member:
        raise DocumentPermissionDenied("User is not associated with any active workspace.")
    return member.workspace_id

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handles secure, validated document uploads, storing the file on disk
    and creating a record in the database.
    """
    # 1. Read file contents and validate size
    content = await file.read()
    FileValidator.validate_size(len(content))
    
    # 2. Validate MIME type, extension, and signature
    ext = FileValidator.validate_format_and_signature(file.filename, file.content_type, content)
    base_mime = file.content_type.split(";")[0].strip().lower()

    # 3. Resolve tenant workspace boundaries
    workspace_id = resolve_workspace_id(current_user, db)
    
    # Verify membership
    get_workspace_member(workspace_id, current_user, db)

    # 4. Storage & Checksum validation
    storage_service = DocumentStorage()
    checksum = storage_service.calculate_checksum(content)
    
    # Detect duplicates within the same user + workspace
    duplicate = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.workspace_id == workspace_id,
        Document.checksum == checksum,
        Document.status != "DELETED"
    ).first()
    
    if duplicate:
        raise DuplicateDocument("A file with identical checksum has already been uploaded in this workspace.")

    # 5. Extract optional metadata (WAV / PDF page counts)
    page_count = None
    duration = None
    
    if ext == ".pdf":
        import re
        try:
            matches = re.findall(b"/Type\s*/Pages\s*/Count\s*(\d+)", content)
            if matches:
                page_count = int(matches[-1])
            else:
                matches = re.findall(b"/Count\s*(\d+)", content)
                if matches:
                    page_count = int(matches[-1])
        except Exception:
            pass
            
    elif ext == ".wav":
        import wave
        try:
            with wave.open(io.BytesIO(content), 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                duration = frames / float(rate)
        except Exception:
            pass

    # 6. Save file and database entity record
    doc_id = uuid.uuid4()
    storage_path = storage_service.store_file(workspace_id, doc_id, content)
    
    db_doc = Document(
        id=doc_id,
        user_id=current_user.id,
        workspace_id=workspace_id,
        filename=file.filename,
        original_filename=file.filename,
        mime_type=base_mime,
        file_extension=ext,
        file_size=len(content),
        checksum=checksum,
        storage_path=storage_path,
        status="UPLOADED",
        page_count=page_count,
        duration_seconds=duration,
        meta_data={}
    )
    
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    logger.info(f"Document registered in DB: {db_doc.id}")
    return db_doc

@router.get("", response_model=List[DocumentListItemResponse])
def list_documents(
    status: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists documents associated with the authenticated user's workspace,
    supporting status filtering and pagination.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    get_workspace_member(workspace_id, current_user, db)
    
    query = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.workspace_id == workspace_id,
        Document.status != "DELETED"
    )
    
    if status:
        query = query.filter(Document.status == status.upper())
        
    return query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{document_id}", response_model=DocumentDetailsResponse)
def get_document_details(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves metadata details of a specific document, enforcing tenant scope.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()
    
    if not doc:
        raise DocumentNotFound("Document not found.")
        
    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")
        
    get_workspace_member(doc.workspace_id, current_user, db)
    
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft-deletes database record status and completely removes the physical file.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()
    
    if not doc:
        raise DocumentNotFound("Document not found.")
        
    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")
        
    get_workspace_member(doc.workspace_id, current_user, db)
    
    # Delete file from storage
    storage_service = DocumentStorage()
    storage_service.delete_file(doc.storage_path)
    
    # Mark database entry deleted
    doc.status = "DELETED"
    doc.storage_path = ""  # Prevent download attempts
    db.commit()
    
    logger.info(f"Document marked DELETED in database: {document_id}")

@router.get("/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Safely streams files from local storage using verified scopes.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()
    
    if not doc:
        raise DocumentNotFound("Document not found.")
        
    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")
        
    get_workspace_member(doc.workspace_id, current_user, db)
    
    storage_service = DocumentStorage()
    file_bytes = storage_service.get_file(doc.storage_path)
    
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"'
        }
    )

@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def queue_process_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers background extraction and text normalization for the specified document.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()

    if not doc:
        raise DocumentNotFound("Document not found.")

    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")

    get_workspace_member(doc.workspace_id, current_user, db)

    # Prevent concurrent or duplicate processing conflicts
    if doc.status == "PROCESSING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is currently being processed."
        )

    # Queue processing tasks in the background safely
    background_tasks.add_task(DocumentProcessingService.process_document, db, doc.id)

    return {
        "document_id": str(doc.id),
        "status": "PROCESSING"
    }

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_processing_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the current extraction status, chunk count, and embedding progress metrics.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()

    if not doc:
        raise DocumentNotFound("Document not found.")

    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")

    get_workspace_member(doc.workspace_id, current_user, db)

    # Dynamically compute chunking metrics
    total = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    processed = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id, 
        DocumentChunk.embedding != None
    ).count()
    progress = (processed / total * 100.0) if total > 0 else 0.0

    return {
        "id": doc.id,
        "status": doc.status,
        "processing_error": doc.processing_error,
        "page_count": doc.page_count,
        "extracted_text_length": doc.extracted_text_length,
        "updated_at": doc.updated_at,
        "total_chunks": total,
        "processed_chunks": processed,
        "failed_chunks": 0,
        "embedding_model": settings.EMBEDDING_MODEL,
        "progress": round(progress, 2)
    }

@router.post("/{document_id}/chunk", status_code=status.HTTP_202_ACCEPTED)
def trigger_document_chunking(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers the chunking and embedding generation pipeline for a document in the background.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()

    if not doc:
        raise DocumentNotFound("Document not found.")

    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")

    get_workspace_member(doc.workspace_id, current_user, db)

    if doc.status in ["PROCESSING", "CHUNKING", "EMBEDDING"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document processing is already active (status: {doc.status})."
        )

    # Trigger core process pipeline containing chunking & embeddings steps
    background_tasks.add_task(DocumentProcessingService.process_document, db, doc.id)

    return {
        "document_id": str(doc.id),
        "status": "PROCESSING"
    }

@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def list_document_chunks(
    document_id: uuid.UUID,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists the chunks of a document with pagination. Embedding vectors are omitted in the response.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()

    if not doc:
        raise DocumentNotFound("Document not found.")

    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")

    get_workspace_member(doc.workspace_id, current_user, db)

    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id
    ).order_by(DocumentChunk.chunk_index.asc()).limit(limit).offset(offset).all()

    return chunks

@router.get("/{document_id}/chunks/{chunk_id}", response_model=DocumentChunkResponse)
def get_document_chunk(
    document_id: uuid.UUID,
    chunk_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed metadata for a single specific chunk.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()

    if not doc:
        raise DocumentNotFound("Document not found.")

    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")

    get_workspace_member(doc.workspace_id, current_user, db)

    chunk = db.query(DocumentChunk).filter(
        DocumentChunk.id == chunk_id,
        DocumentChunk.document_id == doc.id
    ).first()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document chunk not found."
        )

    return chunk

@router.post("/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clears all existing chunks and embeddings, then queues a full re-indexing of the document.
    """
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.status != "DELETED"
    ).first()

    if not doc:
        raise DocumentNotFound("Document not found.")

    if doc.user_id != current_user.id:
        raise DocumentPermissionDenied("Access to this document is denied.")

    get_workspace_member(doc.workspace_id, current_user, db)

    if doc.status in ["PROCESSING", "CHUNKING", "EMBEDDING"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reindex: processing is already active (status: {doc.status})."
        )

    # Queue full document processing background task
    background_tasks.add_task(DocumentProcessingService.process_document, db, doc.id)

    return {
        "document_id": str(doc.id),
        "status": "PROCESSING"
    }


