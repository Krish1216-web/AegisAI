import pytest
from unittest import mock

from app.services.file_validator import FileValidator
from app.core.document_exceptions import DocumentTooLarge, UnsupportedFileType, InvalidFile

def test_validate_size():
    # Exceed default 50MB (50 * 1024 * 1024 + 1 bytes)
    FileValidator.validate_size(50 * 1024 * 1024)  # Should pass
    
    with pytest.raises(DocumentTooLarge):
        FileValidator.validate_size(50 * 1024 * 1024 + 1)

def test_validate_valid_documents():
    # Valid PDF
    ext = FileValidator.validate_format_and_signature("report.pdf", "application/pdf", b"%PDF-1.5 ...")
    assert ext == ".pdf"

    # Valid DOCX
    ext = FileValidator.validate_format_and_signature("notes.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04...")
    assert ext == ".docx"

    # Valid TXT
    ext = FileValidator.validate_format_and_signature("log.txt", "text/plain", b"plain ascii text logs")
    assert ext == ".txt"

    # Valid CSV
    ext = FileValidator.validate_format_and_signature("data.csv", "text/csv", b"col1,col2,col3\n1,2,3")
    assert ext == ".csv"

    # Valid Image
    ext = FileValidator.validate_format_and_signature("photo.png", "image/png", b"\x89PNG\r\n\x1a\n...")
    assert ext == ".png"

    # Valid Audio
    ext = FileValidator.validate_format_and_signature("voice.wav", "audio/wav", b"RIFF\x00\x00\x00\x00WAVE...")
    assert ext == ".wav"

    # Valid Video
    ext = FileValidator.validate_format_and_signature("video.mp4", "video/mp4", b"\x00\x00\x00\x18ftypmp42...")
    assert ext == ".mp4"

def test_unsupported_extension():
    with pytest.raises(UnsupportedFileType):
        FileValidator.validate_format_and_signature("malicious.sh", "text/x-shellscript", b"#!/bin/bash")
        
    with pytest.raises(UnsupportedFileType):
        FileValidator.validate_format_and_signature("file_no_extension", "text/plain", b"plain text")

def test_mime_mismatch():
    # Extension PDF but MIME type is plain text
    with pytest.raises(UnsupportedFileType):
        FileValidator.validate_format_and_signature("report.pdf", "text/plain", b"%PDF-1.5")

def test_spoofed_extension_magic_check():
    # Spoofed PDF (has PDF extension but TXT content)
    with pytest.raises(InvalidFile):
        FileValidator.validate_format_and_signature("fake.pdf", "application/pdf", b"just a plain text file pretending to be pdf")

def test_binary_nulls_in_plain_text():
    # TXT file with binary null bytes
    with pytest.raises(InvalidFile):
        FileValidator.validate_format_and_signature("corrupted.txt", "text/plain", b"hello\x00world binary content")
