import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch

from app.services.extractors.pdf import PDFExtractor
from app.core.document_exceptions import InvalidFile

def test_pdf_extractor_success():
    extractor = PDFExtractor()
    
    # Mock PdfReader behaviour
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello Page Content"
    
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [mock_page, mock_page]
    mock_reader.metadata = {"Title": "Test Report", "Author": "AegisAI"}
    
    with patch("app.services.extractors.pdf.PdfReader", return_value=mock_reader):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"%PDF-1.5 mock pdf data")
            temp_path = f.name
            
        try:
            res = extractor.extract(temp_path)
            assert res.page_count == 2
            assert "Hello Page Content" in res.text
            assert res.metadata["Title"] == "Test Report"
            assert res.character_count > 0
            assert res.word_count == 10
        finally:
            os.remove(temp_path)

def test_pdf_extractor_encrypted():
    extractor = PDFExtractor()
    mock_reader = MagicMock()
    mock_reader.is_encrypted = True
    
    with patch("app.services.extractors.pdf.PdfReader", return_value=mock_reader):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"%PDF-1.5 encrypted pdf data")
            temp_path = f.name
            
        try:
            with pytest.raises(InvalidFile) as exc_info:
                extractor.extract(temp_path)
            assert "password-protected" in str(exc_info.value)
        finally:
            os.remove(temp_path)

def test_pdf_extractor_empty():
    extractor = PDFExtractor()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [mock_page]
    mock_reader.metadata = {}

    with patch("app.services.extractors.pdf.PdfReader", return_value=mock_reader):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"%PDF-1.5 empty pdf data")
            temp_path = f.name
            
        try:
            res = extractor.extract(temp_path)
            assert res.page_count == 1
            assert res.text == ""
            assert res.metadata.get("ocr_required") is True
        finally:
            os.remove(temp_path)
