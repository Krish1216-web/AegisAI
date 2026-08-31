import pytest
from app.services.chunking.recursive import RecursiveCharacterChunker
from app.services.chunking.base import ApproximateTokenizer
from app.services.extractors.base import ExtractedDocument, PageData, SectionData

def test_approximate_tokenizer():
    tok = ApproximateTokenizer()
    text = "Hello Aegis!"
    assert tok.count_tokens(text) == len(text) // 4
    assert tok.decode(tok.encode(text)) == text

def test_recursive_chunker_simple():
    tokenizer = ApproximateTokenizer()
    # 25 characters = approx 6 tokens
    doc = ExtractedDocument(
        text="Hello world. AegisAI platform intelligent chunks.",
        pages=[],
        sections=[],
        metadata={}
    )
    # Configure tiny chunk size (5 tokens, overlap 1 token)
    chunker = RecursiveCharacterChunker(chunk_size=5, chunk_overlap=1)
    chunks = chunker.chunk(doc, tokenizer)
    
    assert len(chunks) > 0
    assert all(c.token_count <= 5 for c in chunks)
    # Check deterministic ordering
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert len(c.content) == c.character_count

def test_recursive_chunker_pages():
    tokenizer = ApproximateTokenizer()
    pages = [
        PageData(page_number=1, text="This is text on page 1 of report."),
        PageData(page_number=2, text="Here is some extra content on page 2.")
    ]
    doc = ExtractedDocument(text="", pages=pages, sections=[], metadata={})
    chunker = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk(doc, tokenizer)
    
    # Assert page numbers are preserved
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2

def test_recursive_chunker_sections():
    tokenizer = ApproximateTokenizer()
    sections = [
        SectionData(title="Overview", text="First section text goes here."),
        SectionData(title="Detail", text="Second section text detailing parameters.")
    ]
    doc = ExtractedDocument(text="", pages=[], sections=sections, metadata={})
    chunker = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk(doc, tokenizer)
    
    # Assert section titles are preserved
    assert len(chunks) >= 2
    assert chunks[0].section_title == "Overview"
    assert chunks[-1].section_title == "Detail"

def test_recursive_chunker_empty():
    tokenizer = ApproximateTokenizer()
    doc = ExtractedDocument(text="", pages=[], sections=[], metadata={})
    chunker = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk(doc, tokenizer)
    assert len(chunks) == 0
