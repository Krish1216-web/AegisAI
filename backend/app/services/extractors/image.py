import os
from abc import ABC, abstractmethod
from PIL import Image
from loguru import logger

from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument
from app.core.document_exceptions import InvalidFile

class BaseOCRProvider(ABC):
    @abstractmethod
    def scan(self, file_path: str) -> str:
        pass

class MockOCRProvider(BaseOCRProvider):
    def scan(self, file_path: str) -> str:
        # Fallback to no-op
        return ""

class ImageExtractor(BaseDocumentExtractor):
    def __init__(self, ocr_provider: BaseOCRProvider = None):
        self.ocr_provider = ocr_provider or MockOCRProvider()

    def extract(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise InvalidFile("Image file does not exist on disk.")

        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode

            # Try to run OCR if a provider is configured and not mock
            is_ocr_available = not isinstance(self.ocr_provider, MockOCRProvider)
            
            try:
                extracted_text = self.ocr_provider.scan(file_path)
            except Exception as e:
                logger.warning(f"OCR scanning failed: {e}")
                extracted_text = ""
                
            char_count = len(extracted_text)
            word_count = len(extracted_text.split())

            return ExtractedDocument(
                text=extracted_text,
                pages=[],
                sections=[],
                metadata={
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "ocr_available": is_ocr_available
                },
                page_count=1,
                character_count=char_count,
                word_count=word_count
            )

        except Exception as e:
            logger.error(f"Failed to parse image file metadata: {e}")
            raise InvalidFile(f"Failed to parse image file: {str(e)}")
