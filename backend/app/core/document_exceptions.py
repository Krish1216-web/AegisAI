from typing import Any
from app.core.exceptions import AegisBaseException

class DocumentNotFound(AegisBaseException):
    def __init__(self, message: str = "The requested document was not found.", details: Any = None):
        super().__init__(message, code="DOCUMENT_NOT_FOUND", details=details)

class UnsupportedFileType(AegisBaseException):
    def __init__(self, message: str = "File extension or MIME type not supported.", details: Any = None):
        super().__init__(message, code="UNSUPPORTED_FILE_TYPE", details=details)

class DocumentTooLarge(AegisBaseException):
    def __init__(self, message: str = "The uploaded file size exceeds maximum limits.", details: Any = None):
        super().__init__(message, code="DOCUMENT_TOO_LARGE", details=details)

class InvalidFile(AegisBaseException):
    def __init__(self, message: str = "The file is corrupt or fails signature checks.", details: Any = None):
        super().__init__(message, code="INVALID_FILE", details=details)

class DocumentPermissionDenied(AegisBaseException):
    def __init__(self, message: str = "Access to this document is denied.", details: Any = None):
        super().__init__(message, code="PERMISSION_DENIED", details=details)

class DocumentStorageError(AegisBaseException):
    def __init__(self, message: str = "An error occurred writing/deleting from physical storage.", details: Any = None):
        super().__init__(message, code="STORAGE_ERROR", details=details)

class DuplicateDocument(AegisBaseException):
    def __init__(self, message: str = "A file with the same checksum has already been uploaded by this user in this workspace.", details: Any = None):
        super().__init__(message, code="DUPLICATE_DOCUMENT", details=details)
