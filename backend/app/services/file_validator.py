import os
from typing import Tuple, Dict, Any, Optional
from loguru import logger

from app.core.config import settings
from app.core.document_exceptions import DocumentTooLarge, UnsupportedFileType, InvalidFile

# Supported extensions mapping to allowed MIME types
SUPPORTED_FORMATS: Dict[str, Tuple[str, ...]] = {
    # Documents
    ".pdf": ("application/pdf",),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation",),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    ".txt": ("text/plain",),
    ".csv": ("text/csv", "application/csv", "text/plain"),
    
    # Images
    ".png": ("image/png",),
    ".jpg": ("image/jpeg", "image/pjpeg"),
    ".jpeg": ("image/jpeg", "image/pjpeg"),
    
    # Audio
    ".mp3": ("audio/mpeg", "audio/mp3"),
    ".wav": ("audio/wav", "audio/x-wav", "audio/wave"),
    
    # Video
    ".mp4": ("video/mp4",),
    ".mov": ("video/quicktime",),
    ".avi": ("video/x-msvideo", "video/avi"),
    ".mkv": ("video/x-matroska", "video/mkv")
}

class FileValidator:
    @staticmethod
    def validate_size(file_size_bytes: int) -> None:
        """
        Validates that the file size does not exceed the configured limit.
        """
        max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        if file_size_bytes > max_bytes:
            raise DocumentTooLarge(
                f"File size of {file_size_bytes / (1024 * 1024):.2f} MB "
                f"exceeds limit of {settings.MAX_DOCUMENT_SIZE_MB} MB."
            )

    @staticmethod
    def validate_format_and_signature(filename: str, mime_type: str, content: bytes) -> str:
        """
        Validates the extension matches the MIME type and verifies the file magic signature bytes.
        Returns the normalized file extension.
        """
        _, ext = os.path.splitext(filename.lower())
        if not ext:
            raise UnsupportedFileType("File has no extension.")

        if ext not in SUPPORTED_FORMATS:
            raise UnsupportedFileType(f"File extension '{ext}' is not supported.")

        allowed_mimes = SUPPORTED_FORMATS[ext]
        # Normalize incoming MIME types (sometimes browsers append charset, etc.)
        base_mime = mime_type.split(";")[0].strip().lower()
        
        if base_mime not in allowed_mimes:
            logger.warning(f"MIME type mismatch for {filename}: got {base_mime}, expected one of {allowed_mimes}")
            # We enforce strict MIME validation to protect against MIME spoofing
            raise UnsupportedFileType(f"MIME type '{base_mime}' does not match extension '{ext}'.")

        # Verify signature bytes
        FileValidator._check_magic_bytes(ext, content)
        
        return ext

    @staticmethod
    def _check_magic_bytes(ext: str, content: bytes) -> None:
        """
        Checks magic byte headers to prevent extension spoofing.
        """
        header = content[:16]
        
        if ext == ".pdf" and not header.startswith(b"%PDF"):
            raise InvalidFile("Invalid PDF file signature.")
            
        elif ext in [".docx", ".xlsx", ".pptx"] and not header.startswith(b"PK\x03\x04"):
            raise InvalidFile("Invalid Office Document container (expected ZIP/PK signature).")
            
        elif ext == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise InvalidFile("Invalid PNG image signature.")
            
        elif ext in [".jpg", ".jpeg"] and not header.startswith(b"\xff\xd8\xff"):
            raise InvalidFile("Invalid JPEG image signature.")
            
        elif ext == ".wav":
            if not (header.startswith(b"RIFF") and header[8:12] == b"WAVE"):
                raise InvalidFile("Invalid WAV audio signature.")
                
        elif ext == ".mp3":
            # MP3 can start with ID3 header (b"ID3") or frame sync (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
            if not (header.startswith(b"ID3") or header.startswith(b"\xff\xfb") or header.startswith(b"\xff\xf3") or header.startswith(b"\xff\xf2")):
                raise InvalidFile("Invalid MP3 audio signature.")
                
        elif ext == ".mp4" and b"ftyp" not in header[4:12]:
            raise InvalidFile("Invalid MP4 video signature.")
            
        elif ext == ".mkv" and not header.startswith(b"\x1a\x45\xdf\xa3"):
            raise InvalidFile("Invalid MKV video signature.")
            
        elif ext == ".avi":
            if not (header.startswith(b"RIFF") and header[8:12] == b"AVI "):
                raise InvalidFile("Invalid AVI video signature.")
                
        elif ext == ".mov":
            # MOV files typically contain ftypqt or start with free/moov/mdat boxes at offset 4
            if not (b"ftypqt" in header or b"moov" in header or header.startswith(b"\x00\x00\x00")):
                raise InvalidFile("Invalid MOV video signature.")
                
        elif ext in [".txt", ".csv"]:
            # Simple check for plain text: should not contain null bytes in the first 4KB
            block = content[:4096]
            if b"\x00" in block:
                raise InvalidFile("Plain text file contains binary null character sequence.")
