import re
import uuid
from typing import List, Optional, Set, Dict, Any, Tuple

from app.models.knowledge_graph import NodeType, RelationshipType
from app.services.entity_extraction.base import BaseEntityExtractor
from app.services.entity_extraction.models import ExtractedEntity, ExtractedRelationship, ExtractionConfig
from app.services.entity_extraction.normalizer import EntityNormalizer, KNOWN_ALIASES

# Tech & Skill Keywords regex
TECH_PATTERNS = [
    r"\b(FastAPI|React(?:\.js)?|PostgreSQL|Postgres|SQLite(?:3)?|Redis|Docker|Kubernetes|k8s|ChromaDB|Qdrant|LangGraph|LangChain|SQLAlchemy|Pydantic(?: v2)?|Python(?:3)?|TypeScript|JavaScript|Node(?:\.js)?|GraphQL|PyTorch|TensorFlow|Tavily|OpenAI|Anthropic|DeepMind|Gemini|AegisAI)\b",
    r"\b([A-Z][a-zA-Z0-9_]+ (?:SDK|API|Engine|Framework|Protocol|Database|Service))\b"
]

# Organization / Company patterns
ORG_PATTERNS = [
    r"\b([A-Z][a-zA-Z0-9_]+ (?:Inc|Corp|LLC|Ltd|Technologies|Labs|Systems|Foundation|Group))\b",
    r"\b(Google|OpenAI|Anthropic|DeepMind|Microsoft|Apple|Amazon|AWS|Meta|Linux Foundation)\b"
]

# Project / Component patterns
PROJECT_PATTERNS = [
    r"\b(Project [A-Z][a-zA-Z0-9_]+)\b",
    r"\b([A-Z][a-zA-Z0-9_]+ (?:Platform|Architecture|Pipeline|System|Module))\b"
]

# Section / Heading patterns
SECTION_PATTERNS = [
    r"(?:^|\n)#{1,3}\s+([A-Za-z0-9 _\-\:\.]+)",
    r"(?:Section|Chapter)\s+([0-9A-Za-z\.\-_ ]+)"
]

# Relationship trigger words mapping
REL_TRIGGERS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:uses|utilizes|built with|powered by|implemented in|written in)\b", re.I), RelationshipType.USES.value),
    (re.compile(r"\b(?:contains|includes|comprises|consists of|houses)\b", re.I), RelationshipType.CONTAINS.value),
    (re.compile(r"\b(?:depends on|relies on|requires|prerequisite)\b", re.I), RelationshipType.DEPENDS_ON.value),
    (re.compile(r"\b(?:references|cites|points to|links to)\b", re.I), RelationshipType.REFERENCES.value),
    (re.compile(r"\b(?:assigned to|allocated to|delegated to)\b", re.I), RelationshipType.ASSIGNED_TO.value),
    (re.compile(r"\b(?:part of|component of|module of)\b", re.I), RelationshipType.PART_OF.value),
    (re.compile(r"\b(?:created by|authored by|written by|developed by)\b", re.I), RelationshipType.CREATED_BY.value),
    (re.compile(r"\b(?:related to|associated with|connected with)\b", re.I), RelationshipType.RELATED_TO.value),
]

