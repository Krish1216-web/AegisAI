import re
import json
import hashlib
from typing import Dict, Any, Optional
from app.models.mcp import MCPCapabilityType

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"reveal\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+dan\s+mode", re.IGNORECASE),
]

class MCPNormalizer:
    """
    Normalizes MCP capability definitions and computes deterministic hashes
    for change and version tracking while ensuring prompt injection payloads remain inert.
    """
    @staticmethod
    def sanitize_text(text: Optional[str], max_length: int = 1000) -> Optional[str]:
        """
        Sanitizes external descriptions and metadata strings.
        Ensures control characters are stripped and untrusted text is cleanly bounded.
        """
        if not text:
            return None
        # Remove ASCII control characters except newline and tab
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text).strip()
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "..."
        return cleaned

    @staticmethod
    def canonicalize_schema(schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Converts JSON Schema into sorted, canonical dictionary structure.
        """
        if not schema or not isinstance(schema, dict):
            return {"type": "object", "properties": {}}

        def sort_dict(d: Any) -> Any:
            if isinstance(d, dict):
                return {k: sort_dict(v) for k, v in sorted(d.items())}
            if isinstance(d, list):
                # If list of dicts, sort each dict
                return [sort_dict(item) for item in d]
            return d

        canonical = sort_dict(schema)
        if "type" not in canonical:
            canonical["type"] = "object"
        return canonical

    @staticmethod
    def compute_definition_hash(
        capability_type: MCPCapabilityType,
        name: str,
        description: Optional[str],
        input_schema: Optional[Dict[str, Any]],
        meta_data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generates a deterministic SHA-256 hash representing the exact capability specification.
        """
        normalized_data = {
            "type": capability_type.value if hasattr(capability_type, "value") else str(capability_type),
            "name": name.strip(),
            "description": (description or "").strip(),
            "schema": MCPNormalizer.canonicalize_schema(input_schema),
            "metadata": {k: v for k, v in sorted((meta_data or {}).items()) if k not in ("size_bytes", "discovered_at", "last_ping")}
        }
        
        serialized = json.dumps(normalized_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
