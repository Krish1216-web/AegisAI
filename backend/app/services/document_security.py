import re
from typing import Dict, Any, List

# Common prompt injection, role override, data exfiltration, and rule bypass patterns
SUSPICIOUS_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"ignore\s+(?:the\s+)?above\s+instructions",
    r"you\s+are\s+now\s+(?:an|a|in)\s+\w+",
    r"system\s+(?:directive|override|instructions?)\s*:",
    r"\[system\s+override\]",
    r"<<sys>>",
    r"new\s+instructions\s*:",
    r"overwrite\s+system\s+(?:prompt|instructions)",
    r"forget\s+(?:everything\s+)?you\s+were\s+told",
    r"developer\s+mode",
    r"bypass\s+(?:all\s+)?(?:safety|security)\s+(?:filters?|constraints|rules)",
    r"ignore\s+your\s+(?:system\s+)?prompt",
    r"you\s+must\s+ignore\s+(?:all|any)?",
    r"ignore\s+all\s+guidelines",
    r"(?:execute|run|call)\s*tool\s*:\s*\w+",
    r"execute_tool\s*:\s*\w+",
    r"call\s+(?:the\s+)?(?:delete|execute|run|drop|admin|exfiltrate)\w*\s+tool",
    r"exfiltrate\s+(?:data|document|secret|token|key|content)\s+to\s+\S+",
    r"send\s+(?:this\s+)?(?:data|document|content|file|secret|key|token)\s+to\s+\S+",
    r"reveal\s+(?:the\s+)?(?:api[_-]?key|secret|password|token|system\s+prompt|credentials|environment)",
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
