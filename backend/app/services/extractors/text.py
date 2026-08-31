import os
from loguru import logger

from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument
from app.core.document_exceptions import InvalidFile

class TextExtractor(BaseDocumentExtractor):
    def extract(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise InvalidFile("Text file does not exist on disk.")

        encodings = ["utf-8", "latin-1", "cp1252", "utf-16"]
        content = None
        used_encoding = None

        # Read file bytes
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
        except Exception as e:
            raise InvalidFile(f"Failed to read file from disk: {str(e)}")

        for enc in encodings:
            try:
                content = raw_bytes.decode(enc)
                used_encoding = enc
                break
            except (UnicodeDecodeError, ValueError):
                continue

        if content is None:
            logger.error(f"Failed to decode text file with standard encodings: {file_path}")
            raise InvalidFile("Could not decode text file: encoding not supported.")

        # Clean null characters
        content = content.replace("\x00", "")
        
        char_count = len(content)
        word_count = len(content.split())

        return ExtractedDocument(
            text=content,
            pages=[],
            sections=[],
            metadata={"encoding": used_encoding},
            page_count=1,
            character_count=char_count,
            word_count=word_count
        )
