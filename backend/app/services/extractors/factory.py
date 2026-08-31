from typing import Dict, Type
from app.services.extractors.base import BaseDocumentExtractor
from app.services.extractors.pdf import PDFExtractor
from app.services.extractors.docx import DOCXExtractor
from app.services.extractors.pptx import PPTXExtractor
from app.services.extractors.xlsx import XLSXExtractor
from app.services.extractors.text import TextExtractor
from app.services.extractors.csv import CSVExtractor
from app.services.extractors.image import ImageExtractor
from app.services.extractors.audio_video import AudioVideoExtractor
from app.core.document_exceptions import UnsupportedFileType

class DocumentExtractorFactory:
    # Map file extensions to their extractor classes
    _extension_map: Dict[str, Type[BaseDocumentExtractor]] = {
        ".pdf": PDFExtractor,
        ".docx": DOCXExtractor,
        ".pptx": PPTXExtractor,
        ".xlsx": XLSXExtractor,
        ".txt": TextExtractor,
        ".csv": CSVExtractor,
        ".png": ImageExtractor,
        ".jpg": ImageExtractor,
        ".jpeg": ImageExtractor,
        ".mp3": AudioVideoExtractor,
        ".wav": AudioVideoExtractor,
        ".mp4": AudioVideoExtractor,
        ".mov": AudioVideoExtractor,
        ".avi": AudioVideoExtractor,
        ".mkv": AudioVideoExtractor
    }

    # Map MIME types to their extractor classes
    _mime_map: Dict[str, Type[BaseDocumentExtractor]] = {
        "application/pdf": PDFExtractor,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXExtractor,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": PPTXExtractor,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": XLSXExtractor,
        "text/plain": TextExtractor,
        "text/csv": CSVExtractor,
        "application/csv": CSVExtractor,
        "image/png": ImageExtractor,
        "image/jpeg": ImageExtractor,
        "image/pjpeg": ImageExtractor,
        "audio/mpeg": AudioVideoExtractor,
        "audio/mp3": AudioVideoExtractor,
        "audio/wav": AudioVideoExtractor,
        "audio/x-wav": AudioVideoExtractor,
        "audio/wave": AudioVideoExtractor,
        "video/mp4": AudioVideoExtractor,
        "video/quicktime": AudioVideoExtractor,
        "video/x-msvideo": AudioVideoExtractor,
        "video/avi": AudioVideoExtractor,
        "video/x-matroska": AudioVideoExtractor,
        "video/mkv": AudioVideoExtractor
    }

    @classmethod
    def get_extractor(cls, mime_type: str, file_extension: str) -> BaseDocumentExtractor:
        """
        Resolves the appropriate extractor instance based on MIME type or extension.
        Raises UnsupportedFileType if no mapping is found.
        """
        ext = file_extension.lower().strip()
        mime = mime_type.split(";")[0].strip().lower()

        # Try matching extension first
        extractor_cls = cls._extension_map.get(ext)
        
        # Fall back to MIME matching
        if not extractor_cls:
            extractor_cls = cls._mime_map.get(mime)

        if not extractor_cls:
            raise UnsupportedFileType(
                f"Unsupported document format: MIME '{mime}' and extension '{ext}' are not supported."
            )

        return extractor_cls()
