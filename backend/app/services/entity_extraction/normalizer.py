import re
import unicodedata
from typing import Dict, Tuple, Optional

KNOWN_ALIASES: Dict[str, Tuple[str, str]] = {
    # alias_lower: (canonical_display_name, entity_type)
    "fastapi": ("FastAPI", "SKILL"),
    "fast-api": ("FastAPI", "SKILL"),
    "react": ("React", "SKILL"),
    "reactjs": ("React", "SKILL"),
    "react.js": ("React", "SKILL"),
    "postgresql": ("PostgreSQL", "SKILL"),
    "postgres": ("PostgreSQL", "SKILL"),
    "pgsql": ("PostgreSQL", "SKILL"),
    "sqlite": ("SQLite", "SKILL"),
    "sqlite3": ("SQLite", "SKILL"),
    "chromadb": ("ChromaDB", "SKILL"),
    "chroma": ("ChromaDB", "SKILL"),
    "qdrant": ("Qdrant", "SKILL"),
    "redis": ("Redis", "SKILL"),
    "docker": ("Docker", "SKILL"),
    "kubernetes": ("Kubernetes", "SKILL"),
    "k8s": ("Kubernetes", "SKILL"),
    "langchain": ("LangChain", "SKILL"),
    "langgraph": ("LangGraph", "SKILL"),
    "lang graph": ("LangGraph", "SKILL"),
    "pydantic": ("Pydantic", "SKILL"),
    "pydantic v2": ("Pydantic", "SKILL"),
    "sqlalchemy": ("SQLAlchemy", "SKILL"),
    "python": ("Python", "SKILL"),
    "python3": ("Python", "SKILL"),
    "typescript": ("TypeScript", "SKILL"),
    "javascript": ("JavaScript", "SKILL"),
    "nodejs": ("Node.js", "SKILL"),
    "node.js": ("Node.js", "SKILL"),
    "aegisai": ("AegisAI", "PROJECT"),
    "aegis ai": ("AegisAI", "PROJECT"),
    "openai": ("OpenAI", "PROJECT"),
    "anthropic": ("Anthropic", "PROJECT"),
    "google": ("Google", "PROJECT"),
    "deepmind": ("DeepMind", "PROJECT"),
    "google deepmind": ("DeepMind", "PROJECT"),
    "tavily": ("Tavily", "SKILL"),
}

class EntityNormalizer:
    """
    Normalizes raw entity mentions into clean canonical names and deterministic lookup keys.
    """
    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)
        # 2. Collapse internal multiple whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        # 3. Strip leading/trailing whitespace & punctuation
        normalized = normalized.strip(" \t\n\r\"'`:;,.-–—()[]{}")
        return normalized

    @staticmethod
    def get_lookup_key(text: str) -> str:
        """
        Returns a lowercased, alphanumerically stripped string for exact duplicate resolution.
        """
        clean = EntityNormalizer.normalize_text(text).lower()
        # Remove punctuation for comparison key
        key = re.sub(r"[^a-z0-9]", "", clean)
        return key

    @classmethod
    def canonicalize(cls, raw_name: str, fallback_type: str = "PROJECT") -> Tuple[str, str, str]:
        """
        Returns:
            (canonical_display_name, lookup_key, resolved_entity_type)
        """
        clean = cls.normalize_text(raw_name)
        if not clean:
            return ("", "", fallback_type)

        lowered = clean.lower()

        # Check known aliases
        if lowered in KNOWN_ALIASES:
            canonical_name, known_type = KNOWN_ALIASES[lowered]
            return (canonical_name, cls.get_lookup_key(canonical_name), known_type)

        lookup_key = cls.get_lookup_key(clean)
        # Title case or original case if already formatted
        display_name = clean
        return (display_name, lookup_key, fallback_type)
