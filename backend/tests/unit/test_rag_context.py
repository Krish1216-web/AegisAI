import pytest
import uuid
from app.models.document import Document, DocumentChunk
from app.core.rag.context import ContextBuilder

def test_context_builder_formatting_and_token_limits():
    doc = Document(
        id=uuid.uuid4(),
        filename="test_guide.pdf",
        original_filename="test_guide.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=10
    )
    
    chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document=doc,
        chunk_index=0,
        content="This is the first segment.",
        token_count=50,
        character_count=26,
        page_number=1,
        section_title="Introduction",
        start_offset=0,
        end_offset=26
    )
    
    chunk_2 = DocumentChunk(
        id=uuid.uuid4(),
        document=doc,
        chunk_index=1,
        content="This is the second segment.",
        token_count=60,
        character_count=27,
        page_number=2,
        section_title="Methodology",
        start_offset=26,
        end_offset=53
    )

    builder = ContextBuilder()
    
    # Test full formatting
    context = builder.build_context([
        {"chunk": chunk_1, "score": 0.9},
        {"chunk": chunk_2, "score": 0.8}
    ], max_tokens=200)
    
    assert "[Source 1: test_guide.pdf, Page: 1, Section: Introduction, Offset: 0-26]" in context
    assert "This is the first segment." in context
    assert "[Source 2: test_guide.pdf, Page: 2, Section: Methodology, Offset: 26-53]" in context
    assert "This is the second segment." in context

    # Test truncation: limit 80 tokens, so chunk_2 (60 tokens) cannot be added (50 + 60 = 110 > 80)
    context_trunc = builder.build_context([
        {"chunk": chunk_1, "score": 0.9},
        {"chunk": chunk_2, "score": 0.8}
    ], max_tokens=80)
    
    assert "first segment" in context_trunc
    assert "second segment" not in context_trunc
