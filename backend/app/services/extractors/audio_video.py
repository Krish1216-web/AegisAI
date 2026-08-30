import os
import wave
from loguru import logger

from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument
from app.core.document_exceptions import InvalidFile

class AudioVideoExtractor(BaseDocumentExtractor):
    def extract(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise InvalidFile("Media file does not exist on disk.")

        # Default fallback metadata structures
        metadata = {
            "duration": None,
            "format": None,
            "codec": None,
            "width": None,
            "height": None,
            "sample_rate": None,
            "channels": None,
            "metadata_warning": None
        }

        # Determine extension to check if we can read it natively (like WAV)
        _, ext = os.path.splitext(file_path.lower())
        
        if ext == ".wav":
            try:
                with wave.open(file_path, "rb") as wav:
                    metadata["channels"] = wav.getnchannels()
                    metadata["sample_rate"] = wav.getframerate()
                    frames = wav.getnframes()
                    if metadata["sample_rate"] > 0:
                        metadata["duration"] = frames / float(metadata["sample_rate"])
                    metadata["format"] = "WAV"
                    metadata["codec"] = "PCM"
            except Exception as e:
                logger.warning(f"Failed to extract native WAV metadata: {e}")
                metadata["metadata_warning"] = f"Failed to extract WAV metadata: {str(e)}"
        else:
            # Placeholder/graceful fallback for format container limits
            metadata["format"] = ext.lstrip(".").upper()
            metadata["metadata_warning"] = f"Extraction of advanced properties not supported for format container '{ext}' without external decoders."

        return ExtractedDocument(
            text="",  # No transcription/speech recognition is performed in this phase
            pages=[],
            sections=[],
            metadata=metadata,
            page_count=0,
            character_count=0,
            word_count=0
        )
