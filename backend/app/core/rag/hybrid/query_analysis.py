import re
from typing import List, Set, Dict, Any, Tuple
from app.services.entity_extraction.normalizer import EntityNormalizer, KNOWN_ALIASES
from app.services.entity_extraction.rule_based import TECH_PATTERNS, ORG_PATTERNS, PROJECT_PATTERNS

RELATION_KEYWORDS = [
    r"\b(related to|connected to|depends on|uses?|use|utilizes?|built with|relationship between|path between|part of|works on)\b",
    r"\b(how does .* relate to|how is .* connected to|architecture of|graph of)\b"
]

DOCUMENT_KEYWORDS = [
    r"\b(document|pdf|file|page|section|paragraph|uploaded|contract|specification|report|quote|summary of)\b"
]

class QueryEntityExtractor:
    """
    Analyzes user queries to deterministically extract domain entities, technical concepts,
    and determine optimal retrieval strategy (vector-centric, graph-centric, or hybrid).
    """
    @staticmethod
    def extract_query_entities(query: str) -> List[str]:
        if not query or not query.strip():
            return []

        clean_q = EntityNormalizer.normalize_text(query)
        entities: List[str] = []
        seen_keys: Set[str] = set()

        # 1. Match Known Aliases
        for alias_lower, (canonical_name, _) in KNOWN_ALIASES.items():
            pattern = r"\b" + re.escape(alias_lower) + r"\b"
            if re.search(pattern, clean_q, re.IGNORECASE):
                key = EntityNormalizer.get_lookup_key(canonical_name)
                if key not in seen_keys:
                    seen_keys.add(key)
                    entities.append(canonical_name)

        # 2. Match Regex Patterns
        all_patterns = TECH_PATTERNS + ORG_PATTERNS + PROJECT_PATTERNS
        for pat in all_patterns:
            for match in re.finditer(pat, clean_q, re.IGNORECASE):
                raw_name = match.group(0)
                display_name, key, _ = EntityNormalizer.canonicalize(raw_name)
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    entities.append(display_name)

        # 3. Capitalized Word Sequences (2+ words)
        cap_matches = re.finditer(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)+)\b", query)
        for m in cap_matches:
            raw = m.group(1).strip()
            display_name, key, _ = EntityNormalizer.canonicalize(raw)
            if key and len(key) > 3 and key not in seen_keys:
                seen_keys.add(key)
                entities.append(display_name)

        return entities

    @staticmethod
    def analyze_query_intent(query: str) -> Dict[str, Any]:
        """
        Determines the query's retrieval profile:
        - strategy: 'graph_centric' | 'vector_centric' | 'hybrid'
        - entities: list of extracted entities
        """
        entities = QueryEntityExtractor.extract_query_entities(query)
        q_lower = query.lower()

        is_graph = any(re.search(p, q_lower) for p in RELATION_KEYWORDS)
        is_doc = any(re.search(p, q_lower) for p in DOCUMENT_KEYWORDS)

        if is_graph and not is_doc:
            strategy = "graph_centric"
        elif is_doc and not is_graph and len(entities) == 0:
            strategy = "vector_centric"
        else:
            strategy = "hybrid"

        return {
            "strategy": strategy,
            "entities": entities,
            "has_graph_intent": is_graph,
            "has_doc_intent": is_doc
        }
