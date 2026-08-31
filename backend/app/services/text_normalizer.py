import re
import unicodedata

def remove_control_characters(text: str) -> str:
    """
    Strips out control characters from text except standard whitespaces like tab, LF, CR.
    """
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\r\t")

def normalize_line_endings(text: str) -> str:
    """
    Standardizes line breaks to LF and reduces redundant paragraph divisions.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Condense 3 or more consecutive linebreaks down to exactly 2 (preserves paragraph breaks)
    return re.sub(r"\n{3,}", "\n\n", text)

def normalize_whitespace(text: str) -> str:
    """
    Replaces non-breaking space structures and reduces excessive spacing on individual lines
    without flattening the lines themselves.
    """
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    lines = []
    for line in text.split("\n"):
        # Replace multiple spaces/tabs on a single line with a single space
        normalized_line = re.sub(r"[ \t]{2,}", " ", line)
        lines.append(normalized_line)
    return "\n".join(lines)

def normalize_text(text: str) -> str:
    """
    Runs the full pipeline of control character removal, line ending normalization,
    and whitespace formatting.
    """
    if not text:
        return ""
    cleaned = remove_control_characters(text)
    cleaned = normalize_line_endings(cleaned)
    cleaned = normalize_whitespace(cleaned)
    return cleaned.strip()
