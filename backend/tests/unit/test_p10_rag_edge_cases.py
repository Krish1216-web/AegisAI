import uuid
import pytest
from app.core.rag.citations import CitationSystem
from app.core.rag.context import ContextBuilder
from app.schemas.rag import RetrievedChunk

class MockChunk:
    def __init__(self, content, doc_id=None, page_number=1, section_title="Intro"):
        self.content = content
        self.document_id = doc_id or uuid.uuid4()
        self.document = None
        self.page_number = page_number
        self.section_title = section_title
        self.start_offset = 0
        self.end_offset = len(content)

def test_citation_engine_empty_and_valid_cases():
    engine = CitationSystem()
    
    # Empty answer or candidates
    assert engine.extract_citations("", []) == []
    
    # Valid answer referencing candidate [1]
    chunk = MockChunk("AegisAI employs a modular multi-agent platform.")
    candidates = [{"chunk": chunk, "score": 0.92}]
    answer = "The platform is multi-agent [1]."
    citations = engine.extract_citations(answer, candidates)
    assert len(citations) == 1
    assert citations[0].document_name == "Unknown Source"
    assert citations[0].citation_number == 1

def test_context_builder_empty_and_bounded():
    builder = ContextBuilder()
    
    # Empty candidates
    ctx = builder.build_context([], max_tokens=500)
    assert ctx == ""
    
    # Valid candidate
    chunk = MockChunk("All API requests must validate JWT signatures.")
    candidates = [{"chunk": chunk, "score": 0.95}]
    ctx = builder.build_context(candidates, max_tokens=500)
    assert "All API requests must validate JWT signatures." in ctx
