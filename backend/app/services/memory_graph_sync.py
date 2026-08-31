import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.models.memory import AgentMemory
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge, NodeType, RelationshipType
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.entity_extraction.resolver import EntityResolver
from app.services.entity_extraction.normalizer import EntityNormalizer
from app.services.entity_extraction.models import ExtractedEntity, ExtractedRelationship
from app.core.rag.hybrid.query_analysis import QueryEntityExtractor
from app.schemas.knowledge_graph import NodeCreate, EdgeCreate

class MemoryGraphSyncService:
    """
    Production-grade bidirectional synchronization layer between AegisAI Memory
    and Knowledge Graph with strict multi-tenancy, loop prevention, and provenance tracking.
    """
    def __init__(self, db: Session):
        self.db = db
        self.kg_service = KnowledgeGraphService(db)
        self.resolver = EntityResolver(db)

    def _get_or_create_user_node(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> KnowledgeGraphNode:
        """
        Retrieves or initializes the anchor USER graph node for the tenant session.
        """
        user_node = self.kg_service.get_node_by_external_id(
            user_id=user_id,
            workspace_id=workspace_id,
            external_id=f"user_{user_id}"
        )
        if not user_node:
            user_node = self.kg_service.create_node(
                user_id=user_id,
                workspace_id=workspace_id,
                node_data=NodeCreate(
                    node_type=NodeType.USER.value,
                    name="CurrentUser",
                    external_id=f"user_{user_id}",
                    description="User identity graph anchor",
                    metadata={"system_anchor": True}
                )
            )
        return user_node

    def sync_memory_to_graph(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        memory: Any # AgentMemory, MemoryRecord, or Dict
    ) -> Dict[str, Any]:
        """
        Extracts entities from memory content, resolves them to canonical nodes,
        and establishes contextual relationship edges while strictly enforcing tenant bounds.
        """
        start_time = time.perf_counter()

        # Extract normalized attributes from memory object or dict
        if isinstance(memory, dict):
            mem_id_str = str(memory.get("id") or memory.get("memory_id") or uuid.uuid4())
            mem_content = memory.get("content", "")
            mem_type = memory.get("memory_type", "USER_PREFERENCE")
            mem_importance = float(memory.get("importance", 0.8))
            mem_confidence = float(memory.get("confidence", 0.9))
            mem_meta = memory.get("meta_data") if isinstance(memory.get("meta_data"), dict) else (memory.get("metadata") if isinstance(memory.get("metadata"), dict) else {})
        else:
            mem_id_str = str(getattr(memory, "id", None) or getattr(memory, "memory_id", uuid.uuid4()))
            mem_content = getattr(memory, "content", "")
            mem_type = getattr(memory, "memory_type", "USER_PREFERENCE")
            if hasattr(mem_type, "value"):
                mem_type = mem_type.value
            mem_importance = float(getattr(memory, "importance", 0.8))
            mem_confidence = float(getattr(memory, "confidence", 0.9))
            raw_meta = getattr(memory, "meta_data", None)
            mem_meta = raw_meta if isinstance(raw_meta, dict) else {}

        if not isinstance(mem_meta, dict):
            mem_meta = {}

        # Loop protection check: skip if memory was originally created from graph sync
        if mem_meta.get("sync_origin") == "graph_to_memory":
            logger.info(f"Skipping sync for memory {mem_id_str} to prevent bidirectional recursion.")
            return {
                "memory_id": mem_id_str,
                "status": "skipped_loop_prevention",
                "nodes_created": 0,
                "edges_created": 0
            }

        # 1. Extract candidate entities from memory text
        extracted_names = QueryEntityExtractor.extract_query_entities(mem_content)
        if not extracted_names:
            # Fallback: extract capitalized tokens
            tokens = [t.strip(".,;:\"'()") for t in mem_content.split() if len(t) > 3 and t[0].isupper()]
            extracted_names = list(dict.fromkeys(tokens))[:5]

        # 2. Get User Anchor Node
        user_node = self._get_or_create_user_node(user_id=user_id, workspace_id=workspace_id)

        nodes_synced: List[KnowledgeGraphNode] = []
        edges_synced: List[KnowledgeGraphEdge] = []

        # Determine semantic relationship based on memory category
        if "PREFERENCE" in str(mem_type).upper():
            rel_type = RelationshipType.USES.value
        elif "PROJECT" in str(mem_type).upper():
            rel_type = RelationshipType.WORKS_ON.value
        elif "TASK" in str(mem_type).upper():
            rel_type = RelationshipType.ASSIGNED_TO.value
        elif "FACT" in str(mem_type).upper() or "LEARNING" in str(mem_type).upper():
            rel_type = RelationshipType.REFERENCES.value
        else:
            rel_type = RelationshipType.RELATED_TO.value

        combined_confidence = round(max(0.1, min(1.0, mem_importance * mem_confidence)), 2)

        # 3. Resolve & Connect Entities
        for ent_name in extracted_names:
            ent = ExtractedEntity(
                name=ent_name,
                entity_type=NodeType.SKILL.value if "PREF" in mem_type else NodeType.PROJECT.value,
                description=f"Entity identified in user memory ({mem_type})"
            )

            # Resolve to existing or create new node
            target_node = self.resolver.resolve_or_create_node(
                user_id=user_id,
                workspace_id=workspace_id,
                extracted=ent,
                allow_fuzzy=True
            )

            # Append memory provenance to node
            target_meta = dict(target_node.meta_data or {})
            prov_list = list(target_meta.get("provenance", []))
            if not any(p.get("memory_id") == mem_id_str for p in prov_list):
                prov_list.append({
                    "source_type": "memory",
                    "memory_id": mem_id_str,
                    "memory_type": str(mem_type)
                })
                target_meta["provenance"] = prov_list[:30]
                target_node.meta_data = target_meta
                self.db.commit()
                self.db.refresh(target_node)

            nodes_synced.append(target_node)

            # 4. Create / Update Edge from User Node to Target Entity
            if user_node.id != target_node.id:
                existing_edge = self.db.query(KnowledgeGraphEdge).filter(
                    KnowledgeGraphEdge.workspace_id == workspace_id,
                    KnowledgeGraphEdge.user_id == user_id,
                    KnowledgeGraphEdge.source_node_id == user_node.id,
                    KnowledgeGraphEdge.target_node_id == target_node.id,
                    KnowledgeGraphEdge.relationship_type == rel_type
                ).first()

                edge_props = {
                    "source_type": "memory",
                    "memory_id": mem_id_str,
                    "memory_type": str(mem_type),
                    "sync_origin": "memory_to_graph",
                    "snippet": mem_content[:200]
                }

                if existing_edge:
                    if combined_confidence > existing_edge.confidence:
                        existing_edge.confidence = combined_confidence
                    cur_meta = dict(existing_edge.meta_data or {})
                    cur_meta.update(edge_props)
                    existing_edge.meta_data = cur_meta
                    self.db.commit()
                    self.db.refresh(existing_edge)
                    edges_synced.append(existing_edge)
                else:
                    new_edge = self.kg_service.create_edge(
                        user_id=user_id,
                        workspace_id=workspace_id,
                        edge_data=EdgeCreate(
                            source_node_id=user_node.id,
                            target_node_id=target_node.id,
                            relationship_type=rel_type,
                            confidence=combined_confidence,
                            properties=edge_props
                        )
                    )
                    edges_synced.append(new_edge)

        elapsed = time.perf_counter() - start_time
        return {
            "memory_id": mem_id_str,
            "status": "synced",
            "nodes_synced_count": len(nodes_synced),
            "edges_synced_count": len(edges_synced),
            "latency_ms": round(elapsed * 1000, 2)
        }

    def sync_graph_to_memory(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        node_id: uuid.UUID
    ) -> Optional[AgentMemory]:
        """
        Extracts meaningful semantic relationships from a graph node to synthesize
        a high-level agent memory representation with recursion protection.
        """
        node = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=node_id)
        if not node:
            return None

        # Loop protection: skip if node was originated purely from memory
        node_meta = node.meta_data or {}
        if node_meta.get("sync_origin") == "memory_to_graph":
            logger.info(f"Skipping graph->memory sync for node {node.id} to avoid loop.")
            return None

        # Fetch incident edges
        edges, _ = self.kg_service.list_edges(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=20
        )
        related_names = []
        for e in edges:
            if e.source_node_id == node.id:
                tgt = self.kg_service.get_node(user_id=user_id, workspace_id=workspace_id, node_id=e.target_node_id)
                if tgt:
                    related_names.append(f"{e.relationship_type.lower()} {tgt.name}")

        rel_summary = f" ({', '.join(related_names[:3])})" if related_names else ""
        content = f"Knowledge Graph Entity: {node.name} [{node.node_type}]{rel_summary}. {node.description or ''}".strip()

        # Check if memory already exists for this graph entity
        existing_mem = self.db.query(AgentMemory).filter(
            AgentMemory.workspace_id == workspace_id,
            AgentMemory.user_id == user_id,
            func.lower(AgentMemory.source) == "knowledge_graph",
            AgentMemory.content.like(f"%{node.name}%")
        ).first()

        if existing_mem:
            existing_mem.content = content
            existing_mem.importance = 0.85
            self.db.commit()
            self.db.refresh(existing_mem)
            return existing_mem

        # Create new agent memory record
        new_memory = AgentMemory(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            memory_type="PROJECT_CONTEXT" if node.node_type == NodeType.PROJECT.value else "USER_FACT",
            content=content,
            source="knowledge_graph",
            importance=0.85,
            confidence=0.95,
            meta_data={
                "sync_origin": "graph_to_memory",
                "graph_node_id": str(node.id),
                "node_type": node.node_type
            }
        )
        self.db.add(new_memory)
        self.db.commit()
        self.db.refresh(new_memory)
        return new_memory

    def handle_memory_deletion(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        memory_id: str
    ) -> Dict[str, Any]:
        """
        Executes provenance-aware cleanup when a memory is invalidated or deleted.
        Removes edges dedicated to the memory and cleans node provenance arrays.
        """
        edges_deleted = 0
        nodes_cleaned = 0

        # 1. Clean edges
        edges, _ = self.kg_service.list_edges(user_id=user_id, workspace_id=workspace_id, limit=500)
        for edge in edges:
            props = dict(edge.meta_data or {})
            if props.get("memory_id") == memory_id:
                self.db.delete(edge)
                edges_deleted += 1

        # 2. Clean node provenance
        nodes, _ = self.kg_service.list_nodes(user_id=user_id, workspace_id=workspace_id, limit=500)
        for node in nodes:
            meta = dict(node.meta_data or {})
            prov = meta.get("provenance", [])
            initial_len = len(prov)
            filtered_prov = [p for p in prov if p.get("memory_id") != memory_id]
            if len(filtered_prov) < initial_len:
                meta["provenance"] = filtered_prov
                node.meta_data = meta
                nodes_cleaned += 1

        self.db.commit()
        return {
            "memory_id": memory_id,
            "edges_deleted": edges_deleted,
            "nodes_cleaned": nodes_cleaned
        }
