import re
from typing import Dict, Any, List

# Common prompt injection, role override, and rule bypass patterns
SUSPICIOUS_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"ignore\s+(?:the\s+)?above\s+instructions",
    r"you\s+are\s+now\s+(?:an|a)\s+\w+",
    r"system\s+directive\s*:",
    r"new\s+instructions\s*:",
    r"overwrite\s+system\s+(?:prompt|instructions)",
    r"forget\s+(?:everything\s+)?you\s+were\s+told",
    r"developer\s+mode\s*:\s*active",
    r"bypass\s+(?:safety|security)\s+filters?",
    r"ignore\s+your\s+(?:system\s+)?prompt",
    r"you\s+must\s+ignore\s+(?:all|any)?",
    r"ignore\s+all\s+guidelines"
]

def scan_document_text(text: str) -> Dict[str, Any]:
    """
    Scans document text for common heuristic prompt injection signatures.
    Returns metadata dict specifying if matches were found and the matched text fragments.
    Does NOT delete or alter document contents.
    """
    if not text:
        return {
            "contains_suspicious_instructions": False,
            "matches": []
        }

    matches = []
    
    for pattern in SUSPICIOUS_PATTERNS:
        # Scan case-insensitively
        found = re.findall(pattern, text, re.IGNORECASE)
        if found:
            # Add found patterns uniquely
            for item in found:
                if item not in matches:
                    matches.append(item)

    return {
        "contains_suspicious_instructions": len(matches) > 0,
        "matches": matches
    }
