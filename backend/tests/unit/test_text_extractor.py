import pytest
import os
import tempfile

from app.services.extractors.text import TextExtractor

def test_text_extractor_utf8():
    extractor = TextExtractor()
    text = "Hello World! This is plaintext content."
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(text.encode("utf-8"))
        temp_path = f.name
        
    try:
        res = extractor.extract(temp_path)
        assert res.text == text
        assert res.metadata["encoding"] == "utf-8"
        assert res.character_count == len(text)
        assert res.word_count == 6
    finally:
        os.remove(temp_path)

def test_text_extractor_latin1():
    extractor = TextExtractor()
    text = "Héllò World! Spêcïal Chars."
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(text.encode("latin-1"))
        temp_path = f.name
        
    try:
        res = extractor.extract(temp_path)
        assert res.text == text
        assert res.metadata["encoding"] == "latin-1"
    finally:
        os.remove(temp_path)
