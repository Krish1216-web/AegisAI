import time
from typing import List
from sqlalchemy.orm import Session
from loguru import logger

from app.models.document import DocumentChunk
from app.core.config import settings
from app.core.embeddings.factory import EmbeddingProviderFactory
from app.core.embeddings.exceptions import EmbeddingDimensionMismatch, EmbeddingProviderException

class EmbeddingService:
    @staticmethod
    def _embed_with_retry(provider, texts: List[str], max_retries: int = 3, initial_backoff: float = 1.5) -> List[List[float]]:
        """
        Executes embedding generation with exponential backoff retry for transient API issues.
        """
        for attempt in range(max_retries):
            try:
                return provider.embed_batch(texts)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Embedding batch generation failed after {max_retries} attempts: {e}")
                    raise EmbeddingProviderException(f"Embedding generation failed: {str(e)}")
                
                sleep_time = initial_backoff * (2 ** attempt)
                logger.warning(f"Embedding transient error on attempt {attempt + 1}. Retrying in {sleep_time:.2f}s... Error: {e}")
                time.sleep(sleep_time)
        return []

    @classmethod
    def generate_and_store_embeddings(cls, db: Session, chunks: List[DocumentChunk]) -> None:
        """
        Generates and stores embeddings for the provided list of document chunks.
        Applies batching, idempotency checks, dimension validation, and retry handlers.
        """
        if not chunks:
            return

        provider = EmbeddingProviderFactory.get_provider()
        model_name = settings.EMBEDDING_MODEL
        expected_dim = settings.EMBEDDING_DIMENSION
        batch_size = settings.EMBEDDING_BATCH_SIZE

        # 1. Process idempotency and collect chunks requiring fresh embeddings
        to_embed_chunks = []
        
        for chunk in chunks:
            # Look up an existing processed embedding with same content hash and model
            existing = db.query(DocumentChunk).filter(
                DocumentChunk.content_hash == chunk.content_hash,
                DocumentChunk.embedding_model == model_name,
                DocumentChunk.embedding.is_not(None)
            ).first()

            if existing:
                # Reuse existing embedding vector
                chunk.embedding = existing.embedding
                chunk.embedding_model = model_name
                chunk.embedding_dimension = expected_dim
                logger.info(f"Reused existing embedding for chunk index {chunk.chunk_index} via content hash matching.")
            else:
                to_embed_chunks.append(chunk)

        # 2. Batch-level deduplication to prevent duplicate requests in the same batch
        if not to_embed_chunks:
            db.commit()
            return

        # Map content_hash -> list of chunks
        hash_to_chunks = {}
        for chunk in to_embed_chunks:
            hash_to_chunks.setdefault(chunk.content_hash, []).append(chunk)

        # Build list of unique hashes and texts
        unique_hashes = list(hash_to_chunks.keys())
        unique_texts = [hash_to_chunks[h][0].content for h in unique_hashes]

        unique_vectors = []
        for start_idx in range(0, len(unique_texts), batch_size):
            batch_texts = unique_texts[start_idx : start_idx + batch_size]
            logger.info(f"Generating embeddings for batch of size {len(batch_texts)} unique text inputs.")
            
            # Generate vectors
            batch_vectors = cls._embed_with_retry(provider, batch_texts)
            unique_vectors.extend(batch_vectors)

        # 3. Validate dimensions and save to all matching chunks
        for h, vector in zip(unique_hashes, unique_vectors):
            if len(vector) != expected_dim:
                raise EmbeddingDimensionMismatch(
                    f"Embedding dimension mismatch: expected {expected_dim}, got {len(vector)}."
                )
            
            # Save vector to all chunks with this content_hash
            for chunk in hash_to_chunks[h]:
                chunk.embedding = vector
                chunk.embedding_model = model_name
                chunk.embedding_dimension = expected_dim

        db.commit()
        logger.info(f"Successfully processed and stored embeddings for {len(to_embed_chunks)} chunks.")
