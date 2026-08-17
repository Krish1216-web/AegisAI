import os
import hashlib
import uuid
from loguru import logger

from app.core.config import settings
from app.core.document_exceptions import DocumentStorageError

class DocumentStorage:
    def __init__(self, storage_root: str = None):
        self.storage_root = os.path.abspath(storage_root or settings.DOCUMENT_STORAGE_PATH)
        # Ensure base directory exists
        os.makedirs(self.storage_root, exist_ok=True)

    def _resolve_and_validate(self, storage_path: str) -> str:
        """
        Normalizes, validates, and resolves the absolute target path,
        guarding against directory traversal.
        """
        # Reject obvious directory traversal attempts
        if ".." in storage_path or storage_path.startswith("/") or storage_path.startswith("\\") or ":" in storage_path:
            raise DocumentStorageError("Directory traversal or invalid path detected.")

        # Create localized absolute path reference
        abs_target = os.path.abspath(os.path.join(self.storage_root, storage_path))

        # Check bounds
        if not abs_target.startswith(self.storage_root):
            raise DocumentStorageError("Target path lies outside storage root boundaries.")

        return abs_target

    def calculate_checksum(self, content: bytes) -> str:
        """
        Computes the SHA-256 hash of file content.
        """
        return hashlib.sha256(content).hexdigest()

    def store_file(self, workspace_id: uuid.UUID, document_id: uuid.UUID, content: bytes) -> str:
        """
        Writes the uploaded document byte stream to disk using secure identifiers.
        Returns the relative storage path.
        """
        # Conceptual structure: workspaces/<workspace_id>/documents/<document_id>/original_file
        relative_path = os.path.join(
            "workspaces", 
            str(workspace_id), 
            "documents", 
            str(document_id), 
            "original_file"
        )
        
        try:
            abs_path = self._resolve_and_validate(relative_path)
            
            # Ensure parent directories exist
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            # Write file content
            with open(abs_path, "wb") as f:
                f.write(content)
                
            logger.info(f"File stored successfully at relative path: {relative_path}")
            return relative_path.replace("\\", "/")  # Normalize separator for DB storage
        except Exception as e:
            logger.error(f"Failed to write file to storage: {e}")
            raise DocumentStorageError(f"File write operation failed: {str(e)}")

    def get_file(self, storage_path: str) -> bytes:
        """
        Retrieves raw document bytes from storage.
        """
        try:
            abs_path = self._resolve_and_validate(storage_path)
            if not os.path.exists(abs_path):
                raise DocumentStorageError("File not found in physical storage.")
                
            with open(abs_path, "rb") as f:
                return f.read()
        except DocumentStorageError:
            raise
        except Exception as e:
            logger.error(f"Failed to read file from storage: {e}")
            raise DocumentStorageError(f"File read operation failed: {str(e)}")

    def delete_file(self, storage_path: str) -> None:
        """
        Deletes the target file from storage and attempts to clean up empty directories.
        """
        try:
            abs_path = self._resolve_and_validate(storage_path)
            if os.path.exists(abs_path):
                os.remove(abs_path)
                logger.info(f"Deleted file at: {abs_path}")
                
                # Attempt to clean empty ancestor directories recursively up to storage_root
                parent = os.path.dirname(abs_path)
                while parent != self.storage_root:
                    if not os.listdir(parent):
                        os.rmdir(parent)
                        logger.info(f"Cleaned empty parent folder: {parent}")
                        parent = os.path.dirname(parent)
                    else:
                        break
        except Exception as e:
            logger.error(f"Failed to delete file from storage: {e}")
            raise DocumentStorageError(f"File delete operation failed: {str(e)}")

    def file_exists(self, storage_path: str) -> bool:
        """
        Checks if the file exists in storage.
        """
        try:
            abs_path = self._resolve_and_validate(storage_path)
            return os.path.exists(abs_path)
        except Exception:
            return False
