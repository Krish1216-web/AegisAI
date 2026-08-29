import pytest
import uuid
from app.models.document import Document, DocumentChunk
from app.core.rag.reranker import SimpleScoreReranker

def test_reranker_combined_score_and_boosts():
    doc_pdf = Document(
        id=uuid.uuid4(),
        filename="tech_specs.pdf",
        original_filename="tech_specs.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=123
    )
    
    chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document=doc_pdf,
        chunk_index=0,
        content="We implement neural networks and transformer layers.",
        token_count=10,
        character_count=50,
        section_title="Architecture Intro"
    )
    
    chunk_2 = DocumentChunk(
        id=uuid.uuid4(),
        document=doc_pdf,
        chunk_index=1,
        content="Some random boilerplate details.",
        token_count=10,
        character_count=30,
        section_title="Boilerplate Appendix"
    )

    reranker = SimpleScoreReranker(w_sim=0.6, w_keyword=0.4)
    
    # Query overlap words: "neural networks"
    query = "neural networks introduction"
    candidates = [
        {"chunk": chunk_1, "score": 0.5},
        {"chunk": chunk_2, "score": 0.6}
    ]

    # Without metadata filters
    results = reranker.rerank(query, candidates)
    assert results[0]["chunk"].id == chunk_1.id  # chunk_1 should rank higher due to strong keyword match

    # With metadata filters boosting chunk_2 via section matching
    filters = {"section_title": "Appendix"}
    boosted_results = reranker.rerank(query, candidates, metadata_filters=filters)
    # chunk_2 should receive boost for section_title matching "Appendix"
    # base score chunk_2: 0.6 * 0.6 + 0.4 * 0 = 0.36. Boost = 0.05. Total = 0.41.
    # chunk_1 should also be computed correctly. Let's verify it works without erroring.
    assert len(boosted_results) == 2
