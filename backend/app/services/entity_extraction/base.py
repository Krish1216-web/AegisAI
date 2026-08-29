import uuid
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.services.entity_extraction.models import ExtractedEntity, ExtractedRelationship, ExtractionResult, ExtractionConfig

class BaseEntityExtractor(ABC):
    """
    Abstract base interface for extracting structured entities and relationships from document chunks.
    """
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()

    @abstractmethod
    def extract_entities(
        self,
        text: str,
        document_id: Optional[uuid.UUID] = None,
        chunk_id: Optional[uuid.UUID] = None,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        **kwargs
    ) -> List[ExtractedEntity]:
        """
        Extracts named entities from the supplied chunk text.
        """
        pass

    @abstractmethod
    def extract_relationships(
        self,
        text: str,
        entities: List[ExtractedEntity],
        document_id: Optional[uuid.UUID] = None,
        chunk_id: Optional[uuid.UUID] = None,
        **kwargs
    ) -> List[ExtractedRelationship]:
        """
        Extracts relationship edges between the discovered entities in the chunk text.
        """
        pass

    def extract(
        self,
        text: str,
        document_id: Optional[uuid.UUID] = None,
        chunk_id: Optional[uuid.UUID] = None,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Complete extraction pass returning both entities and relationships with execution metadata.
        """
        start_time = time.perf_counter()
        if not text or not text.strip():
            return ExtractionResult(
                entities=[],
                relationships=[],
                document_id=document_id,
                chunk_id=chunk_id,
                extraction_time=0.0,
                provider=self.config.provider
            )

        entities = self.extract_entities(
            text=text,
            document_id=document_id,
            chunk_id=chunk_id,
            page_number=page_number,
            section_title=section_title,
            **kwargs
        )

        # Enforce max entities limit
        entities = entities[:self.config.max_entities_per_chunk]

        relationships = self.extract_relationships(
            text=text,
            entities=entities,
            document_id=document_id,
            chunk_id=chunk_id,
            **kwargs
        )

        # Enforce max relationships limit
        relationships = relationships[:self.config.max_relationships_per_chunk]

        elapsed = time.perf_counter() - start_time
        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            document_id=document_id,
            chunk_id=chunk_id,
            extraction_time=round(elapsed, 4),
            provider=self.config.provider
        )
