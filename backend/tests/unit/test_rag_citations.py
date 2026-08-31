import pytest
import uuid
from app.models.document import Document, DocumentChunk
from app.core.rag.citations import CitationSystem

def test_citation_system_extraction_and_sanitization():
    doc = Document(
        id=uuid.uuid4(),
        filename="report.pdf",
        original_filename="report.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=100
    )
    
    chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        document=doc,
        chunk_index=0,
        content="AI systems can solve complex reasoning tasks.",
        token_count=10,
        character_count=45
    )
    
    chunk_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        document=doc,
        chunk_index=1,
        content="Security gates must be deterministic.",
        token_count=10,
        character_count=36
    )

    candidates = [
        {"chunk": chunk_1, "score": 0.95},
        {"chunk": chunk_2, "score": 0.88}
    ]

    system = CitationSystem()

    # Mix of valid [1], [2], duplicate [1], and fabricated [3] citations
    answer = "AI solves complex reasoning [1]. Security gates are deterministic [2] and [1]. Fabricated claims are here [3]."
    
    # Validation step (should strip [3] but preserve [1] and [2])
    sanitized = system.validate_citations(answer, candidates)
    assert "[1]" in sanitized
    assert "[2]" in sanitized
    assert "[3]" not in sanitized
    
    # Extraction step (should return Citation schemas for [1] and [2] without duplication)
    citations = system.extract_citations(sanitized, candidates)
    assert len(citations) == 2
    
    c1 = citations[0]
    assert c1.citation_number == 1
    assert c1.document_name == "report.pdf"
    assert "complex reasoning" in c1.snippet
    
    c2 = citations[1]
    assert c2.citation_number == 2
    assert c2.document_name == "report.pdf"
    assert "deterministic" in c2.snippet