class RuleBasedEntityExtractor(BaseEntityExtractor):
    """
    Deterministic, bounded, regex and pattern-driven entity & relationship extractor.
    Operates 100% locally without external AI provider dependencies.
    """
    def __init__(self, config: Optional[ExtractionConfig] = None):
        super().__init__(config or ExtractionConfig(provider="rule_based"))

    def extract_entities(
        self,
        text: str,
        document_id: Optional[uuid.UUID] = None,
        chunk_id: Optional[uuid.UUID] = None,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        **kwargs
    ) -> List[ExtractedEntity]:
        if not text or not text.strip():
            return []

        entities: List[ExtractedEntity] = []
        seen_keys: Set[str] = set()

        # 1. Extract Technologies / Skills
        for pattern in TECH_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw_name = match.group(0)
                display_name, lookup_key, ent_type = EntityNormalizer.canonicalize(raw_name, fallback_type=NodeType.SKILL.value)
                if lookup_key and lookup_key not in seen_keys:
                    seen_keys.add(lookup_key)
                    entities.append(
                        ExtractedEntity(
                            name=display_name,
                            entity_type=ent_type,
                            description=f"Extracted {ent_type.lower()} entity from text context.",
                            confidence=0.92,
                            source_text=raw_name,
                            start_offset=match.start(),
                            end_offset=match.end(),
                            document_id=document_id,
                            chunk_id=chunk_id,
                            page_number=page_number,
                            section_title=section_title
                        )
                    )

        # 2. Extract Organizations / Projects
        for pattern in ORG_PATTERNS:
            for match in re.finditer(pattern, text):
                raw_name = match.group(0)
                display_name, lookup_key, ent_type = EntityNormalizer.canonicalize(raw_name, fallback_type=NodeType.PROJECT.value)
                if lookup_key and lookup_key not in seen_keys:
                    seen_keys.add(lookup_key)
                    entities.append(
                        ExtractedEntity(
                            name=display_name,
                            entity_type=ent_type,
                            description=f"Extracted organization/project entity.",
                            confidence=0.88,
                            source_text=raw_name,
                            start_offset=match.start(),
                            end_offset=match.end(),
                            document_id=document_id,
                            chunk_id=chunk_id,
                            page_number=page_number,
                            section_title=section_title
                        )
                    )

        for pattern in PROJECT_PATTERNS:
            for match in re.finditer(pattern, text):
                raw_name = match.group(0)
                display_name, lookup_key, ent_type = EntityNormalizer.canonicalize(raw_name, fallback_type=NodeType.PROJECT.value)
                if lookup_key and lookup_key not in seen_keys:
                    seen_keys.add(lookup_key)
                    entities.append(
                        ExtractedEntity(
                            name=display_name,
                            entity_type=ent_type,
                            description=f"Extracted project entity.",
                            confidence=0.85,
                            source_text=raw_name,
                            start_offset=match.start(),
                            end_offset=match.end(),
                            document_id=document_id,
                            chunk_id=chunk_id,
                            page_number=page_number,
                            section_title=section_title
                        )
                    )

        # 3. Extract Section / Chunk references if available
        for pattern in SECTION_PATTERNS:
            for match in re.finditer(pattern, text):
                raw_name = match.group(1).strip()
                if len(raw_name) > 3:
                    display_name, lookup_key, _ = EntityNormalizer.canonicalize(raw_name, fallback_type=NodeType.DOCUMENT_CHUNK.value)
                    if lookup_key and lookup_key not in seen_keys:
                        seen_keys.add(lookup_key)
                        entities.append(
                            ExtractedEntity(
                                name=display_name,
                                entity_type=NodeType.DOCUMENT_CHUNK.value,
                                description=f"Extracted document section: {display_name}",
                                confidence=0.80,
                                source_text=raw_name,
                                start_offset=match.start(),
                                end_offset=match.end(),
                                document_id=document_id,
                                chunk_id=chunk_id,
                                page_number=page_number,
                                section_title=section_title
                            )
                        )

        return entities

    def extract_relationships(
        self,
        text: str,
        entities: List[ExtractedEntity],
        document_id: Optional[uuid.UUID] = None,
        chunk_id: Optional[uuid.UUID] = None,
        **kwargs
    ) -> List[ExtractedRelationship]:
        if len(entities) < 2 or not text:
            return []

        relationships: List[ExtractedRelationship] = []
        seen_pairs: Set[Tuple[str, str, str]] = set()

        # Split into sentences or clauses for proximity analysis
        sentences = re.split(r"(?:\. |\n|\;)", text)

        for sent in sentences:
            if not sent.strip():
                continue
            # Find entities present in this sentence
            present_entities = [e for e in entities if e.name.lower() in sent.lower()]
            if len(present_entities) >= 2:
                # Detect relationship trigger in this sentence
                detected_rel_type = RelationshipType.RELATED_TO.value
                for trigger_re, rel_type in REL_TRIGGERS:
                    if trigger_re.search(sent):
                        detected_rel_type = rel_type
                        break

                # Create pairwise edges for co-occurring entities in the clause
                for i in range(len(present_entities)):
                    for j in range(i + 1, len(present_entities)):
                        src = present_entities[i]
                        tgt = present_entities[j]

                        if src.name == tgt.name:
                            continue

                        pair_key = (src.name, tgt.name, detected_rel_type)
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            relationships.append(
                                ExtractedRelationship(
                                    source_entity_name=src.name,
                                    target_entity_name=tgt.name,
                                    relationship_type=detected_rel_type,
                                    confidence=0.85 if detected_rel_type != RelationshipType.RELATED_TO.value else 0.70,
                                    source_text=sent.strip()[:250],
                                    document_id=document_id,
                                    chunk_id=chunk_id
                                )
                            )

        return relationships
